"""The only place that sends HTTP requests. See docs/architecture.md.

Guarantees, per run:

* robots.txt of a host is read before any other URL on that host, and every
  URL is checked against it for our user agent;
* at most ``max_requests`` requests in total, counting each redirect hop;
* at least ``delay`` seconds (or the robots.txt crawl-delay) between requests;
* the first block or challenge stops the run; later calls raise ``BlockedError``;
* no cookie jar, no proxies, no JavaScript.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urljoin, urlsplit

import httpx
from protego import Protego

from scrapeplanner import config
from scrapeplanner.detectors.antibot import classify_block
from scrapeplanner.models import RequestLogEntry, SkippedRequest, StopInfo
from scrapeplanner.record import Recorder

SkipReason = Literal["robots", "budget", "blocked", "crawl_delay"]
ROBOTS_MAX_BYTES = 512_000  # RFC 9309 §2.5: parse at least 500 KiB
REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})
_CHARSET_RE = re.compile(rb"""<meta[^>]+charset=["']?([A-Za-z0-9_\-]+)""", re.IGNORECASE)


class FetchError(Exception):
    """Base class for requests the fetcher refused to send."""


class RobotsDisallowed(FetchError):
    pass


class BudgetExceeded(FetchError):
    pass


class BlockedError(FetchError):
    pass


class CrawlDelayTooLong(FetchError):
    pass


@dataclass
class FetchedPage:
    """A response as the detectors see it (already decoded and size-capped)."""

    url: str
    final_url: str
    status: int
    headers: httpx.Headers
    body: bytes
    purpose: str
    truncated: bool = False
    elapsed_ms: int = 0
    redirects: list[str] = field(default_factory=list)
    too_many_redirects: bool = False

    @property
    def content_type(self) -> str:
        return str(self.headers.get("content-type", "")).split(";")[0].strip().lower()

    @property
    def cookie_names(self) -> list[str]:
        names = []
        for value in self.headers.get_list("set-cookie"):
            name = value.split("=", 1)[0].strip()
            if name:
                names.append(name)
        return names

    @property
    def text(self) -> str:
        return decode_body(self.body, self.headers.get("content-type", ""))

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


def decode_body(body: bytes, content_type: str) -> str:
    """Decode with the header charset, then a <meta charset>, then UTF-8."""
    candidates: list[str] = []
    match = re.search(r"charset=([\w\-]+)", content_type, re.IGNORECASE)
    if match:
        candidates.append(match.group(1))
    meta = _CHARSET_RE.search(body[:4096])
    if meta:
        candidates.append(meta.group(1).decode("ascii", "ignore"))
    candidates.append("utf-8")
    for encoding in candidates:
        try:
            return body.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", errors="replace")


@dataclass
class HostRobots:
    """robots.txt state for one host."""

    url: str
    status: int | None
    parser: Protego | None
    disallow_all: bool
    text: str = ""
    note: str | None = None

    def allowed(self, url: str) -> bool:
        if self.disallow_all:
            return False
        if self.parser is None:
            return True
        return bool(self.parser.can_fetch(url, config.UA_TOKEN))

    @property
    def crawl_delay(self) -> float | None:
        if self.parser is None:
            return None
        value = self.parser.crawl_delay(config.UA_TOKEN)
        return float(value) if value is not None else None


def host_key(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc.lower()}"


class PoliteFetcher:
    def __init__(
        self,
        *,
        max_requests: int = config.MAX_REQUESTS,
        delay: float = config.DELAY_SECONDS,
        timeout: float = config.TIMEOUT_SECONDS,
        max_body_bytes: int = config.MAX_BODY_BYTES,
        transport: httpx.BaseTransport | None = None,
        recorder: Recorder | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not 1 <= max_requests <= config.MAX_REQUESTS_CAP:
            raise ValueError(f"max_requests must be between 1 and {config.MAX_REQUESTS_CAP}")
        self.max_requests = max_requests
        self.base_delay = max(0.0, delay)
        self.max_body_bytes = max_body_bytes
        self.recorder = recorder
        self._sleep = sleep
        self._clock = clock
        self._last_request: float | None = None
        self.log: list[RequestLogEntry] = []
        self.skipped: list[SkippedRequest] = []
        self.stopped: StopInfo | None = None
        self.robots: dict[str, HostRobots] = {}
        self.pages: list[FetchedPage] = []
        """Every response received, in order (used for anti-bot detection)."""
        self._client = httpx.Client(
            transport=transport,
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,  # never pick up proxies from the environment
            headers={
                "User-Agent": config.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en",
            },
        )

    # -- public API -----------------------------------------------------

    @property
    def requests_used(self) -> int:
        return len(self.log)

    @property
    def remaining(self) -> int:
        return self.max_requests - self.requests_used

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> PoliteFetcher:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def delay_for(self, url: str) -> float:
        robots = self.robots.get(host_key(url))
        crawl_delay = robots.crawl_delay if robots else None
        return max(self.base_delay, crawl_delay or 0.0)

    def is_allowed(self, url: str) -> bool | None:
        """robots.txt verdict for ``url``; ``None`` if that host's robots is not loaded."""
        robots = self.robots.get(host_key(url))
        return robots.allowed(url) if robots else None

    def load_robots(self, url: str) -> HostRobots:
        """Fetch and parse robots.txt for the host of ``url`` (once per host)."""
        key = host_key(url)
        if key in self.robots:
            return self.robots[key]
        robots_url = f"{key}/robots.txt"
        try:
            page = self._get(robots_url, "robots", max_bytes=ROBOTS_MAX_BYTES, follow=True)
        except httpx.HTTPError as exc:
            state = HostRobots(robots_url, None, None, True, note=f"network error: {exc}")
        else:
            state = self._robots_from_response(robots_url, page)
        self.robots[key] = state
        delay = state.crawl_delay
        if delay is not None and delay > config.MAX_CRAWL_DELAY:
            self.stopped = StopInfo(
                reason="crawl_delay",
                url=robots_url,
                detail=f"crawl-delay {delay:g}s is above the {config.MAX_CRAWL_DELAY:g}s cap",
            )
        return state

    def fetch(
        self, url: str, purpose: str, *, follow: bool = True, max_bytes: int | None = None
    ) -> FetchedPage:
        """GET ``url`` after robots, budget and delay checks. Follows redirects."""
        return self._get(url, purpose, max_bytes=max_bytes, follow=follow, check_robots=True)

    # -- internals ------------------------------------------------------

    def _robots_from_response(self, robots_url: str, page: FetchedPage) -> HostRobots:
        status = page.status
        if 200 <= status < 300:
            text = decode_body(page.body, page.headers.get("content-type", ""))
            if "html" in page.content_type and "<html" in text[:2000].lower():
                return HostRobots(
                    robots_url, status, None, False, note="robots.txt served HTML; no rules"
                )
            return HostRobots(robots_url, status, Protego.parse(text), False, text=text)
        if status in (401, 403):
            return HostRobots(
                robots_url,
                status,
                None,
                True,
                note=f"robots.txt answered {status}: treated as disallow-all",
            )
        if 400 <= status < 500:
            return HostRobots(robots_url, status, None, False, note=f"no robots.txt ({status})")
        return HostRobots(
            robots_url,
            status,
            None,
            True,
            note=f"robots.txt answered {status}: treated as disallow-all",
        )

    def _get(
        self,
        url: str,
        purpose: str,
        *,
        max_bytes: int | None,
        follow: bool,
        check_robots: bool = False,
    ) -> FetchedPage:
        redirects: list[str] = []
        current = url
        for _hop in range(config.MAX_REDIRECTS + 1):
            if check_robots:
                self._check_robots(current, purpose)
            page = self._send(current, purpose, max_bytes or self.max_body_bytes)
            page.url = url
            page.redirects = redirects
            if self.stopped is not None:
                return page
            location = page.headers.get("location")
            if follow and page.status in REDIRECT_CODES and location:
                redirects.append(current)
                current = urljoin(current, location)
                continue
            return page
        page.too_many_redirects = True
        return page

    def _check_robots(self, url: str, purpose: str) -> None:
        if self.stopped is not None:
            self._skip(url, purpose, "blocked")
            raise BlockedError(self.stopped.detail)
        robots = self.load_robots(url)
        stopped = self._current_stop()  # load_robots may have stopped the run
        if stopped is not None:
            reason: SkipReason = "crawl_delay" if stopped.reason == "crawl_delay" else "blocked"
            self._skip(url, purpose, reason)
            raise BlockedError(stopped.detail)
        if not robots.allowed(url):
            self._skip(url, purpose, "robots")
            raise RobotsDisallowed(url)

    def _current_stop(self) -> StopInfo | None:
        return self.stopped

    def _skip(self, url: str, purpose: str, reason: SkipReason) -> None:
        self.skipped.append(SkippedRequest(url=url, purpose=purpose, reason=reason))

    def _send(self, url: str, purpose: str, max_bytes: int) -> FetchedPage:
        if self.stopped is not None:
            self._skip(url, purpose, "blocked")
            raise BlockedError(self.stopped.detail)
        if self.requests_used >= self.max_requests:
            self._skip(url, purpose, "budget")
            raise BudgetExceeded(url)
        self._wait(url)
        self._client.cookies.clear()  # never send cookies back
        started = self._clock()
        entry = RequestLogEntry(url=url, purpose=purpose)
        self.log.append(entry)
        try:
            with self._client.stream("GET", url) as response:
                chunks: list[bytes] = []
                size = 0
                truncated = False
                for chunk in response.iter_bytes():
                    chunks.append(chunk)
                    size += len(chunk)
                    if size > max_bytes:
                        truncated = True
                        break
                body = b"".join(chunks)[:max_bytes]
                status = response.status_code
                headers = response.headers
        except httpx.HTTPError as exc:
            entry.error = f"{type(exc).__name__}: {exc}"[:200]
            entry.elapsed_ms = int((self._clock() - started) * 1000)
            if self.recorder is not None:
                self.recorder.save_error(url, purpose, exc)
            raise
        finally:
            self._last_request = self._clock()
        entry.status = status
        entry.bytes = len(body)
        entry.elapsed_ms = int((self._clock() - started) * 1000)
        page = FetchedPage(
            url=url,
            final_url=url,
            status=status,
            headers=headers,
            body=body,
            purpose=purpose,
            truncated=truncated,
            elapsed_ms=entry.elapsed_ms,
        )
        self.pages.append(page)
        if self.recorder is not None:
            self.recorder.save(page)
        block = classify_block(status, headers, page.cookie_names, page.text)
        if block is not None:
            reason, detail = block
            self.stopped = StopInfo(reason=reason, url=url, detail=detail)
        return page

    def _wait(self, url: str) -> None:
        if self._last_request is None:
            return
        gap = self.delay_for(url)
        waited = self._clock() - self._last_request
        if waited < gap:
            self._sleep(gap - waited)

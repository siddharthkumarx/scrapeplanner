"""Run one analysis: decide which URLs to request, call the detectors, build the plan.

Request order (each step only if the budget, robots.txt and the block state allow):

1. ``/robots.txt``
2. the target page (redirects followed, each hop counted)
3. one sitemap: from robots.txt, else ``/sitemap.xml``
4. the most promising feed probe for the detected platform
5. one child sitemap, if step 3 found a sitemap index
6. the remaining feed probes, best first
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx

from scrapeplanner import __version__, config
from scrapeplanner.detectors import (
    antibot,
    embedded,
    feeds,
    platform,
    rendering,
    robots,
    structured,
)
from scrapeplanner.detectors import sitemaps as sitemap_detector
from scrapeplanner.fetch import (
    BlockedError,
    BudgetExceeded,
    FetchedPage,
    FetchError,
    PoliteFetcher,
    RobotsDisallowed,
    host_key,
)
from scrapeplanner.html import HtmlDoc
from scrapeplanner.models import (
    EmbeddedStateReport,
    FeedCandidate,
    FeedsReport,
    PageInfo,
    PlatformReport,
    RenderingReport,
    Report,
    SitemapReport,
    StopInfo,
    StructuredDataReport,
    ToolInfo,
)
from scrapeplanner.planner import Findings, build_plan
from scrapeplanner.record import Recorder

MAX_LINKED_FEED_PROBES = 2
_CHILD_HINTS = {
    "commerce": ("sitemap_products", "product-sitemap", "products", "product", "catalog"),
    "jobs": ("job", "career", "position"),
    "articles": ("post", "article", "news", "story"),
}


def _catalog_answered(probed: list[FeedCandidate]) -> bool:
    return any(
        c.kind == "shopify_products_json" and c.status == "ok" and (c.items_seen or 0) > 0
        for c in probed
    )


class InvalidURL(ValueError):
    pass


@dataclass
class Options:
    items: int = config.DEFAULT_ITEMS
    max_requests: int = config.MAX_REQUESTS
    delay: float = config.DELAY_SECONDS
    timeout: float = config.TIMEOUT_SECONDS
    record_dir: Path | None = None


def normalize_url(raw: str) -> str:
    """Add https:// when no scheme is given; only http(s) URLs with a host are allowed."""
    text = raw.strip()
    if "://" not in text:
        text = "https://" + text
    parts = urlsplit(text)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise InvalidURL(f"not an http(s) URL: {raw!r}")
    if parts.username or parts.password:
        raise InvalidURL("URLs with credentials are not supported (no logins)")
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path or "/", parts.query, ""))


def _is_html(page: FetchedPage) -> bool:
    if "html" in page.content_type:
        return True
    return page.content_type in ("", "text/plain") and page.body.lstrip()[:1] == b"<"


def _child_hints(platform_report: PlatformReport, key_types: list[str]) -> tuple[str, ...]:
    if platform_report.name in ("shopify", "woocommerce", "magento", "bigcommerce"):
        return _CHILD_HINTS["commerce"]
    if "JobPosting" in key_types:
        return _CHILD_HINTS["jobs"]
    if any("Article" in name or name == "BlogPosting" for name in key_types):
        return _CHILD_HINTS["articles"]
    return ()


class _Run:
    def __init__(self, url: str, options: Options, fetcher: PoliteFetcher) -> None:
        self.url = url
        self.options = options
        self.fetcher = fetcher
        self.page_info = PageInfo(url=url)
        self.page: FetchedPage | None = None
        self.doc: HtmlDoc | None = None
        self.error: StopInfo | None = None

    def get(self, url: str, purpose: str) -> FetchedPage | None:
        """Fetch, translating refusals into ``None`` (they are already logged)."""
        try:
            return self.fetcher.fetch(url, purpose)
        except FetchError:
            return None
        except httpx.HTTPError as exc:
            if purpose == "page":
                self.error = StopInfo(reason="error", url=url, detail=f"{type(exc).__name__}")
            return None

    # -- steps ------------------------------------------------------------

    def fetch_page(self) -> None:
        try:
            self.fetcher.load_robots(self.url)
        except (FetchError, httpx.HTTPError):
            return
        page = self.get(self.url, "page")
        if page is None:
            return
        self.page = page
        info = self.page_info
        info.fetched = True
        info.final_url = page.final_url
        info.status = page.status
        info.content_type = page.content_type or None
        info.bytes = len(page.body)
        if page.ok and _is_html(page):
            self.doc = HtmlDoc(page.text, page.final_url)
            info.title = self.doc.title
            info.lang = self.doc.lang

    @property
    def base(self) -> str:
        return self.page_info.final_url or self.url

    def fetch_sitemap(self) -> tuple[SitemapReport, list[str]]:
        origin = host_key(self.base)
        robots_state = self.fetcher.robots.get(origin)
        listed: list[str] = []
        if robots_state is not None and robots_state.parser is not None:
            listed = [str(url) for url in robots_state.parser.sitemaps]
        same_host = [url for url in listed if host_key(url) == origin]
        if same_host or listed:
            url, source = (same_host or listed)[0], "robots"
        else:
            url, source = f"{origin}/sitemap.xml", "default"
        report = SitemapReport(url=url, source=source)  # type: ignore[arg-type]
        page = self.get(url, "sitemap")
        if page is None:
            report.note = self._why_skipped(url) or "not fetched"
            return report, []
        return self._parse_sitemap(report, page)

    def _parse_sitemap(
        self, report: SitemapReport, page: FetchedPage
    ) -> tuple[SitemapReport, list[str]]:
        report.fetched = True
        report.status = page.status
        if not page.ok:
            report.note = f"HTTP {page.status}"
            return report, []
        parsed, children = sitemap_detector.parse(page.body, truncated=page.truncated)
        merged = parsed.model_copy(
            update={
                "url": report.url,
                "source": report.source,
                "fetched": True,
                "status": page.status,
            }
        )
        return merged, children

    def fetch_child_sitemap(
        self, report: SitemapReport, children: list[str], hints: tuple[str, ...]
    ) -> None:
        child_url = sitemap_detector.pick_child(children, hints)
        if child_url is None:
            return
        child = SitemapReport(url=child_url, source=report.source)
        page = self.get(child_url, "sitemap-child")
        if page is None:
            child.note = self._why_skipped(child_url) or "not fetched"
        else:
            child, _ = self._parse_sitemap(child, page)
        report.child = child

    def probe(self, candidate: FeedCandidate) -> FeedCandidate:
        try:
            page = self.fetcher.fetch(candidate.url, f"feed:{candidate.kind}")
        except RobotsDisallowed:
            return candidate.model_copy(update={"status": "skipped_robots"})
        except BudgetExceeded:
            return candidate.model_copy(update={"status": "skipped_budget"})
        except BlockedError:
            return candidate.model_copy(update={"status": "blocked"})
        except httpx.HTTPError as exc:
            return candidate.model_copy(
                update={"status": "invalid", "note": f"{type(exc).__name__}"}
            )
        result = feeds.evaluate(
            candidate, page.status, page.content_type, page.text, dict(page.headers)
        )
        if self.fetcher.stopped is not None and self.fetcher.stopped.url == page.final_url:
            result.status = "blocked"
        elif page.truncated and result.status == "invalid":
            result.note = "response larger than the 5 MB cap; not parsed"
        return result

    def _why_skipped(self, url: str) -> str | None:
        for skipped in reversed(self.fetcher.skipped):
            if skipped.url == url:
                return {
                    "robots": "disallowed by robots.txt",
                    "budget": "request budget used up",
                    "blocked": "run stopped at a block",
                    "crawl_delay": "crawl-delay above the cap",
                }[skipped.reason]
        return None


def analyze(
    raw_url: str,
    options: Options | None = None,
    *,
    transport: httpx.BaseTransport | None = None,
    sleep: Callable[[float], None] = time.sleep,
    now: datetime | None = None,
) -> Report:
    options = options or Options()
    url = normalize_url(raw_url)
    started = now or datetime.now(UTC)
    t0 = time.perf_counter()
    recorder = Recorder(options.record_dir) if options.record_dir else None
    fetcher = PoliteFetcher(
        max_requests=options.max_requests,
        delay=options.delay,
        timeout=options.timeout,
        transport=transport,
        recorder=recorder,
        sleep=sleep,
    )
    with fetcher:
        run = _Run(url, options, fetcher)
        run.fetch_page()

        platform_report = PlatformReport()
        structured_report = StructuredDataReport()
        embedded_report = EmbeddedStateReport()
        rendering_report = RenderingReport()
        if run.page is not None and run.doc is not None:
            platform_report = platform.detect(run.page.headers, run.page.cookie_names, run.doc)
            structured_report = structured.detect(run.doc)
            embedded_report = embedded.detect(run.doc)
            rendering_report = rendering.detect(run.doc, structured_report, embedded_report)
            stop = fetcher.stopped
            if stop is not None and stop.url == run.page.final_url:
                # The "page" was a block or challenge page: nothing of the site to look at.
                platform_report.checked = False
        elif run.page is not None:
            # Headers only (blocked or non-HTML page): a name is possible, a full check is not.
            platform_report = platform.detect(
                run.page.headers, run.page.cookie_names, HtmlDoc("", run.base)
            )
            platform_report.checked = False

        sitemap_report = SitemapReport()
        children: list[str] = []
        candidates: list[FeedCandidate] = []
        if run.page is not None and run.page.ok:
            sitemap_report, children = run.fetch_sitemap()
            candidates = feeds.candidates(platform_report, run.doc, run.base)
            probed: list[FeedCandidate] = []
            linked_probes = 0
            for index, candidate in enumerate(candidates):
                if index == 1 and children:
                    hints = _child_hints(platform_report, structured_report.key_types)
                    run.fetch_child_sitemap(sitemap_report, children, hints)
                    children = []
                generic = candidate.kind in ("rss", "atom", "json_feed", "json_link")
                if generic and linked_probes >= MAX_LINKED_FEED_PROBES:
                    probed.append(candidate)
                    continue
                if candidate.kind == "shopify_product_js" and _catalog_answered(probed):
                    # products.json already returned the products; the per-product JSON
                    # would add nothing to the plan, so keep the request (I-009).
                    probed.append(
                        candidate.model_copy(
                            update={"note": "not requested: /products.json already answered"}
                        )
                    )
                    continue
                linked_probes += generic
                probed.append(run.probe(candidate))
            if children:
                hints = _child_hints(platform_report, structured_report.key_types)
                run.fetch_child_sitemap(sitemap_report, children, hints)
            candidates = probed

        origin = host_key(run.base)
        used_urls = [run.base]
        if sitemap_report.url:
            used_urls.append(sitemap_report.url)
        used_urls.extend(candidate.url for candidate in candidates)
        if sitemap_report.child and sitemap_report.child.sample_urls:
            used_urls.append(sitemap_report.child.sample_urls[0])
        elif sitemap_report.sample_urls and sitemap_report.kind == "urlset":
            used_urls.append(sitemap_report.sample_urls[0])
        robots_report = robots.build_report(
            f"{origin}/robots.txt",
            fetcher.robots.get(origin),
            [u for u in used_urls if host_key(u) == origin],
        )

        antibot_report = antibot.merge(
            (
                page.final_url,
                antibot.detect(page.status, page.headers, page.cookie_names, page.text),
            )
            for page in fetcher.pages
        )
        stopped = fetcher.stopped or run.error
        plan = build_plan(
            Findings(
                page=run.page_info,
                robots=robots_report,
                sitemap=sitemap_report,
                platform=platform_report,
                antibot=antibot_report,
                structured=structured_report,
                embedded=embedded_report,
                rendering=rendering_report,
                feeds=FeedsReport(candidates=candidates),
                stopped=stopped,
                items=options.items,
                base_delay=options.delay,
                today=started.date(),
            )
        )
        return Report(
            tool=ToolInfo(version=__version__, user_agent=config.USER_AGENT),
            input_url=url,
            site=urlsplit(run.base).netloc,
            started_at=started.isoformat(timespec="seconds"),
            duration_seconds=round(time.perf_counter() - t0, 2),
            max_requests=options.max_requests,
            requests_used=fetcher.requests_used,
            requests=fetcher.log,
            skipped=fetcher.skipped,
            stopped=stopped,
            page=run.page_info,
            robots=robots_report,
            sitemap=sitemap_report,
            platform=platform_report,
            antibot=antibot_report,
            structured=structured_report,
            embedded=embedded_report,
            rendering=rendering_report,
            feeds=FeedsReport(candidates=candidates),
            plan=plan,
        )

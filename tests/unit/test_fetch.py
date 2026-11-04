from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import httpx
import pytest

from scrapeplanner import config
from scrapeplanner.fetch import (
    BlockedError,
    BudgetExceeded,
    PoliteFetcher,
    RobotsDisallowed,
    decode_body,
)
from scrapeplanner.record import Recorder, ReplayTransport, load_exchanges
from tests.sitekit import Route, transport

ROBOTS = "https://site.test/robots.txt"
TXT = {"content-type": "text/plain"}
HTML = {"content-type": "text/html"}


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(round(seconds, 3))
        self.now += seconds


def make(routes: Mapping[str, Route], seen: list[str] | None = None, **kwargs: object) -> PoliteFetcher:
    clock = FakeClock()
    return PoliteFetcher(
        transport=transport(routes, seen),
        sleep=clock.sleep,
        clock=clock,
        **kwargs,  # type: ignore[arg-type]
    )


def test_robots_first_then_page_with_user_agent() -> None:
    agents: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        agents.append(request.headers["user-agent"])
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, html="<p>hi</p>")

    with PoliteFetcher(transport=httpx.MockTransport(handler), sleep=lambda _: None) as f:
        page = f.fetch("https://site.test/", "page")
    assert page.status == 200
    assert [entry.purpose for entry in f.log] == ["robots", "page"]
    assert set(agents) == {config.USER_AGENT}
    assert config.PROJECT_URL in config.USER_AGENT


def test_disallowed_url_is_never_requested() -> None:
    seen: list[str] = []
    routes = {ROBOTS: (200, TXT, "User-agent: *\nDisallow: /private\n")}
    f = make(routes, seen)
    with pytest.raises(RobotsDisallowed):
        f.fetch("https://site.test/private/x", "page")
    assert seen == [ROBOTS]
    assert f.skipped[0].reason == "robots"


def test_rules_for_our_token_apply() -> None:
    robots = "User-agent: scrapeplanner\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
    f = make({ROBOTS: (200, TXT, robots)})
    with pytest.raises(RobotsDisallowed):
        f.fetch("https://site.test/", "page")


@pytest.mark.parametrize(("status", "allowed"), [(404, True), (403, False), (500, False)])
def test_robots_status_semantics(status: int, allowed: bool) -> None:
    f = make({ROBOTS: (status, TXT, "")})
    state = f.load_robots("https://site.test/")
    assert state.allowed("https://site.test/anything") is allowed


def test_budget_counts_every_request() -> None:
    routes = {ROBOTS: (404, TXT, "")}
    routes.update({f"https://site.test/{i}": (200, HTML, "ok") for i in range(5)})
    f = make(routes, max_requests=3)
    f.fetch("https://site.test/0", "p")
    f.fetch("https://site.test/1", "p")
    with pytest.raises(BudgetExceeded):
        f.fetch("https://site.test/2", "p")
    assert f.requests_used == 3
    assert f.skipped[-1].reason == "budget"


def test_redirect_hops_count_and_are_followed() -> None:
    routes = {
        ROBOTS: (404, TXT, ""),
        "https://site.test/": (301, {"location": "/home"}, ""),
        "https://site.test/home": (200, HTML, "home"),
    }
    f = make(routes)
    page = f.fetch("https://site.test/", "page")
    assert page.final_url == "https://site.test/home"
    assert page.redirects == ["https://site.test/"]
    assert f.requests_used == 3


def test_cross_host_redirect_loads_that_hosts_robots() -> None:
    seen: list[str] = []
    routes = {
        ROBOTS: (404, TXT, ""),
        "https://site.test/": (301, {"location": "https://www.site.test/"}, ""),
        "https://www.site.test/robots.txt": (200, TXT, "User-agent: *\nDisallow: /\n"),
    }
    f = make(routes, seen)
    with pytest.raises(RobotsDisallowed):
        f.fetch("https://site.test/", "page")
    assert "https://www.site.test/" not in seen


def test_delay_and_crawl_delay() -> None:
    routes = {ROBOTS: (200, TXT, "User-agent: *\nCrawl-delay: 4\n")}
    routes.update({f"https://site.test/{i}": (200, HTML, "ok") for i in range(3)})
    clock = FakeClock()
    f = PoliteFetcher(transport=transport(routes), sleep=clock.sleep, clock=clock, delay=1.0)
    f.fetch("https://site.test/0", "p")
    f.fetch("https://site.test/1", "p")
    assert clock.slept == [4.0, 4.0]


def test_crawl_delay_above_cap_stops() -> None:
    routes = {ROBOTS: (200, TXT, "User-agent: *\nCrawl-delay: 120\n")}
    f = make(routes)
    with pytest.raises(BlockedError):
        f.fetch("https://site.test/", "page")
    assert f.stopped is not None
    assert f.stopped.reason == "crawl_delay"
    assert f.requests_used == 1


def test_stops_at_first_block() -> None:
    seen: list[str] = []
    routes = {
        ROBOTS: (404, TXT, ""),
        "https://site.test/": (403, {"server": "cloudflare", "cf-ray": "1"}, "denied"),
    }
    f = make(routes, seen)
    page = f.fetch("https://site.test/", "page")
    assert page.status == 403
    assert f.stopped is not None
    assert f.stopped.reason == "blocked"
    with pytest.raises(BlockedError):
        f.fetch("https://site.test/other", "page")
    assert seen == [ROBOTS, "https://site.test/"]


def test_429_stops() -> None:
    routes = {ROBOTS: (404, TXT, ""), "https://site.test/": (429, HTML, "slow down")}
    f = make(routes)
    f.fetch("https://site.test/", "page")
    assert f.stopped is not None
    assert f.stopped.reason == "rate_limited"


def test_no_cookies_sent_back() -> None:
    sent: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request.headers.get("cookie"))
        return httpx.Response(200, headers={"set-cookie": "sid=abc; Path=/"}, text="x")

    with PoliteFetcher(transport=httpx.MockTransport(handler), sleep=lambda _: None) as f:
        f.fetch("https://site.test/a", "p")
        f.fetch("https://site.test/b", "p")
    assert sent == [None, None, None]


def test_body_cap() -> None:
    routes = {ROBOTS: (404, TXT, ""), "https://site.test/": (200, HTML, "x" * 5000)}
    f = make(routes, max_body_bytes=1000)
    page = f.fetch("https://site.test/", "page")
    assert page.truncated
    assert len(page.body) == 1000


def test_budget_limits() -> None:
    with pytest.raises(ValueError, match="max_requests"):
        PoliteFetcher(max_requests=config.MAX_REQUESTS_CAP + 1)


def test_decode_body_charsets() -> None:
    assert decode_body("café".encode("latin-1"), "text/html; charset=latin-1") == "café"
    meta = b'<meta charset="windows-1252"><p>\xe9</p>'
    assert "é" in decode_body(meta, "text/html")
    assert decode_body(b"\xff\xfe", "") == "��"


def test_record_and_replay_round_trip(tmp_path: Path) -> None:
    routes = {
        ROBOTS: (404, TXT, ""),
        "https://site.test/": (200, {**HTML, "set-cookie": "_px3=secret; Path=/"}, "<p>hi</p>"),
    }
    with PoliteFetcher(
        transport=transport(routes), recorder=Recorder(tmp_path), sleep=lambda _: None
    ) as f:
        f.fetch("https://site.test/", "page")
    entries = load_exchanges(tmp_path)
    assert [e["url"] for e in entries] == [ROBOTS, "https://site.test/"]
    raw = json.dumps(entries)
    assert "secret" not in raw
    assert "_px3=<redacted>" in raw

    replay = ReplayTransport(tmp_path)
    with PoliteFetcher(transport=replay, sleep=lambda _: None) as f:
        page = f.fetch("https://site.test/", "page")
        missing = f.fetch("https://site.test/other", "page")
    assert page.text == "<p>hi</p>"
    assert page.cookie_names == ["_px3"]
    assert missing.status == 599
    assert replay.misses == ["https://site.test/other"]

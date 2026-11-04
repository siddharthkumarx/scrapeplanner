"""robots.txt report: rules for the paths the plan would use, crawl-delay, sitemaps."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from scrapeplanner import config
from scrapeplanner.models import RobotsReport

if TYPE_CHECKING:
    from scrapeplanner.fetch import HostRobots


def _path_key(url: str) -> str:
    parts = urlsplit(url)
    return parts.path + (f"?{parts.query}" if parts.query else "") or "/"


def build_report(robots_url: str, robots: HostRobots | None, urls: Iterable[str]) -> RobotsReport:
    """Summarise robots.txt for ``urls`` (absolute URLs on the robots host)."""
    report = RobotsReport(url=robots_url)
    if robots is None:
        report.note = "robots.txt not fetched"
        return report
    report.fetched = robots.status is not None
    report.status = robots.status
    report.found = robots.parser is not None
    report.disallow_all = robots.disallow_all
    report.note = robots.note
    for url in urls:
        report.paths.setdefault(_path_key(url), robots.allowed(url))
    if robots.parser is not None:
        report.crawl_delay = robots.crawl_delay
        rate = robots.parser.request_rate(config.UA_TOKEN)
        if rate is not None:
            report.request_rate = f"{rate.requests}/{rate.seconds}s"
        report.sitemaps = [str(url) for url in robots.parser.sitemaps]
    return report

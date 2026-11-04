"""``--profile PATH``: a starter profile.yaml for a collector (method, URLs, fields, rate).

The profile is a starting point to review, not a finished scraper config. It
always carries the polite settings (rate, user agent, stop rules) the plan
used, so a collector built from it stays inside them.
"""

from __future__ import annotations

from typing import Any

import yaml

from scrapeplanner import config
from scrapeplanner.models import Report

PROFILE_VERSION = 1


def build_profile(report: Report) -> dict[str, Any]:
    plan = report.plan
    method = next((m for m in plan.methods if m.name == plan.recommended), None)
    sitemap_url = None
    if report.sitemap.kind in ("urlset", "sitemapindex"):
        sitemap_url = report.sitemap.child.url if report.sitemap.child else report.sitemap.url
    source: dict[str, Any] = {
        "urls": method.urls if method else [],
    }
    if method and any("{page}" in url for url in method.urls):
        source["pagination"] = {"param": "page", "start": 1, "stop_when": "empty page"}
    if (
        sitemap_url
        and method
        and method.name in ("structured_data", "embedded_json", "html", "browser")
    ):
        source["discover_from_sitemap"] = sitemap_url
    profile: dict[str, Any] = {
        "profile_version": PROFILE_VERSION,
        "generated_by": f"scrapeplanner {report.tool.version}",
        "generated_at": report.started_at,
        "site": f"https://{report.site}",
        "verdict": plan.verdict,
        "method": plan.recommended,
        "source": source,
        "fields": method.fields if method else [],
        "rate": {
            "delay_seconds": plan.rate.delay_seconds,
            "concurrency": plan.rate.concurrency,
            "max_requests_per_day": plan.rate.max_requests_per_day,
            "reason": plan.rate.reason,
        },
        "politeness": {
            "user_agent": config.USER_AGENT,
            "respect_robots_txt": True,
            "crawl_delay": report.robots.crawl_delay,
            "stop_on": ["challenge page", "HTTP 401", "HTTP 403", "HTTP 429", "HTTP 503"],
            "no": ["proxies", "CAPTCHA solving", "logins", "personal data"],
        },
        "estimate": {
            "items": plan.items,
            "requests": method.est_requests if method else None,
            "hours": method.est_hours if method else None,
        },
        "notes": (method.notes if method else []) + plan.risks,
    }
    if plan.verdict == "not_a_fit":
        profile["method"] = None
        profile["source"] = {"urls": []}
        profile["fields"] = []
        profile["notes"] = [*plan.risks, *plan.next_steps]
    return profile


def to_yaml(report: Report) -> str:
    header = (
        "# Starter profile written by scrapeplanner. Review before use.\n"
        "# Every value comes from one analysis run; re-run to refresh it.\n"
    )
    body = yaml.safe_dump(build_profile(report), sort_keys=False, allow_unicode=True, width=100)
    return header + body

"""Turn detector findings into a plan: methods cheapest first, rate, estimate, risks.

Every number the planner prints is either measured (counts from the page,
the sitemap or a feed) or derived from a stated rule below. The rules:

* polite delay = max(1 s, the --delay option, robots crawl-delay, robots
  request-rate); 5 s when a bot-management vendor is in front of the site or
  the site answered 429 during the run;
* request estimate = pages needed for N items at the method's page size, plus
  the sitemap files needed to discover detail pages;
* time = requests x delay, one request at a time.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlsplit

from scrapeplanner.models import (
    METHOD_LABELS,
    PLATFORM_LABELS,
    VENDOR_LABELS,
    AntiBotReport,
    EmbeddedStateReport,
    FeedCandidate,
    FeedsReport,
    FitVerdict,
    MethodName,
    MethodPlan,
    PageInfo,
    Plan,
    PlatformReport,
    RatePlan,
    RenderingReport,
    RobotsReport,
    SitemapReport,
    StopInfo,
    StructuredDataReport,
    platform_label,
)

BOT_MANAGED_DELAY = 5.0
BOT_MANAGED_DAILY_CAP = 5_000
STALE_SITEMAP_DAYS = 365
MIN_DATA_BLOB_BYTES = 5_000
_FEED_RANK = {
    "greenhouse_api": 0,
    "lever_api": 0,
    "ashby_api": 0,
    "ckan_api": 0,
    "shopify_products_json": 0,
    "woo_store_api": 1,
    "wp_rest": 2,
    "json_feed": 3,
    "rss": 4,
    "atom": 5,
    "json_link": 6,
    "shopify_product_js": 7,
}


@dataclass
class Findings:
    page: PageInfo
    robots: RobotsReport
    sitemap: SitemapReport
    platform: PlatformReport
    antibot: AntiBotReport
    structured: StructuredDataReport
    embedded: EmbeddedStateReport
    rendering: RenderingReport
    feeds: FeedsReport
    stopped: StopInfo | None
    items: int
    base_delay: float
    today: date


def bot_managed_vendors(antibot: AntiBotReport) -> list[str]:
    """Vendors whose bot management (not just a CDN) is in front of the site."""
    return [hit.vendor for hit in antibot.vendors if hit.bot_management]


def _rate(f: Findings) -> RatePlan:
    delay = max(1.0, f.base_delay)
    reasons = [f"default {delay:g}s between requests"]
    if f.robots.crawl_delay and f.robots.crawl_delay > delay:
        delay = f.robots.crawl_delay
        reasons = [f"robots.txt crawl-delay {delay:g}s"]
    if f.robots.request_rate:
        requests, _, seconds = f.robots.request_rate.rstrip("s").partition("/")
        if requests.isdigit() and seconds.isdigit() and int(requests) > 0:
            per = int(seconds) / int(requests)
            if per > delay:
                delay = per
                reasons = [f"robots.txt request-rate {f.robots.request_rate}"]
    cap = None
    managed = bot_managed_vendors(f.antibot)
    if managed and delay < BOT_MANAGED_DELAY:
        delay = BOT_MANAGED_DELAY
        cap = BOT_MANAGED_DAILY_CAP
        names = ", ".join(VENDOR_LABELS[name] for name in managed)
        reasons = [f"{names} bot management in front of the site: slow and capped"]
    elif managed:
        cap = BOT_MANAGED_DAILY_CAP
    if f.stopped is not None and f.stopped.reason == "rate_limited" and delay < BOT_MANAGED_DELAY:
        delay = BOT_MANAGED_DELAY
        reasons = [f"the site answered 429 during this run at {max(1.0, f.base_delay):g}s spacing"]
    return RatePlan(
        delay_seconds=delay, concurrency=1, max_requests_per_day=cap, reason="; ".join(reasons)
    )


def _hours(requests: int | None, delay: float) -> float | None:
    if requests is None:
        return None
    return round(requests * delay / 3600, 2)


def _discovery(f: Findings, items: int) -> tuple[int, str]:
    """Requests needed to find ``items`` detail-page URLs, with a description."""
    sitemap = f.sitemap
    per_file = None
    if sitemap.child and sitemap.child.url_count:
        per_file = sitemap.child.url_count
    elif sitemap.kind == "urlset" and sitemap.url_count:
        per_file = sitemap.url_count
    if per_file:
        files = math.ceil(items / per_file)
        extra = 1 if sitemap.kind == "sitemapindex" else 0
        return files + extra, f"URLs from the sitemap (~{per_file:,} per file)"
    return 0, "URLs from listing pages (count not measured)"


def _best_feed(feeds: FeedsReport) -> FeedCandidate | None:
    ok = [c for c in feeds.candidates if c.status == "ok"]
    ok.sort(key=lambda c: _FEED_RANK.get(c.kind, 99))
    return ok[0] if ok else None


def _feed_method(f: Findings, items: int, delay: float) -> MethodPlan:
    feed = _best_feed(f.feeds)
    if feed is None:
        tried = [c for c in f.feeds.candidates if c.status != "linked"]
        summary = "no public feed answered" if tried else "no public feed found"
        if any(c.status == "skipped_robots" for c in f.feeds.candidates):
            summary += " (some disallowed by robots.txt)"
        return MethodPlan(name="feed_api", usable=False, summary=summary)
    notes: list[str] = []
    partial = False
    urls = [feed.url]
    if feed.kind == "shopify_products_json":
        seen = feed.items_seen or 0
        if seen < (feed.page_size or 250):
            est = 1
            notes.append(f"the store lists {seen} products: one request returns all of them")
        else:
            est = math.ceil(items / (feed.page_size or 250))
        urls = [feed.url.split("?")[0] + "?limit=250&page={page}"]
        summary = "Shopify /products.json: products, variants, prices, images"
    elif feed.kind in ("woo_store_api", "wp_rest"):
        size = feed.page_size or 100
        wanted = min(items, feed.total_items) if feed.total_items is not None else items
        est = max(1, math.ceil(wanted / size))
        if feed.total_items is not None:
            notes.append(f"endpoint reports {feed.total_items} records in total")
        base = feed.url.split("?")[0]
        urls = [f"{base}?per_page={size}&page={{page}}"]
        summary = (
            "WooCommerce Store API: products with prices and stock"
            if feed.kind == "woo_store_api"
            else "WordPress REST API: posts"
        )
    elif feed.kind in ("greenhouse_api", "lever_api", "ashby_api"):
        est = 1
        total = feed.total_items or 0
        notes.append(f"one request returns all {total} open jobs; the board lists no more")
        name = {"greenhouse_api": "Greenhouse", "lever_api": "Lever", "ashby_api": "Ashby"}
        summary = f"{name[feed.kind]} job-board API: every open job with its fields"
    elif feed.kind == "ckan_api":
        size = feed.page_size or 1000
        wanted = min(items, feed.total_items) if feed.total_items is not None else items
        est = max(1, math.ceil(wanted / size))
        if feed.total_items is not None:
            notes.append(f"the catalog reports {feed.total_items:,} datasets in total")
        base = feed.url.split("?")[0]
        urls = [f"{base}?rows={size}&start={{offset}}"]
        summary = "CKAN API (package_search): dataset metadata and resource links"
    elif feed.kind == "shopify_product_js":
        discovery, how = _discovery(f, items)
        est = items + discovery
        notes.append(f"one request per product; {how}")
        summary = "Shopify /products/<handle>.js per product"
    else:
        est = 1
        partial = (feed.items_seen or 0) < items
        notes.append(
            f"a feed returns only its latest {feed.items_seen or 0} entries; poll it for new ones"
        )
        summary = f"{feed.kind.replace('_', ' ')} feed"
    return MethodPlan(
        partial=partial,
        name="feed_api",
        usable=True,
        summary=summary,
        urls=urls,
        fields=feed.fields,
        est_requests=est,
        est_hours=_hours(est, delay),
        notes=notes,
    )


def _per_page_method(
    name: MethodName,
    f: Findings,
    items: int,
    delay: float,
    per_page: int,
    summary: str,
    fields: list[str],
    notes: list[str],
) -> MethodPlan:
    if per_page > 1:
        est = math.ceil(items / per_page)
        notes = [*notes, f"{per_page} records on the analysed page: about {est} listing pages"]
        urls = [f.page.final_url or f.page.url]
    else:
        discovery, how = _discovery(f, items)
        est = items + discovery
        notes = [*notes, f"one detail page per record; {how}"]
        urls = f.sitemap.child.sample_urls[:3] if f.sitemap.child else f.sitemap.sample_urls[:3]
        urls = urls or [f.page.final_url or f.page.url]
    return MethodPlan(
        name=name,
        usable=True,
        summary=summary,
        urls=urls,
        fields=fields,
        est_requests=est,
        est_hours=_hours(est, delay),
        notes=notes,
    )


def _structured_method(f: Findings, items: int, delay: float) -> MethodPlan:
    s = f.structured
    if not s.items:
        others = ", ".join(sorted(s.types)) if s.types else "none"
        return MethodPlan(
            name="structured_data",
            usable=False,
            summary=f"no schema.org records on this page (types seen: {others})",
        )
    top = s.items[0]
    records = [item for item in s.items if item.type not in ("ItemList", "OfferCatalog")]
    per_page = max((item.count for item in records), default=1)
    if top.type in ("ItemList", "OfferCatalog") and records:
        top = max(records, key=lambda item: item.count)
    summary = f"{top.type} in {top.source} ({top.count} on the page)"
    return _per_page_method("structured_data", f, items, delay, per_page, summary, top.fields, [])


def _embedded_method(f: Findings, items: int, delay: float) -> MethodPlan:
    blobs = [b for b in f.embedded.blobs if b.bytes >= MIN_DATA_BLOB_BYTES]
    if not blobs:
        return MethodPlan(name="embedded_json", usable=False, summary="no large inline state")
    blob = blobs[0]
    notes = []
    if blob.kind == "next_data":
        notes.append("buildId changes on every deploy; read it from the page, never hard-code it")
    if blob.kind == "next_flight":
        notes.append("React Server Components payload: a custom parser is needed")
    if blob.kind in ("nuxt_data",):
        notes.append("Nuxt 3 devalue format: decode the array references before use")
    summary = f"{blob.locator} ({blob.bytes:,} bytes)"
    return _per_page_method("embedded_json", f, items, delay, 1, summary, blob.keys, notes)


def _html_method(f: Findings, items: int, delay: float) -> MethodPlan:
    if not f.page.fetched or f.rendering.verdict in ("unknown", "browser_likely"):
        reason = "page not analysed" if not f.page.fetched else "little content without JavaScript"
        return MethodPlan(name="html", usable=False, summary=reason)
    summary = f"CSS selectors on server-rendered HTML ({f.rendering.text_chars:,} chars of text)"
    plan = _per_page_method("html", f, items, delay, 1, summary, [], [])
    plan.notes.append("selectors break on redesigns; prefer the methods above when usable")
    return plan


def _browser_method(f: Findings, items: int, delay: float, needed: bool) -> MethodPlan:
    if not needed:
        return MethodPlan(
            name="browser", usable=False, summary="not needed: data is available without JavaScript"
        )
    discovery, how = _discovery(f, items)
    est = items + discovery
    return MethodPlan(
        name="browser",
        usable=True,
        summary="render pages in a headless browser (highest cost)",
        urls=[f.page.final_url or f.page.url],
        est_requests=est,
        est_hours=_hours(est, delay),
        notes=[
            f"page loads only; each load also fetches scripts and API calls; {how}",
            "check the browser's network tab first: the page may call a JSON API",
        ],
    )


def build_plan(f: Findings) -> Plan:
    items = max(1, f.items)
    rate = _rate(f)
    delay = rate.delay_seconds
    risks: list[str] = []
    steps: list[str] = []
    managed = bot_managed_vendors(f.antibot)

    verdict: FitVerdict = "unknown"
    stop = f.stopped
    page_url = f.page.final_url or f.page.url
    # A challenge anywhere, or a block of the page itself, rules the site out. A plain
    # 403/429 on one optional probe stops the run but the page we already have still counts.
    fatal = stop is not None and (
        stop.reason == "challenge"
        or (
            stop.reason in ("blocked", "rate_limited")
            and (stop.url == page_url or not f.page.fetched or not (f.page.status or 0) < 300)
        )
    )
    if f.robots.disallow_all:
        verdict = "not_a_fit"
        risks.append(
            f"robots.txt could not be read ({f.robots.note or 'error'}): treated as "
            "'disallow everything'"
        )
    if f.robots.paths and not f.robots.paths.get(_path(f.page.url), True):
        verdict = "not_a_fit"
        risks.append("robots.txt disallows the requested page for our user agent")
    if fatal and stop is not None:
        verdict = "not_a_fit"
        risks.append(f"stopped at the first block: {stop.detail} ({stop.url})")
        steps.append(
            "Ask the site owner for access, an API key or a data export; "
            "do not try to get past the block"
        )
    elif stop is not None and stop.reason in ("blocked", "rate_limited"):
        risks.append(
            f"the site refused {stop.url} ({stop.detail}); the run stopped there, and a "
            "collector must stop at any 403 or 429 too"
        )
    if f.stopped is not None and f.stopped.reason == "crawl_delay":
        verdict = "not_a_fit"
        risks.append(f.stopped.detail)

    methods = [
        _feed_method(f, items, delay),
        _structured_method(f, items, delay),
        _embedded_method(f, items, delay),
        _html_method(f, items, delay),
    ]
    found_any = any(m.usable and not m.partial for m in methods)
    browser_needed = f.page.fetched and not found_any
    methods.append(_browser_method(f, items, delay, browser_needed))
    if verdict == "not_a_fit":
        for method in methods:
            method.usable = False
            method.est_requests = None
            method.est_hours = None
    # Cheapest method that reaches all N items; a partial one only if nothing else works.
    recommended = next((m.name for m in methods if m.usable and not m.partial), None)
    if recommended is None:
        recommended = next((m.name for m in methods if m.usable), None)

    if verdict != "not_a_fit":
        if not f.page.fetched:
            verdict = "unknown"
            risks.append("the page could not be fetched; nothing to plan from")
        elif managed or recommended == "browser" or stop is not None:
            verdict = "caution"
        else:
            verdict = "good"

    for name in managed:
        hit = next(h for h in f.antibot.vendors if h.vendor == name)
        if hit.status == "present":
            risks.append(
                f"{VENDOR_LABELS[name]} bot management is in front of the site: keep to the "
                "rate below and stop at the first challenge"
            )
    disallowed = [path for path, ok in f.robots.paths.items() if not ok]
    if disallowed and verdict != "not_a_fit":
        risks.append("robots.txt disallows: " + ", ".join(disallowed[:5]))
    if f.robots.crawl_delay:
        risks.append(f"robots.txt asks for {f.robots.crawl_delay:g}s between requests")
    stale = _stale(f.sitemap, f.today)
    if stale:
        risks.append(stale)
    if f.page.fetched and f.platform.checked and f.platform.name == "unknown":
        risks.append("platform not recognised: no platform-specific feed was probed")
    if recommended in ("html", "browser", "embedded_json"):
        risks.append("page-layout methods break when the site changes; monitor field coverage")
    if f.structured.key_types and any(
        t in ("Review", "JobPosting") for t in f.structured.key_types
    ):
        risks.append("reviews and job posts can name people: collect only the fields you need")
    if any(c.status == "skipped_budget" for c in f.feeds.candidates):
        risks.append("request budget ran out before every feed was probed (see --max-requests)")

    if verdict in ("good", "caution"):
        steps.append("Check the site's terms of service for data collection and reuse")
        steps.append("Write a starter profile with --profile profile.yaml and review it")
        if recommended == "browser":
            steps.append("Look for a JSON API in the browser's network tab before using a browser")
    if verdict == "caution" and managed:
        steps.append("If you need volume, ask the owner for an API or a feed")

    return Plan(
        verdict=verdict,
        recommended=recommended,
        items=items,
        rate=rate,
        methods=methods,
        risks=risks,
        next_steps=steps,
    )


def _path(url: str) -> str:
    parts = urlsplit(url)
    return (parts.path or "/") + (f"?{parts.query}" if parts.query else "")


def _stale(sitemap: SitemapReport, today: date) -> str | None:
    newest = sitemap.child.newest_lastmod if sitemap.child else sitemap.newest_lastmod
    if not newest:
        return None
    try:
        age = (today - date.fromisoformat(newest)).days
    except ValueError:
        return None
    if age > STALE_SITEMAP_DAYS:
        return f"sitemap looks stale: newest lastmod is {newest}"
    return None


def describe(platform: PlatformReport) -> str:
    """'Shopify (+ Next.js)', 'unknown', or 'not checked' when no page was analysed."""
    if not platform.checked and platform.name == "unknown":
        return "not checked (no page to analyse)"
    label = PLATFORM_LABELS[platform.name]
    if platform.frameworks:
        return f"{label} (+ {', '.join(platform_label(n) for n in platform.frameworks)})"
    return label


__all__ = ["METHOD_LABELS", "Findings", "bot_managed_vendors", "build_plan", "describe"]

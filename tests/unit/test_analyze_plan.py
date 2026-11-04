"""Analyzer, planner and outputs on small fake sites."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from scrapeplanner import analyze as analyze_module
from scrapeplanner import cli
from scrapeplanner.analyze import InvalidURL, Options, analyze, normalize_url
from scrapeplanner.models import Report
from scrapeplanner.output.json_out import to_json
from scrapeplanner.output.profile import build_profile, to_yaml
from tests.sitekit import Route, transport

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)
TXT = {"content-type": "text/plain"}
HTML = {"content-type": "text/html; charset=utf-8"}
XML = {"content-type": "application/xml"}
JSON = {"content-type": "application/json"}
BODY_TEXT = "<p>Plenty of server-rendered words here.</p>" * 40


def run(routes: dict[str, Route], url: str = "https://shop.test/", **options: int) -> Report:
    seen: list[str] = []
    report = analyze(
        url,
        Options(**options),  # type: ignore[arg-type]
        transport=transport(routes, seen),
        sleep=lambda _: None,
        now=NOW,
    )
    assert report.requests_used == len(seen)
    return report


def shopify_routes(products: int = 40) -> dict[str, Route]:
    home = (
        '<html><head><script src="//cdn.shopify.com/a.js"></script>'
        "<script>Shopify.theme = {};</script></head><body>"
        f'<a href="/products/red-cap">cap</a>{BODY_TEXT}</body></html>'
    )
    index = (
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        "<sitemap><loc>https://shop.test/sitemap_pages_1.xml</loc></sitemap>"
        "<sitemap><loc>https://shop.test/sitemap_products_1.xml</loc></sitemap></sitemapindex>"
    )
    child = (
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<url><loc>https://shop.test/products/p{i}</loc></url>" for i in range(50))
        + "</urlset>"
    )
    catalog = {"products": [{"id": i, "title": "t", "variants": []} for i in range(products)]}
    return {
        "https://shop.test/robots.txt": (
            200,
            TXT,
            "User-agent: *\nDisallow: /cart\nSitemap: https://shop.test/sitemap.xml\n",
        ),
        "https://shop.test/": (200, {**HTML, "x-shopid": "7"}, home),
        "https://shop.test/sitemap.xml": (200, XML, index),
        "https://shop.test/sitemap_products_1.xml": (200, XML, child),
        "https://shop.test/products.json?limit=250": (200, JSON, json.dumps(catalog)),
        "https://shop.test/products/red-cap.js": (200, JSON, '{"id":1,"variants":[{}]}'),
    }


def test_normalize_url() -> None:
    assert normalize_url("Example.com") == "https://example.com/"
    assert normalize_url("http://a.test/x?y=1#frag") == "http://a.test/x?y=1"
    with pytest.raises(InvalidURL):
        normalize_url("ftp://a.test/")
    with pytest.raises(InvalidURL):
        normalize_url("https://user:pw@a.test/")


def test_shopify_plan() -> None:
    report = run(shopify_routes())
    assert report.platform.name == "shopify"
    assert [r.purpose for r in report.requests] == [
        "robots",
        "page",
        "sitemap",
        "feed:shopify_products_json",
        "sitemap-child",
        "feed:shopify_product_js",
    ]
    assert report.sitemap.child is not None
    assert report.sitemap.child.url_count == 50
    plan = report.plan
    assert plan.verdict == "good"
    assert plan.recommended == "feed_api"
    feed = plan.methods[0]
    assert feed.est_requests == 1  # 40 products < 250: one page holds the catalog
    assert feed.urls == ["https://shop.test/products.json?limit=250&page={page}"]
    html = next(m for m in plan.methods if m.name == "html")
    assert html.est_requests == 1000 + 20 + 1  # detail pages + sitemap files + index
    assert report.robots.paths["/products.json?limit=250"] is True


def test_full_catalog_pages() -> None:
    plan = run(shopify_routes(products=250), items=1000).plan
    assert plan.methods[0].est_requests == 4


def test_budget_is_respected() -> None:
    report = run(shopify_routes(), max_requests=3)
    assert report.requests_used == 3
    assert any(s.reason == "budget" for s in report.skipped)
    assert report.feeds.candidates[0].status == "skipped_budget"


def test_robots_disallowing_the_page() -> None:
    routes: dict[str, Route] = {
        "https://shop.test/robots.txt": (200, TXT, "User-agent: *\nDisallow: /\n"),
    }
    report = run(routes)
    assert report.requests_used == 1
    assert not report.page.fetched
    assert report.plan.verdict == "not_a_fit"
    assert report.plan.recommended is None
    assert any("disallows the requested page" in r for r in report.plan.risks)


def test_challenge_stops_and_plans_politely() -> None:
    routes: dict[str, Route] = {
        "https://shop.test/robots.txt": (404, TXT, ""),
        "https://shop.test/": (
            403,
            {**HTML, "x-datadome": "protected", "set-cookie": "datadome=x; Path=/"},
            '<html><script src="https://ct.captcha-delivery.com/c.js"></script></html>',
        ),
    }
    report = run(routes)
    assert report.requests_used == 2
    assert report.stopped is not None
    assert report.stopped.reason == "challenge"
    assert report.antibot.challenged
    assert report.antibot.vendors[0].vendor == "datadome"
    plan = report.plan
    assert plan.verdict == "not_a_fit"
    assert all(not m.usable for m in plan.methods)
    assert any("Ask the site owner" in step for step in plan.next_steps)
    text = json.dumps(report.model_dump(mode="json")).lower()
    for word in ("bypass", "evade", "rotate", "residential", "solver"):
        assert word not in text


def test_bot_managed_site_slows_down() -> None:
    routes = shopify_routes()
    status, headers, body = routes["https://shop.test/"]
    routes["https://shop.test/"] = (status, {**headers, "set-cookie": "_px3=a; Path=/"}, body)
    plan = run(routes).plan
    assert plan.verdict == "caution"
    assert plan.rate.delay_seconds == 5.0
    assert plan.rate.max_requests_per_day == 5000


def test_crawl_delay_sets_rate() -> None:
    routes = shopify_routes()
    routes["https://shop.test/robots.txt"] = (200, TXT, "User-agent: *\nCrawl-delay: 7\n")
    plan = run(routes).plan
    assert plan.rate.delay_seconds == 7.0
    assert any("7s between requests" in r for r in plan.risks)


def test_partial_feed_does_not_win() -> None:
    home = (
        '<html><head><link rel="alternate" type="application/rss+xml" href="/feed.xml">'
        f"</head><body>{BODY_TEXT}</body></html>"
    )
    routes: dict[str, Route] = {
        "https://blog.test/robots.txt": (404, TXT, ""),
        "https://blog.test/": (200, HTML, home),
        "https://blog.test/feed.xml": (200, XML, "<rss>" + "<item></item>" * 10 + "</rss>"),
    }
    plan = run(routes, url="https://blog.test/").plan
    feed = plan.methods[0]
    assert feed.usable
    assert feed.partial
    assert plan.recommended == "html"


def test_browser_only_when_nothing_else() -> None:
    shell = '<html><body><div id="root"></div><script>' + "x" * 30000 + "</script></body></html>"
    routes: dict[str, Route] = {
        "https://app.test/robots.txt": (404, TXT, ""),
        "https://app.test/": (200, HTML, shell),
    }
    plan = run(routes, url="https://app.test/").plan
    assert plan.recommended == "browser"
    assert plan.verdict == "caution"


def test_json_and_profile_outputs(tmp_path: Path) -> None:
    report = run(shopify_routes())
    data = json.loads(to_json(report))
    assert data["schema_version"] == "1"
    assert Report.model_validate(data) == report
    profile = yaml.safe_load(to_yaml(report))
    assert profile == build_profile(report)
    assert profile["method"] == "feed_api"
    assert profile["source"]["pagination"]["param"] == "page"
    assert profile["rate"]["delay_seconds"] == 1.0
    assert profile["politeness"]["respect_robots_txt"] is True


def test_profile_for_not_a_fit_has_no_urls() -> None:
    routes: dict[str, Route] = {
        "https://shop.test/robots.txt": (200, TXT, "User-agent: *\nDisallow: /\n"),
    }
    profile = build_profile(run(routes))
    assert profile["method"] is None
    assert profile["source"] == {"urls": []}


def test_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    report = run(shopify_routes())
    calls: list[Options] = []

    def fake(url: str, options: Options) -> Report:
        calls.append(options)
        return report

    monkeypatch.setattr(cli, "analyze", fake)
    runner = CliRunner()
    profile = tmp_path / "profile.yaml"
    result = runner.invoke(
        cli.app, ["shop.test", "--json", "--profile", str(profile), "--items", "50"]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["platform"]["name"] == "shopify"
    assert profile.exists()
    assert calls[0].items == 50

    text = runner.invoke(cli.app, ["shop.test"], env={"COLUMNS": "120"})
    assert text.exit_code == 0
    assert "GOOD FIT" in text.stdout
    assert "Shopify" in text.stdout

    assert runner.invoke(cli.app, ["shop.test", "--max-requests", "51"]).exit_code != 0
    assert "scrapeplanner" in runner.invoke(cli.app, ["--version"]).stdout


def test_cli_rejects_bad_url() -> None:
    result = CliRunner().invoke(cli.app, ["ftp://x.test/"])
    assert result.exit_code == 2


def test_analyze_module_has_no_bypass_options() -> None:
    fields = set(Options.__dataclass_fields__)
    assert fields == {"items", "max_requests", "delay", "timeout", "record_dir"}
    assert not hasattr(analyze_module, "proxy")


def test_refused_probe_stops_but_keeps_page_findings() -> None:
    routes = shopify_routes()
    routes["https://shop.test/products.json?limit=250"] = (403, HTML, "Forbidden")
    report = run(routes)
    assert report.stopped is not None
    assert report.stopped.url == "https://shop.test/products.json?limit=250"
    assert report.requests[-1].purpose == "feed:shopify_products_json"
    plan = report.plan
    assert plan.verdict == "caution"
    assert plan.recommended == "html"
    assert any("refused" in risk for risk in plan.risks)


def test_aws_waf_challenge_stops() -> None:
    page = "<html><script>window.awsWafCookieDomainList = ['shop.test'];</script></html>"
    routes: dict[str, Route] = {
        "https://shop.test/robots.txt": (404, TXT, ""),
        "https://shop.test/": (202, HTML, page),
    }
    report = run(routes)
    assert report.requests_used == 2
    assert report.antibot.vendors[0].vendor == "aws_waf"
    assert report.plan.verdict == "not_a_fit"


def test_429_on_a_probe_slows_the_plan() -> None:
    routes = shopify_routes()
    routes["https://shop.test/products/red-cap.js"] = (429, JSON, "{}")
    plan = run(routes).plan
    assert plan.verdict == "caution"
    assert plan.recommended == "feed_api"
    assert plan.rate.delay_seconds == 5.0
    assert "429" in plan.rate.reason

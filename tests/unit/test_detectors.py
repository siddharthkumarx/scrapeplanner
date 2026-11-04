"""Unit tests for the detectors on small hand-written inputs."""

from __future__ import annotations

import gzip
import json

import pytest

from scrapeplanner.detectors import (
    antibot,
    embedded,
    feeds,
    platform,
    rendering,
    sitemaps,
    structured,
)
from scrapeplanner.html import HtmlDoc
from scrapeplanner.models import FeedCandidate, PlatformReport


def doc(html: str, url: str = "https://site.test/") -> HtmlDoc:
    return HtmlDoc(html, url)


# -- anti-bot ---------------------------------------------------------------


def test_cloudflare_cdn_is_present_not_challenge() -> None:
    hits = antibot.detect(200, {"server": "cloudflare", "cf-ray": "x"}, [], "<p>" + "a" * 40000)
    assert [(h.vendor, h.status) for h in hits] == [("cloudflare", "present")]
    assert antibot.classify_block(200, {"cf-ray": "x"}, [], "ok") is None


def test_cloudflare_challenge_page() -> None:
    body = "<html><head><title>Just a moment...</title></head></html>"
    block = antibot.classify_block(403, {"cf-mitigated": "challenge"}, [], body)
    assert block is not None
    assert block[0] == "challenge"


def test_challenge_marker_in_big_page_is_not_a_challenge() -> None:
    body = "<script>window._cf_chl_opt={}</script>" + "x" * 50000
    hits = antibot.detect(200, {}, [], body)
    assert hits[0].status == "present"


@pytest.mark.parametrize(
    ("headers", "cookies", "body", "vendor"),
    [
        ({}, ["_abck", "bm_sz"], "", "akamai"),
        ({"x-datadome": "protected"}, ["datadome"], "", "datadome"),
        ({}, ["_px3", "_pxvid"], "", "human"),
        ({"x-iinfo": "1"}, ["visid_incap_123"], "", "imperva"),
        ({"x-kpsdk-ct": "1"}, [], "", "kasada"),
    ],
)
def test_vendor_present(
    headers: dict[str, str], cookies: list[str], body: str, vendor: str
) -> None:
    hits = antibot.detect(200, headers, cookies, body + "x" * 40000)
    assert [h.vendor for h in hits] == [vendor]
    assert hits[0].status == "present"


@pytest.mark.parametrize(
    ("status", "body", "vendor"),
    [
        (403, '<script src="https://ct.captcha-delivery.com/c.js"></script>', "datadome"),
        (403, '<div id="px-captcha"></div>', "human"),
        (200, '<iframe src="/_Incapsula_Resource?x=1"></iframe>', "imperva"),
        (403, "Reference #18.1 https://errors.edgesuite.net/18.1", "akamai"),
    ],
)
def test_vendor_challenge(status: int, body: str, vendor: str) -> None:
    hits = antibot.detect(status, {}, [], body)
    assert (hits[0].vendor, hits[0].status) == (vendor, "challenge")
    block = antibot.classify_block(status, {}, [], body)
    assert block is not None
    assert block[0] == "challenge"


def test_kasada_429_is_challenge() -> None:
    hits = antibot.detect(429, {"x-kpsdk-ct": "a"}, [], "")
    assert hits[0].status == "challenge"


def test_plain_403_blocks_without_vendor() -> None:
    assert antibot.classify_block(403, {}, [], "Forbidden") == ("blocked", "HTTP 403")


def test_merge_keeps_first_challenge_url() -> None:
    report = antibot.merge(
        [
            ("https://a/", antibot.detect(200, {"cf-ray": "1"}, [], "x" * 40000)),
            ("https://a/x", antibot.detect(403, {}, [], "<title>Just a moment...</title>")),
        ]
    )
    assert report.challenged
    assert report.challenge_url == "https://a/x"
    assert len(report.vendors) == 1


# -- platform ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("headers", "cookies", "html", "name"),
    [
        ({"x-shopid": "1"}, [], '<script src="//cdn.shopify.com/a.js"></script>', "shopify"),
        ({}, [], '<link href="/wp-content/plugins/woocommerce/a.css">', "woocommerce"),
        ({}, [], '<script type="text/x-magento-init">{}</script>', "magento"),
        ({}, [], '<script src="https://cdn11.bigcommerce.com/s-1/a.js"></script>', "bigcommerce"),
        ({"x-wix-request-id": "1"}, [], "", "wix"),
        ({}, [], "<!-- This is Squarespace. --><p>", "squarespace"),
        ({}, [], '<script id="__NEXT_DATA__" type="application/json">{}</script>', "nextjs"),
        ({}, [], '<script src="/_nuxt/app.js"></script>', "nuxt"),
        ({}, [], "<p>plain</p>", "unknown"),
    ],
)
def test_platforms(headers: dict[str, str], cookies: list[str], html: str, name: str) -> None:
    assert platform.detect(headers, cookies, doc(html)).name == name


def test_commerce_beats_framework() -> None:
    html = (
        '<script src="/_next/static/a.js"></script><script src="https://cdn.shopify.com/x.js">'
        "</script>"
    )
    report = platform.detect({"x-shopid": "1"}, [], doc(html))
    assert report.name == "shopify"
    assert report.frameworks == ["nextjs"]
    assert report.confidence == "high"


def test_single_hint_is_not_enough() -> None:
    report = platform.detect({}, [], doc("<p>see shop.myshopify.com</p>"))
    assert report.name == "unknown"


def test_wordpress_is_a_platform() -> None:
    html = (
        '<meta name="generator" content="WordPress 6.8">'
        '<link rel="https://api.w.org/" href="/wp-json/">'
    )
    report = platform.detect({}, [], doc(html))
    assert report.name == "wordpress"
    assert report.generator == "WordPress 6.8"
    assert report.checked


@pytest.mark.parametrize(
    ("headers", "cookies", "html", "name"),
    [
        ({"x-powered-by": "WordPress VIP <https://wpvip.com>"}, [], "", "wordpress"),
        ({"link": '<https://a.test/wp-json/>; rel="https://api.w.org/"'}, [], "", "wordpress"),
        ({}, [], '<meta name="Generator" content="Drupal 10">', "drupal"),
        ({"x-drupal-cache": "HIT"}, [], "", "drupal"),
        ({}, [], '<html data-wf-page="1" data-wf-site="2">', "webflow"),
        ({}, [], '<meta name="generator" content="Webflow">', "webflow"),
        ({}, [], '<div id="___gatsby"></div>', "gatsby"),
        ({}, [], '<script src="/on/demandware.store/Sites-x/en/Page"></script>', "sfcc"),
        ({}, ["dwsid", "dwanonymous_abc"], "", "sfcc"),
        ({}, [], '<script type="text/x-magento-init">{}</script>', "magento"),
        ({}, [], '<app-root ng-version="17.3.0"></app-root>', "angular"),
        ({}, [], '<div id="root"></div><script src="/static/js/main.1a2b3c4d.js">', "react"),
        ({}, [], '<div data-reactroot=""><p>hi</p></div>', "react"),
        ({}, [], '<div data-v-1a2b3c4d class="x"></div>', "vue"),
        ({}, [], '<div id="app" data-server-rendered="true"></div>', "vue"),
        ({}, [], "<!--lit-part abc--><p>x</p>", "lit"),
        ({}, [], "<meta name=generator content='Hugo 0.140.0'>", "hugo"),
        ({}, [], '<nav class="td-navbar navbar">', "hugo"),
        ({}, [], '<script src="_static/documentation_options.js"></script>', "sphinx"),
        ({}, [], '<meta name="generator" content="Docusaurus v3.5">', "docusaurus"),
        ({"x-wix-renderer-server": "1"}, [], "", "wix"),
        ({}, ["svSession"], '<script src="https://static.parastorage.com/x.js">', "wix"),
        ({}, [], '<img src="https://images.squarespace-cdn.com/a.jpg">', "unknown"),
        ({}, ["ss_cvr"], '<img src="https://images.squarespace-cdn.com/a.jpg">', "squarespace"),
    ],
)
def test_more_platforms(headers: dict[str, str], cookies: list[str], html: str, name: str) -> None:
    assert platform.detect(headers, cookies, doc(html)).name == name


def test_group_order_and_implied_libraries() -> None:
    next_page = '<script id="__NEXT_DATA__" type="application/json">{}</script><div data-reactroot>'
    report = platform.detect({}, [], doc(next_page))
    assert report.name == "nextjs"
    assert report.frameworks == []  # React is implied by Next.js
    woo = (
        '<link href="/wp-content/plugins/woocommerce/a.css">'
        '<meta name="generator" content="WordPress 6.8">'
    )
    report = platform.detect({}, [], doc(woo))
    assert (report.name, report.frameworks) == ("woocommerce", [])
    wp_react = '<meta name="generator" content="WordPress 6.8"><div data-reactroot></div>'
    report = platform.detect({}, [], doc(wp_react))
    assert (report.name, report.frameworks) == ("wordpress", ["react"])


# -- structured data ----------------------------------------------------------

PRODUCT_LD = {
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "Blue Shirt",
    "sku": "B1",
    "offers": {"@type": "Offer", "price": "19.00", "priceCurrency": "EUR"},
}


def test_jsonld_product() -> None:
    html = f'<script type="application/ld+json">{json.dumps(PRODUCT_LD)}</script>'
    report = structured.detect(doc(html))
    assert report.jsonld_blocks == 1
    assert report.types == {"Product": 1, "Offer": 1}
    assert report.key_types == ["Product"]
    item = report.items[0]
    assert item.fields == ["name", "sku", "offers.price", "offers.priceCurrency"]
    assert item.sample["offers.price"] == "19.00"


def test_jsonld_graph_lenient_and_invalid() -> None:
    graph = '{"@context":"https://schema.org","@graph":[{"@type":"NewsArticle","headline":"H",}]}'
    html = (
        f'<script type="application/ld+json"><!--{graph}--></script>'
        '<script type="application/ld+json">{broken</script>'
    )
    report = structured.detect(doc(html))
    assert report.types == {"NewsArticle": 1}
    assert report.jsonld_invalid == 1


def test_author_names_are_not_sampled() -> None:
    article = {"@type": "Article", "headline": "H", "author": {"@type": "Person", "name": "Jo"}}
    html = f'<script type="application/ld+json">{json.dumps(article)}</script>'
    item = structured.detect(doc(html)).items[0]
    assert "author" in item.fields
    assert "author" not in item.sample
    assert all("Jo" not in value for value in item.sample.values())


def test_microdata_nested() -> None:
    html = """
    <div itemscope itemtype="https://schema.org/Product">
      <h1 itemprop="name">Lamp</h1>
      <div itemprop="offers" itemscope itemtype="https://schema.org/Offer">
        <meta itemprop="price" content="12.50"><meta itemprop="priceCurrency" content="USD">
      </div>
    </div>"""
    report = structured.detect(doc(html))
    assert report.microdata_items == 1
    product = next(i for i in report.items if i.type == "Product")
    assert product.source == "microdata"
    assert product.sample == {
        "name": "Lamp",
        "offers.price": "12.50",
        "offers.priceCurrency": "USD",
    }


# -- embedded state -------------------------------------------------------------


def test_next_data() -> None:
    data = {"props": {"pageProps": {"products": [1], "total": 3}}, "page": "/", "buildId": "b1"}
    html = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script>'
    blob = embedded.detect(doc(html)).blobs[0]
    assert blob.kind == "next_data"
    assert blob.keys == ["products", "total"]
    assert blob.details == {"page": "/", "buildId": "b1"}


def test_other_states() -> None:
    big = json.dumps({"items": list(range(500))})
    html = (
        '<script>self.__next_f.push([1,"a"])</script><script>self.__next_f.push([1,"b"])</script>'
        "<script>window.__APOLLO_STATE__ = "
        '{"Product:1":{},"Product:2":{},"ROOT_QUERY":{}};</script>'
        f'<script type="application/json" id="data">{big}</script>'
        "<script>window.__NUXT__=(function(a){return {data:[a]}}(1));</script>"
        '<script type="application/json" id="tiny">{"a":1}</script>'
    )
    blobs = {b.kind: b for b in embedded.detect(doc(html)).blobs}
    assert blobs["next_flight"].details["chunks"] == "2"
    assert blobs["apollo_state"].keys == ["Product x2", "ROOT_QUERY x1"]
    assert blobs["json_script"].locator == "script#data"
    assert blobs["nuxt_state"].details["format"] == "javascript (Nuxt 2)"
    assert len(blobs) == 4


# -- rendering ------------------------------------------------------------------


def _render(html: str) -> str:
    d = doc(html)
    return rendering.detect(d, structured.detect(d), embedded.detect(d)).verdict


def test_rendering_verdicts() -> None:
    assert _render("<body>" + "<p>word </p>" * 200 + "</body>") == "raw_html"
    shell = '<body><div id="root"></div><script>' + "x" * 20000 + "</script></body>"
    assert _render(shell) == "browser_likely"
    state = json.dumps({"props": {"pageProps": {"x": "y" * 8000}}})
    next_shell = (
        '<body><div id="__next"></div>'
        f'<script id="__NEXT_DATA__" type="application/json">{state}</script></body>'
    )
    assert _render(next_shell) == "embedded_json"
    ld = f'<script type="application/ld+json">{json.dumps(PRODUCT_LD)}</script>'
    assert _render(f'<body><div id="app"></div>{ld}</body>') == "raw_html"


# -- sitemaps -------------------------------------------------------------------

URLSET = (
    '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
    'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'
    "<url><loc>https://s/a</loc><lastmod>2026-01-02</lastmod>"
    "<image:image><image:loc>https://s/a.jpg</image:loc></image:image></url>"
    "<url><loc>https://s/b</loc><lastmod>2025-05-06T10:00:00+00:00</lastmod></url>"
    "<url><loc>https://s/c</loc></url></urlset>"
)


def test_urlset() -> None:
    report, children = sitemaps.parse(URLSET.encode())
    assert report.kind == "urlset"
    assert report.url_count == 3
    assert report.sample_urls == ["https://s/a", "https://s/b", "https://s/c"]
    assert (report.oldest_lastmod, report.newest_lastmod) == ("2025-05-06", "2026-01-02")
    assert report.with_lastmod == 2
    assert children == []


def test_gzipped_index() -> None:
    xml = (
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        "<sitemap><loc>https://s/pages.xml</loc></sitemap>"
        "<sitemap><loc>https://s/products-1.xml</loc></sitemap></sitemapindex>"
    )
    report, children = sitemaps.parse(gzip.compress(xml.encode()))
    assert report.kind == "sitemapindex"
    assert report.child_sitemaps == 2
    assert sitemaps.pick_child(children, ("product",)) == "https://s/products-1.xml"
    assert sitemaps.pick_child(children, ()) == "https://s/pages.xml"


def test_truncated_and_hostile_sitemaps() -> None:
    cut, _ = sitemaps.parse(URLSET.encode()[:200], truncated=True)
    assert cut.kind == "urlset"
    assert cut.truncated
    entity = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><urlset>&a;</urlset>'
    assert sitemaps.parse(entity)[0].kind == "invalid"
    assert sitemaps.parse(b"<html><body>no</body></html>")[0].kind == "invalid"
    assert sitemaps.parse(b"not xml at all")[0].kind == "invalid"


# -- feeds ------------------------------------------------------------------------


def test_candidates_shopify_and_links() -> None:
    html = (
        '<a href="/products/blue-shirt">x</a>'
        '<link rel="alternate" type="application/rss+xml" href="/blogs/news.atom" title="News">'
        '<link rel="alternate" type="application/rss+xml" href="https://other.test/feed">'
    )
    found = feeds.candidates(PlatformReport(name="shopify"), doc(html), "https://site.test/")
    assert [(c.kind, c.url) for c in found] == [
        ("shopify_products_json", "https://site.test/products.json?limit=250"),
        ("shopify_product_js", "https://site.test/products/blue-shirt.js"),
        ("rss", "https://site.test/blogs/news.atom"),
    ]
    assert all(c.status == "linked" for c in found)


def test_candidates_wordpress() -> None:
    found = feeds.candidates(
        PlatformReport(name="unknown", frameworks=["wordpress"]), doc(""), "https://site.test/x"
    )
    assert found[0].url == "https://site.test/wp-json/wp/v2/posts?per_page=1"


def _cand(kind: str) -> FeedCandidate:
    return FeedCandidate(kind=kind, url="https://site.test/f", status="linked")  # type: ignore[arg-type]


def test_evaluate_shapes() -> None:
    body = json.dumps({"products": [{"id": 1, "title": "t", "variants": []}]})
    ok = feeds.evaluate(_cand("shopify_products_json"), 200, "application/json", body, {})
    assert (ok.status, ok.items_seen, ok.fields) == ("ok", 1, ["id", "title", "variants"])
    woo = feeds.evaluate(
        _cand("woo_store_api"), 200, "application/json", '[{"id":1}]', {"X-WP-Total": "321"}
    )
    assert (woo.status, woo.total_items) == ("ok", 321)
    rss = feeds.evaluate(_cand("rss"), 200, "text/xml", "<rss><item></item><item></item></rss>", {})
    assert (rss.status, rss.items_seen) == ("ok", 2)
    assert feeds.evaluate(_cand("rss"), 404, "", "", {}).status == "not_found"
    html = feeds.evaluate(_cand("shopify_products_json"), 200, "text/html", "<html>", {})
    assert html.status == "invalid"
    wrong = feeds.evaluate(_cand("woo_store_api"), 200, "application/json", "{}", {})
    assert wrong.status == "invalid"


def test_wordpress_core_react_is_not_a_react_site() -> None:
    html = (
        '<meta name="generator" content="WordPress 6.8">'
        '<script src="https://a.test/wp-includes/js/dist/vendor/react-dom.min.js?ver=18.3.1"></script>'
    )
    report = platform.detect({}, [], doc(html))
    assert (report.name, report.frameworks) == ("wordpress", [])


def test_own_bot_check_page_is_a_challenge() -> None:
    # Shape of the page amazon.com served in checks/results/004-sites (HTTP 200, 3.8 KB).
    body = (
        "<html><body><h4>Click the button below to continue shopping</h4>"
        '<form method="get" action="/errors_page/validateCaptcha"><button>Continue shopping'
        "</button></form></body></html>"
    )
    block = antibot.classify_block(200, {}, [], body)
    assert block is not None
    assert block[0] == "challenge"
    assert antibot.detect(200, {}, [], body)[0].vendor == "own_check"


def test_captcha_widget_in_a_normal_page_is_ignored() -> None:
    body = '<form class="newsletter"><div class="g-recaptcha"></div></form>' + "<p>x</p>" * 8000
    assert antibot.detect(200, {}, [], body) == []
    assert antibot.classify_block(200, {}, [], body) is None


@pytest.mark.parametrize(
    ("url", "html", "name", "api"),
    [
        (
            "https://job-boards.greenhouse.io/acme",
            "",
            "greenhouse",
            "https://boards-api.greenhouse.io/v1/boards/acme/jobs",
        ),
        (
            "https://acme.test/careers",
            '<script src="https://boards.greenhouse.io/embed/job_board/js?for=acme"></script>',
            "greenhouse",
            "https://boards-api.greenhouse.io/v1/boards/acme/jobs",
        ),
        (
            "https://jobs.lever.co/acme",
            "",
            "lever",
            "https://api.lever.co/v0/postings/acme?mode=json",
        ),
        (
            "https://jobs.ashbyhq.com/acme",
            "",
            "ashby",
            "https://api.ashbyhq.com/posting-api/job-board/acme",
        ),
    ],
)
def test_job_boards_and_their_apis(url: str, html: str, name: str, api: str) -> None:
    page = doc(html, url)
    report = platform.detect({}, [], page)
    assert report.name == name
    found = feeds.candidates(report, page, url)
    assert found[0].url == api


def test_ckan_portal() -> None:
    html = '<meta name="generator" content="ckan 2.10.4"><a href="/api/3/action/package_list">'
    page = doc(html, "https://data.test/dataset")
    report = platform.detect({}, [], page)
    assert report.name == "ckan"
    found = feeds.candidates(report, page, "https://data.test/dataset")
    assert found[0].url == "https://data.test/api/3/action/package_search?rows=1"
    body = json.dumps({"success": True, "result": {"count": 4321, "results": [{"name": "x"}]}})
    ok = feeds.evaluate(found[0], 200, "application/json", body, {})
    assert (ok.status, ok.total_items, ok.page_size) == ("ok", 4321, 1000)


def test_wordpress_data_module_is_not_ckan() -> None:
    html = '<meta name="generator" content="WordPress 6.9"><div data-module="x"></div>'
    assert platform.detect({}, [], doc(html)).name == "wordpress"


def test_job_board_api_shapes() -> None:
    gh = feeds.evaluate(
        _cand("greenhouse_api"), 200, "application/json", '{"jobs":[{"id":1},{"id":2}]}', {}
    )
    assert (gh.status, gh.total_items) == ("ok", 2)
    lever = feeds.evaluate(_cand("lever_api"), 200, "application/json", '[{"id":"a"}]', {})
    assert (lever.status, lever.total_items) == ("ok", 1)
    assert feeds.evaluate(_cand("ashby_api"), 200, "application/json", "[]", {}).status == "invalid"

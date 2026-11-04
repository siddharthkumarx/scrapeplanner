"""Which platform runs the site: commerce platforms, site builders and CMSs,
documentation generators, meta-frameworks, client-side libraries.

Each signal has a weight: 3 = decisive on its own, 2 = strong, 1 = hint.
A platform needs a score of 2 or more. The groups in ``GROUPS`` are checked in
order, so a headless Shopify store on Next.js reports ``shopify`` with
``nextjs`` under ``frameworks``, and a WordPress site built with React
reports ``wordpress``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from scrapeplanner.html import HtmlDoc
from scrapeplanner.models import Confidence, PlatformName, PlatformReport

Where = Literal["header", "header_value", "cookie", "html", "generator", "url"]


@dataclass(frozen=True)
class Signal:
    name: str
    where: Where
    pattern: str
    weight: int
    label: str


SIGNALS: tuple[Signal, ...] = (
    # Shopify
    Signal("shopify", "header", "x-shopid", 3, "header x-shopid"),
    Signal("shopify", "header", "x-shopify-stage", 3, "header x-shopify-stage"),
    Signal("shopify", "header_value", r"powered-by=shopify", 3, "header powered-by: Shopify"),
    Signal("shopify", "cookie", r"^_shopify_(y|s|sa_t|sa_p)$|^cart_sig$", 2, "cookie _shopify_*"),
    Signal("shopify", "html", r"cdn\.shopify\.com", 2, "assets on cdn.shopify.com"),
    Signal(
        "shopify", "html", r"""["'](?:https?:)?//[^"']*/cdn/shop/""", 2, "assets under /cdn/shop/"
    ),
    Signal("shopify", "html", r"Shopify\.theme\b", 3, "Shopify.theme script"),
    Signal("shopify", "html", r"window\.Shopify\b|Shopify\.shop\s*=", 2, "window.Shopify object"),
    Signal("shopify", "html", r"\.myshopify\.com", 1, "mentions .myshopify.com"),
    # WooCommerce
    Signal("woocommerce", "generator", r"^WooCommerce", 3, "meta generator WooCommerce"),
    Signal(
        "woocommerce", "html", r"/wp-content/plugins/woocommerce/", 3, "WooCommerce plugin assets"
    ),
    Signal(
        "woocommerce",
        "html",
        r"\bwc_add_to_cart_params\b|\bwoocommerce_params\b",
        3,
        "woocommerce_params script",
    ),
    Signal(
        "woocommerce", "html", r"""class=["'][^"']*\bwoocommerce\b""", 2, "woocommerce CSS class"
    ),
    Signal("woocommerce", "html", r"/wc/store/v1", 2, "WooCommerce Store API reference"),
    Signal(
        "woocommerce",
        "cookie",
        r"^woocommerce_|^wp_woocommerce_session_",
        3,
        "cookie woocommerce_*",
    ),
    # Magento / Adobe Commerce
    Signal("magento", "header", "x-magento-tags", 3, "header x-magento-tags"),
    Signal("magento", "header", "x-magento-cache-debug", 3, "header x-magento-cache-debug"),
    Signal("magento", "html", r"text/x-magento-init", 3, "text/x-magento-init script"),
    Signal("magento", "html", r"data-mage-init", 3, "data-mage-init attribute"),
    Signal("magento", "html", r"\bMagento_[A-Z][A-Za-z]+/", 2, "Magento_* module assets"),
    Signal("magento", "html", r"/static/version\d+/frontend/", 2, "Magento static/version path"),
    Signal("magento", "cookie", r"^mage-|^form_key$", 2, "cookie mage-*/form_key"),
    # BigCommerce
    Signal("bigcommerce", "html", r"cdn\d*\.bigcommerce\.com", 3, "assets on cdn*.bigcommerce.com"),
    Signal("bigcommerce", "html", r"\bBCData\b", 2, "BCData script"),
    Signal("bigcommerce", "html", r"stencil-utils|stencilBootstrap", 2, "Stencil theme script"),
    Signal(
        "bigcommerce",
        "cookie",
        r"^SHOP_SESSION_TOKEN$|^fornax_anonymousId$",
        2,
        "cookie SHOP_SESSION_TOKEN",
    ),
    # Wix
    Signal("wix", "header", "x-wix-request-id", 3, "header x-wix-request-id"),
    Signal("wix", "generator", r"^Wix\.com", 3, "meta generator Wix.com"),
    Signal("wix", "html", r"static\.parastorage\.com", 3, "assets on static.parastorage.com"),
    Signal("wix", "html", r"static\.wixstatic\.com", 2, "images on static.wixstatic.com"),
    # Squarespace
    Signal("squarespace", "html", r"<!-- This is Squarespace\. -->", 3, "Squarespace HTML comment"),
    Signal("squarespace", "html", r"Static\.SQUARESPACE_CONTEXT", 3, "SQUARESPACE_CONTEXT script"),
    Signal(
        "squarespace", "html", r"static1\.squarespace\.com", 2, "assets on static1.squarespace.com"
    ),
    Signal("squarespace", "header_value", r"server=^squarespace", 3, "header server: Squarespace"),
    Signal(
        "squarespace", "html", r"images\.squarespace-cdn\.com", 1, "images on squarespace-cdn.com"
    ),
    Signal("squarespace", "cookie", r"^ss_cv[rt]$", 2, "cookie ss_cvr/ss_cvt"),
    # Hosted job boards (the board URL itself, or the embed on a company careers page)
    Signal(
        "greenhouse",
        "url",
        r"^https?://(?:job-)?boards\.greenhouse\.io/",
        3,
        "page on boards.greenhouse.io",
    ),
    Signal(
        "greenhouse",
        "html",
        r"boards\.greenhouse\.io/embed/job_board|grnhse_app",
        3,
        "Greenhouse job-board embed",
    ),
    Signal("lever", "url", r"^https?://jobs\.(?:eu\.)?lever\.co/", 3, "page on jobs.lever.co"),
    Signal(
        "lever",
        "html",
        r"""["']https?://jobs\.(?:eu\.)?lever\.co/[^"'/]+""",
        2,
        "links to jobs.lever.co",
    ),
    Signal("ashby", "url", r"^https?://jobs\.ashbyhq\.com/", 3, "page on jobs.ashbyhq.com"),
    Signal(
        "ashby",
        "html",
        r"jobs\.ashbyhq\.com/[^\"'/]+/embed|__ashbyBaseJobBoardUrl",
        3,
        "Ashby job-board embed",
    ),
    # Open-data portals
    Signal("ckan", "generator", r"^ckan", 3, "meta generator CKAN"),
    Signal("ckan", "html", r"/api/3/action/", 2, "links to the CKAN action API"),
    Signal("ckan", "html", r"/webassets/(?:base|vendor|ckanext)|ckanext-", 2, "CKAN web assets"),
    Signal("socrata", "header", "x-socrata-requestid", 3, "header x-socrata-requestid"),
    Signal("socrata", "html", r"/api/views/[a-z0-9]{4}-[a-z0-9]{4}", 2, "Socrata dataset views"),
    Signal("socrata", "html", r"socrata", 1, "mentions Socrata"),
    # Wix (re-checked: Thunderbolt renderer and its cookies)
    Signal("wix", "header", "x-wix-renderer-server", 3, "header x-wix-renderer-server"),
    Signal("wix", "html", r"wix-thunderbolt|thunderbolt-commons", 3, "Wix Thunderbolt renderer"),
    Signal("wix", "cookie", r"^svSession$", 2, "cookie svSession"),
    # Salesforce Commerce Cloud (Demandware)
    Signal("sfcc", "html", r"/on/demandware\.store/", 3, "/on/demandware.store/ URLs"),
    Signal("sfcc", "html", r"demandware\.static|/dw/image/v2/", 3, "Demandware static/image URLs"),
    Signal("sfcc", "cookie", r"^dwanonymous_|^dwsid$|^dwac_", 3, "cookie dwsid/dwanonymous_"),
    Signal("sfcc", "header", "x-dw-request-base-id", 3, "header x-dw-request-base-id"),
    # Webflow
    Signal("webflow", "generator", r"^Webflow", 3, "meta generator Webflow"),
    Signal("webflow", "html", r"""data-wf-(?:page|site)=["']""", 3, "data-wf-page/data-wf-site"),
    Signal(
        "webflow",
        "html",
        r"(?:assets|cdn\.prod)\.website-files\.com",
        2,
        "assets on website-files.com",
    ),
    # WordPress (WooCommerce, when present, wins as the commerce platform)
    Signal("wordpress", "generator", r"^WordPress", 3, "meta generator WordPress"),
    Signal(
        "wordpress", "html", r"/wp-content/(?:themes|plugins|uploads)/", 2, "/wp-content/ assets"
    ),
    Signal(
        "wordpress", "html", r"""rel=["']https://api\.w\.org/["']""", 3, "WordPress REST API link"
    ),
    Signal(
        "wordpress",
        "header_value",
        r"link=rel=\"https://api\.w\.org/\"",
        3,
        "header link: api.w.org",
    ),
    Signal(
        "wordpress", "header_value", r"x-powered-by=wordpress", 3, "header x-powered-by: WordPress"
    ),
    # Drupal
    Signal("drupal", "generator", r"^Drupal", 3, "meta generator Drupal"),
    Signal("drupal", "header", "x-drupal-cache", 3, "header x-drupal-cache"),
    Signal("drupal", "header", "x-drupal-dynamic-cache", 3, "header x-drupal-dynamic-cache"),
    Signal("drupal", "header_value", r"x-generator=^drupal", 3, "header x-generator: Drupal"),
    Signal("drupal", "html", r"drupalSettings|data-drupal-selector", 3, "drupalSettings script"),
    Signal(
        "drupal",
        "html",
        r"/sites/(?:default|all)/(?:files|themes|modules)/",
        2,
        "/sites/default/ assets",
    ),
    # Documentation generators
    Signal("hugo", "generator", r"^Hugo", 3, "meta generator Hugo"),
    Signal(
        "hugo",
        "html",
        r"""class=["'][^"']*\btd-(?:navbar|sidebar|main)\b""",
        3,
        "Docsy theme (Hugo)",
    ),
    Signal(
        "sphinx",
        "html",
        r"_static/(?:sphinx_highlight|documentation_options)\.js",
        3,
        "Sphinx static assets",
    ),
    Signal("sphinx", "html", r"Created using <a[^>]*>Sphinx</a>", 2, "Created using Sphinx"),
    Signal("docusaurus", "generator", r"^Docusaurus", 3, "meta generator Docusaurus"),
    Signal("docusaurus", "html", r"""id=["']__docusaurus""", 3, "#__docusaurus root"),
    # Next.js
    Signal(
        "nextjs", "html", r"""<script[^>]+id=["']__NEXT_DATA__["']""", 3, "__NEXT_DATA__ script"
    ),
    Signal("nextjs", "html", r"/_next/static/", 3, "assets under /_next/static/"),
    Signal("nextjs", "html", r"self\.__next_f\.push", 3, "App Router flight data"),
    Signal("nextjs", "header_value", r"x-powered-by=next\.js", 3, "header x-powered-by: Next.js"),
    Signal("nextjs", "header", "x-nextjs-cache", 3, "header x-nextjs-cache"),
    Signal("nextjs", "header", "x-nextjs-prerender", 3, "header x-nextjs-prerender"),
    # Nuxt
    Signal("nuxt", "html", r"window\.__NUXT__\s*=", 3, "window.__NUXT__ state"),
    Signal("nuxt", "html", r"""<script[^>]+id=["']__NUXT_DATA__["']""", 3, "__NUXT_DATA__ script"),
    Signal("nuxt", "html", r"""["'][^"']*/_nuxt/""", 3, "assets under /_nuxt/"),
    Signal("nuxt", "html", r"""id=["']__nuxt["']""", 2, "#__nuxt root"),
    Signal("nuxt", "header_value", r"x-powered-by=nuxt", 3, "header x-powered-by: Nuxt"),
    # Gatsby
    Signal("gatsby", "html", r"""id=["']___gatsby["']""", 3, "#___gatsby root"),
    Signal("gatsby", "generator", r"^Gatsby", 3, "meta generator Gatsby"),
    Signal("gatsby", "html", r"/page-data/[^\"']*page-data\.json", 2, "page-data.json links"),
    # Other meta-frameworks
    Signal("sveltekit", "html", r"__sveltekit_", 3, "SvelteKit bootstrap"),
    Signal("astro", "html", r"<astro-island\b", 3, "astro-island element"),
    Signal("remix", "html", r"__remixContext", 3, "Remix context"),
    # Angular
    Signal("angular", "html", r"\bng-version=", 3, "Angular ng-version"),
    Signal("angular", "html", r"\b_ng(?:host|content)-[a-z0-9-]+", 3, "Angular _nghost attributes"),
    Signal("angular", "html", r"ng-server-context=", 3, "Angular ng-server-context"),
    Signal("angular", "html", r"<app-root\b", 2, "<app-root> element"),
    # Generic single-page apps and component libraries
    Signal("react", "html", r"\bdata-reactroot\b", 3, "data-reactroot attribute"),
    Signal(
        "react",
        "html",
        r"""id=["']react-(?:root|app|application)["']""",
        2,
        "#react-root container",
    ),
    Signal(
        "react",
        "html",
        r"React@\d+\.\d+|(?<!/wp-includes/js/dist/vendor/)react-dom(?:\.production)?(?:\.min)?\.js",
        2,
        "React build marker",
    ),
    Signal("react", "html", r"""<div id=["']root["']>\s*</div>""", 1, "empty #root container"),
    Signal("react", "html", r"/static/js/main\.[0-9a-f]{8}\.js", 2, "create-react-app bundle"),
    Signal("vue", "html", r"\bdata-v-[0-9a-f]{8}\b", 3, "Vue scoped-style attributes"),
    Signal("vue", "html", r"""data-server-rendered=["']true["']""", 3, "Vue SSR marker"),
    Signal(
        "vue",
        "html",
        r"vue(?:\.runtime)?(?:\.global)?(?:\.prod)?(?:\.min)?\.js|__VUE__",
        3,
        "Vue runtime script",
    ),
    Signal("vue", "html", r"""<div id=["']app["']>\s*</div>""", 1, "empty #app container"),
    Signal("lit", "html", r"<!--lit-part\b", 3, "Lit server-rendered parts"),
)

GROUPS: tuple[tuple[PlatformName, ...], ...] = (
    # 1. platforms that decide which public feeds exist: commerce, job boards, data portals
    ("shopify", "woocommerce", "magento", "bigcommerce", "sfcc"),
    ("greenhouse", "lever", "ashby"),
    ("ckan", "socrata"),
    # 2. site builders and CMSs
    ("wix", "squarespace", "webflow", "wordpress", "drupal"),
    # 3. documentation generators
    ("hugo", "sphinx", "docusaurus"),
    # 4. meta-frameworks
    ("nextjs", "nuxt", "gatsby", "remix", "sveltekit", "astro", "angular"),
    # 5. client-side libraries (generic single-page apps)
    ("react", "vue", "lit"),
)
"""The first group with a match names the platform; the rest go to ``frameworks``."""
IMPLIED: dict[str, frozenset[str]] = {
    "nextjs": frozenset({"react"}),
    "gatsby": frozenset({"react"}),
    "remix": frozenset({"react"}),
    "docusaurus": frozenset({"react"}),
    "nuxt": frozenset({"vue"}),
    "woocommerce": frozenset({"wordpress"}),
}
"""Libraries a platform always brings; not repeated under ``frameworks``."""
MIN_SCORE = 2


def _confidence(score: int) -> Confidence:
    if score >= 5:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


def detect(headers: Mapping[str, str], cookie_names: Sequence[str], doc: HtmlDoc) -> PlatformReport:
    lowered = {key.lower(): value for key, value in headers.items()}
    generator = doc.meta("generator")
    scores: dict[str, int] = {}
    evidence: dict[str, list[str]] = {}
    for signal in SIGNALS:
        regex = re.compile(signal.pattern, re.IGNORECASE)
        if signal.where == "header":
            fired = signal.pattern in lowered
        elif signal.where == "header_value":
            name, _, value_pattern = signal.pattern.partition("=")
            value = lowered.get(name)
            fired = value is not None and bool(re.search(value_pattern, value, re.IGNORECASE))
        elif signal.where == "cookie":
            fired = any(regex.search(name) for name in cookie_names)
        elif signal.where == "generator":
            fired = generator is not None and bool(regex.search(generator))
        elif signal.where == "url":
            fired = bool(regex.search(doc.base_url))
        else:
            fired = bool(regex.search(doc.html))
        if fired:
            scores[signal.name] = scores.get(signal.name, 0) + signal.weight
            evidence.setdefault(signal.name, []).append(signal.label)

    found = {name: score for name, score in scores.items() if score >= MIN_SCORE}
    report = PlatformReport(generator=generator, checked=True)
    chosen: PlatformName | None = None
    for group in GROUPS:
        candidates: list[PlatformName] = [name for name in group if name in found]
        if candidates:
            scores_in_group = [found[name] for name in candidates]
            chosen = candidates[scores_in_group.index(max(scores_in_group))]
            break
    implied: frozenset[str] = frozenset()
    if chosen is not None:
        report.name = chosen
        report.confidence = _confidence(found[chosen])
        report.evidence = evidence[chosen]
        implied = IMPLIED.get(chosen, frozenset())
    report.frameworks = sorted(
        (name for name in found if name != chosen and name not in implied),
        key=lambda name: (-found[name], name),
    )
    return report

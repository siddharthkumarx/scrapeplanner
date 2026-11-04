"""Which platform runs the site: commerce platforms, site builders, JS frameworks.

Each signal has a weight: 3 = decisive on its own, 2 = strong, 1 = hint.
A platform needs a score of 2 or more. Commerce platforms and site builders
win over frameworks, so a headless Shopify store on Next.js reports
``shopify`` with ``nextjs`` under ``frameworks``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from scrapeplanner.html import HtmlDoc
from scrapeplanner.models import Confidence, PlatformName, PlatformReport

Where = Literal["header", "header_value", "cookie", "html", "generator"]


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
    # Other stacks, reported under ``frameworks`` only.
    Signal("wordpress", "generator", r"^WordPress", 3, "meta generator WordPress"),
    Signal(
        "wordpress", "html", r"/wp-content/(?:themes|plugins|uploads)/", 2, "/wp-content/ assets"
    ),
    Signal(
        "wordpress", "html", r"""rel=["']https://api\.w\.org/["']""", 3, "WordPress REST API link"
    ),
    Signal("drupal", "generator", r"^Drupal", 3, "meta generator Drupal"),
    Signal("drupal", "header", "x-drupal-cache", 3, "header x-drupal-cache"),
    Signal("drupal", "html", r"drupalSettings", 2, "drupalSettings script"),
    Signal("gatsby", "html", r"""id=["']___gatsby["']""", 3, "#___gatsby root"),
    Signal("sveltekit", "html", r"__sveltekit_", 3, "SvelteKit bootstrap"),
    Signal("astro", "html", r"<astro-island\b", 3, "astro-island element"),
    Signal("remix", "html", r"__remixContext", 3, "Remix context"),
    Signal("angular", "html", r"\bng-version=", 3, "Angular ng-version"),
    Signal("hugo", "generator", r"^Hugo", 3, "meta generator Hugo"),
    Signal("docusaurus", "generator", r"^Docusaurus", 3, "meta generator Docusaurus"),
    Signal(
        "sphinx",
        "html",
        r"_static/(?:sphinx_highlight|documentation_options)\.js",
        3,
        "Sphinx static assets",
    ),
)

COMMERCE_AND_BUILDERS: tuple[PlatformName, ...] = (
    "shopify",
    "woocommerce",
    "magento",
    "bigcommerce",
    "wix",
    "squarespace",
)
FRAMEWORKS: tuple[PlatformName, ...] = ("nextjs", "nuxt")
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
        else:
            fired = bool(regex.search(doc.html))
        if fired:
            scores[signal.name] = scores.get(signal.name, 0) + signal.weight
            evidence.setdefault(signal.name, []).append(signal.label)

    found = {name: score for name, score in scores.items() if score >= MIN_SCORE}
    report = PlatformReport(generator=generator)
    chosen: str | None = None
    for group in (COMMERCE_AND_BUILDERS, FRAMEWORKS):
        candidates = [name for name in group if name in found]
        if candidates:
            chosen = max(candidates, key=lambda name: found[name])
            break
    if chosen is not None:
        report.name = chosen  # type: ignore[assignment]
        report.confidence = _confidence(found[chosen])
        report.evidence = evidence[chosen]
    report.frameworks = sorted(
        (name for name in found if name != chosen), key=lambda name: (-found[name], name)
    )
    return report

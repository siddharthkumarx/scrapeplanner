"""Report models. ``Report`` is the schema of ``--json`` output.

Bump ``SCHEMA_VERSION`` on any breaking change to field names or meanings.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION: Literal["1"] = "1"

Confidence = Literal["high", "medium", "low"]
PlatformName = Literal[
    "shopify",
    "woocommerce",
    "magento",
    "bigcommerce",
    "wix",
    "squarespace",
    "nextjs",
    "nuxt",
    "unknown",
]
VendorName = Literal["cloudflare", "akamai", "datadome", "human", "imperva", "kasada", "aws_waf"]
MethodName = Literal["feed_api", "structured_data", "embedded_json", "html", "browser"]
RenderVerdict = Literal["raw_html", "embedded_json", "browser_likely", "unknown"]
FitVerdict = Literal["good", "caution", "not_a_fit", "unknown"]

PLATFORM_LABELS: dict[str, str] = {
    "shopify": "Shopify",
    "woocommerce": "WooCommerce",
    "magento": "Magento",
    "bigcommerce": "BigCommerce",
    "wix": "Wix",
    "squarespace": "Squarespace",
    "nextjs": "Next.js",
    "nuxt": "Nuxt",
    "unknown": "unknown",
}
VENDOR_LABELS: dict[str, str] = {
    "cloudflare": "Cloudflare",
    "akamai": "Akamai",
    "datadome": "DataDome",
    "human": "HUMAN/PerimeterX",
    "imperva": "Imperva",
    "kasada": "Kasada",
    "aws_waf": "AWS WAF",
}
METHOD_LABELS: dict[str, str] = {
    "feed_api": "Public feed / JSON API",
    "structured_data": "Structured data (JSON-LD / microdata)",
    "embedded_json": "Embedded JSON state",
    "html": "HTML parsing",
    "browser": "Headless browser",
}

METHOD_SHORT: dict[str, str] = {
    "feed_api": "Feed / API",
    "structured_data": "Structured data",
    "embedded_json": "Embedded JSON",
    "html": "HTML",
    "browser": "Browser",
}


def vendor_label(vendor: str, status: str, bot_management: bool) -> str:
    """'Cloudflare (CDN only)', 'DataDome (challenge)', 'Akamai (present)'."""
    if status == "challenge":
        return f"{VENDOR_LABELS[vendor]} (challenge)"
    return f"{VENDOR_LABELS[vendor]} ({'present' if bot_management else 'CDN only'})"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ToolInfo(_Model):
    name: str = "scrapeplanner"
    version: str
    user_agent: str


class RequestLogEntry(_Model):
    """One HTTP request the tool actually sent."""

    method: str = "GET"
    url: str
    purpose: str
    status: int | None = None
    elapsed_ms: int = 0
    bytes: int = 0
    error: str | None = None


class SkippedRequest(_Model):
    """A request the tool wanted to send but did not."""

    url: str
    purpose: str
    reason: Literal["robots", "budget", "blocked", "crawl_delay"]


class StopInfo(_Model):
    reason: Literal["blocked", "challenge", "rate_limited", "robots", "crawl_delay", "error"]
    url: str
    detail: str


class PageInfo(_Model):
    url: str
    final_url: str | None = None
    fetched: bool = False
    status: int | None = None
    content_type: str | None = None
    bytes: int = 0
    title: str | None = None
    lang: str | None = None


class RobotsReport(_Model):
    url: str
    fetched: bool = False
    status: int | None = None
    found: bool = False
    """A robots.txt with content was served (2xx)."""
    disallow_all: bool = False
    """Access is treated as fully disallowed (e.g. 401/403/5xx on robots.txt)."""
    paths: dict[str, bool] = Field(default_factory=dict)
    """Paths the tool would use -> allowed for our user agent."""
    crawl_delay: float | None = None
    request_rate: str | None = None
    sitemaps: list[str] = Field(default_factory=list)
    note: str | None = None


class SitemapReport(_Model):
    url: str | None = None
    source: Literal["robots", "default", "none"] = "none"
    fetched: bool = False
    status: int | None = None
    kind: Literal["urlset", "sitemapindex", "invalid"] | None = None
    url_count: int | None = None
    child_sitemaps: int | None = None
    newest_lastmod: str | None = None
    oldest_lastmod: str | None = None
    with_lastmod: int = 0
    sample_urls: list[str] = Field(default_factory=list)
    truncated: bool = False
    note: str | None = None
    child: SitemapReport | None = None
    """For a sitemap index: the one child sitemap that was read."""


class PlatformReport(_Model):
    name: PlatformName = "unknown"
    confidence: Confidence | None = None
    evidence: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    """Other stacks seen (e.g. ``nextjs`` under a headless Shopify, ``wordpress``)."""
    generator: str | None = None


class VendorHit(_Model):
    vendor: VendorName
    status: Literal["present", "challenge"]
    bot_management: bool = True
    """False when only CDN headers were seen (e.g. Cloudflare cf-ray, server: AkamaiGHost)."""
    evidence: list[str] = Field(default_factory=list)


class AntiBotReport(_Model):
    vendors: list[VendorHit] = Field(default_factory=list)
    challenged: bool = False
    challenge_url: str | None = None


class StructuredItem(_Model):
    type: str
    source: Literal["json-ld", "microdata"]
    count: int
    fields: list[str] = Field(default_factory=list)
    """Key fields present on at least one item of this type."""
    sample: dict[str, str] = Field(default_factory=dict)


class StructuredDataReport(_Model):
    jsonld_blocks: int = 0
    jsonld_invalid: int = 0
    microdata_items: int = 0
    types: dict[str, int] = Field(default_factory=dict)
    items: list[StructuredItem] = Field(default_factory=list)
    key_types: list[str] = Field(default_factory=list)
    """Types that carry collectable records (Product, JobPosting, Article...)."""


class EmbeddedBlob(_Model):
    kind: Literal[
        "next_data",
        "next_flight",
        "nuxt_data",
        "nuxt_state",
        "apollo_state",
        "redux_state",
        "json_script",
    ]
    locator: str
    bytes: int
    keys: list[str] = Field(default_factory=list)
    details: dict[str, str] = Field(default_factory=dict)


class EmbeddedStateReport(_Model):
    blobs: list[EmbeddedBlob] = Field(default_factory=list)


class RenderingReport(_Model):
    verdict: RenderVerdict = "unknown"
    html_bytes: int = 0
    text_chars: int = 0
    links: int = 0
    script_bytes: int = 0
    app_shell: bool = False
    noscript_warning: bool = False
    reasons: list[str] = Field(default_factory=list)


class FeedCandidate(_Model):
    kind: Literal[
        "shopify_products_json",
        "shopify_product_js",
        "woo_store_api",
        "wp_rest",
        "json_link",
        "json_feed",
        "rss",
        "atom",
    ]
    url: str
    status: Literal[
        "ok", "not_found", "invalid", "skipped_robots", "skipped_budget", "blocked", "linked"
    ]
    """``linked``: found on the page but not requested (budget kept for others)."""
    http_status: int | None = None
    items_seen: int | None = None
    """Records in the probe response."""
    total_items: int | None = None
    """Total the endpoint reports (e.g. the X-WP-Total header)."""
    page_size: int | None = None
    fields: list[str] = Field(default_factory=list)
    note: str | None = None


class FeedsReport(_Model):
    candidates: list[FeedCandidate] = Field(default_factory=list)


class MethodPlan(_Model):
    name: MethodName
    usable: bool
    summary: str
    urls: list[str] = Field(default_factory=list)
    fields: list[str] = Field(default_factory=list)
    est_requests: int | None = None
    est_hours: float | None = None
    partial: bool = False
    """The method reaches only part of the N items (e.g. a feed of the latest posts)."""
    notes: list[str] = Field(default_factory=list)


class RatePlan(_Model):
    delay_seconds: float
    concurrency: int = 1
    max_requests_per_day: int | None = None
    reason: str


class Plan(_Model):
    verdict: FitVerdict
    recommended: MethodName | None = None
    items: int
    rate: RatePlan
    methods: list[MethodPlan]
    risks: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class Report(_Model):
    schema_version: Literal["1"] = SCHEMA_VERSION
    tool: ToolInfo
    input_url: str
    site: str
    started_at: str
    duration_seconds: float
    max_requests: int
    requests_used: int
    requests: list[RequestLogEntry] = Field(default_factory=list)
    skipped: list[SkippedRequest] = Field(default_factory=list)
    stopped: StopInfo | None = None
    page: PageInfo
    robots: RobotsReport
    sitemap: SitemapReport
    platform: PlatformReport
    antibot: AntiBotReport
    structured: StructuredDataReport
    embedded: EmbeddedStateReport
    rendering: RenderingReport
    feeds: FeedsReport
    plan: Plan

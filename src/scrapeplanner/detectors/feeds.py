"""Public feeds and JSON endpoints: which to probe, and whether a response is valid.

``candidates()`` proposes URLs; the analyzer decides how many to request
within the budget; ``evaluate()`` checks a response's shape.
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlsplit

from scrapeplanner.html import HtmlDoc
from scrapeplanner.models import FeedCandidate, PlatformReport

SHOPIFY_PAGE_SIZE = 250
WOO_PAGE_SIZE = 100
WP_PAGE_SIZE = 100
MAX_FIELDS = 15

_FEED_TYPES = {
    "application/rss+xml": "rss",
    "application/atom+xml": "atom",
    "application/feed+json": "json_feed",
    "application/json": "json_link",
}
_SHOPIFY_HANDLE = re.compile(r"/products/([a-z0-9][a-z0-9\-_.%]*)", re.IGNORECASE)


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def shopify_handle(doc: HtmlDoc) -> str | None:
    for path in doc.same_site_paths():
        match = _SHOPIFY_HANDLE.search(path)
        if match and not match.group(1).endswith((".js", ".json")):
            return match.group(1)
    return None


def candidates(platform: PlatformReport, doc: HtmlDoc | None, page_url: str) -> list[FeedCandidate]:
    """Feeds worth probing, best first. All start as ``linked`` (not requested)."""
    origin = _origin(page_url)
    found: list[FeedCandidate] = []

    def add(kind: str, url: str, note: str | None = None) -> None:
        if all(existing.url != url for existing in found):
            found.append(FeedCandidate(kind=kind, url=url, status="linked", note=note))  # type: ignore[arg-type]

    is_wordpress = platform.name == "woocommerce" or "wordpress" in platform.frameworks
    if platform.name == "shopify":
        add("shopify_products_json", f"{origin}/products.json?limit={SHOPIFY_PAGE_SIZE}")
        handle = shopify_handle(doc) if doc else None
        if handle:
            add("shopify_product_js", f"{origin}/products/{handle}.js")
    if platform.name == "woocommerce":
        add("woo_store_api", f"{origin}/wp-json/wc/store/v1/products?per_page=1")
    if doc is not None:
        for link in doc.links:
            if "alternate" not in link.rel.split():
                continue
            kind = _FEED_TYPES.get(link.type)
            if kind and _origin(link.href) == origin:
                if "/comments/feed" in link.href or "oembed" in link.href:
                    continue
                add(kind, link.href, note=link.title or None)
    if is_wordpress and platform.name != "woocommerce":
        add("wp_rest", f"{origin}/wp-json/wp/v2/posts?per_page=1")
    return found


def _fields(item: Any) -> list[str]:
    if isinstance(item, dict):
        return [str(key) for key in list(item)[:MAX_FIELDS]]
    return []


def _xml_count(text: str, tag: str) -> int:
    return len(re.findall(rf"<{tag}[\s>]", text))


def evaluate(
    candidate: FeedCandidate,
    status: int,
    content_type: str,
    text: str,
    headers: dict[str, str],
) -> FeedCandidate:
    """Fill status, items and fields from a probe response."""
    result = candidate.model_copy()
    result.http_status = status
    if status in (404, 410):
        result.status = "not_found"
        return result
    if not 200 <= status < 300:
        result.status = "invalid"
        result.note = f"HTTP {status}"
        return result

    kind = candidate.kind
    if kind in ("rss", "atom"):
        tag = "item" if kind == "rss" else "entry"
        count = _xml_count(text, tag)
        if count or "<rss" in text[:500] or "<feed" in text[:500]:
            result.status = "ok"
            result.items_seen = count
            result.page_size = count or None
        else:
            result.status = "invalid"
            result.note = "not an RSS/Atom document"
        return result

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, RecursionError):
        result.status = "invalid"
        result.note = f"not JSON ({content_type or 'no content-type'})"
        return result

    lowered = {key.lower(): value for key, value in headers.items()}
    if kind == "shopify_products_json":
        products = data.get("products") if isinstance(data, dict) else None
        if isinstance(products, list):
            result.status = "ok"
            result.items_seen = len(products)
            result.page_size = SHOPIFY_PAGE_SIZE
            result.fields = _fields(products[0]) if products else []
            if len(products) < SHOPIFY_PAGE_SIZE:
                result.note = f"whole catalog fits in one page ({len(products)} products)"
        else:
            result.status = "invalid"
            result.note = "no 'products' list"
    elif kind == "shopify_product_js":
        if isinstance(data, dict) and "variants" in data:
            result.status = "ok"
            result.items_seen = 1
            result.fields = _fields(data)
        else:
            result.status = "invalid"
            result.note = "no 'variants' in product JSON"
    elif kind in ("woo_store_api", "wp_rest"):
        if isinstance(data, list):
            result.status = "ok"
            result.items_seen = len(data)
            result.page_size = WOO_PAGE_SIZE if kind == "woo_store_api" else WP_PAGE_SIZE
            result.fields = _fields(data[0]) if data else []
            total = lowered.get("x-wp-total", "")
            if total.isdigit():
                result.total_items = int(total)
        else:
            result.status = "invalid"
            result.note = "expected a JSON list"
    elif kind == "json_feed":
        items = data.get("items") if isinstance(data, dict) else None
        if isinstance(items, list):
            result.status = "ok"
            result.items_seen = len(items)
            result.page_size = len(items) or None
            result.fields = _fields(items[0]) if items else []
        else:
            result.status = "invalid"
            result.note = "no 'items' list"
    else:  # generic JSON link
        result.status = "ok"
        if isinstance(data, list):
            result.items_seen = len(data)
            result.fields = _fields(data[0]) if data else []
        else:
            result.fields = _fields(data)
    return result

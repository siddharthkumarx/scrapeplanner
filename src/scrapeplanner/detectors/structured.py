"""Structured data: JSON-LD and microdata (schema.org).

Own parser on top of the shared selectolax tree (see D-002 for why not extruct).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from typing import Any

from selectolax.lexbor import LexborNode

from scrapeplanner.html import HtmlDoc
from scrapeplanner.models import StructuredDataReport, StructuredItem

KEY_TYPES: frozenset[str] = frozenset(
    {
        "Product",
        "ProductGroup",
        "IndividualProduct",
        "ProductModel",
        "Vehicle",
        "Car",
        "JobPosting",
        "Article",
        "NewsArticle",
        "BlogPosting",
        "TechArticle",
        "ScholarlyArticle",
        "Report",
        "LiveBlogPosting",
        "AnalysisNewsArticle",
        "ReportageNewsArticle",
        "Event",
        "Recipe",
        "Course",
        "Book",
        "Movie",
        "Dataset",
        "SoftwareApplication",
        "RealEstateListing",
        "Accommodation",
        "Hotel",
        "LodgingBusiness",
        "Residence",
        "LocalBusiness",
        "Restaurant",
        "Store",
        "Place",
        "Review",
        "ItemList",
        "OfferCatalog",
        "VideoObject",
        "PodcastEpisode",
        "FAQPage",
        "QAPage",
        "HowTo",
    }
)
"""Types that carry records worth collecting (WebSite, BreadcrumbList... are not)."""

# Fields reported per type (dotted paths into the item). Samples are only taken
# from SAMPLE_FIELDS so that people's names never end up in a report.
FIELDS: dict[str, tuple[str, ...]] = {
    "Product": (
        "name",
        "sku",
        "gtin13",
        "gtin",
        "mpn",
        "brand",
        "image",
        "description",
        "offers.price",
        "offers.lowPrice",
        "offers.priceCurrency",
        "offers.availability",
        "aggregateRating.ratingValue",
        "review",
    ),
    "JobPosting": (
        "title",
        "datePosted",
        "validThrough",
        "employmentType",
        "hiringOrganization",
        "jobLocation",
        "baseSalary",
        "description",
        "directApply",
    ),
    "Article": (
        "headline",
        "datePublished",
        "dateModified",
        "author",
        "image",
        "articleSection",
        "publisher",
    ),
    "Event": ("name", "startDate", "endDate", "location", "offers", "eventStatus"),
    "Recipe": ("name", "recipeIngredient", "recipeInstructions", "totalTime", "aggregateRating"),
    "ItemList": ("numberOfItems", "itemListElement"),
    "LocalBusiness": ("name", "address", "geo", "openingHours", "priceRange", "aggregateRating"),
}
FIELD_ALIASES = {
    "NewsArticle": "Article",
    "BlogPosting": "Article",
    "TechArticle": "Article",
    "ScholarlyArticle": "Article",
    "LiveBlogPosting": "Article",
    "Report": "Article",
    "AnalysisNewsArticle": "Article",
    "ReportageNewsArticle": "Article",
    "ProductGroup": "Product",
    "IndividualProduct": "Product",
    "ProductModel": "Product",
    "Vehicle": "Product",
    "Car": "Product",
    "Restaurant": "LocalBusiness",
    "Store": "LocalBusiness",
    "Hotel": "LocalBusiness",
    "LodgingBusiness": "LocalBusiness",
    "OfferCatalog": "ItemList",
}
SAMPLE_FIELDS = frozenset(
    {
        "name",
        "title",
        "headline",
        "sku",
        "offers.price",
        "offers.lowPrice",
        "offers.priceCurrency",
        "offers.availability",
        "datePosted",
        "datePublished",
        "employmentType",
        "startDate",
        "numberOfItems",
    }
)
SAMPLE_MAX_CHARS = 80
_TRAILING_COMMA = re.compile(r",\s*([}\]])")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _type_names(value: Any) -> list[str]:
    raw = value if isinstance(value, list) else [value]
    names = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            names.append(item.strip().rstrip("/").rsplit("/", 1)[-1].rsplit("#", 1)[-1])
    return names


def _loads_lenient(text: str) -> Any:
    text = text.strip()
    for prefix, suffix in (("<!--", "-->"), ("<![CDATA[", "]]>"), ("//<![CDATA[", "//]]>")):
        if text.startswith(prefix) and text.endswith(suffix):
            text = text[len(prefix) : -len(suffix)].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    cleaned = _TRAILING_COMMA.sub(r"\1", _CONTROL.sub(" ", text))
    return json.loads(cleaned, strict=False)


def _walk_typed(node: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    """Every dict with an @type, depth first, including @graph members."""
    if isinstance(node, list):
        for item in node:
            yield from _walk_typed(item)
    elif isinstance(node, dict):
        for name in _type_names(node.get("@type")):
            yield name, node
        for key, value in node.items():
            if key != "@context" and isinstance(value, (dict, list)):
                yield from _walk_typed(value)


def _get(item: dict[str, Any], path: str) -> Any:
    value: Any = item
    for part in path.split("."):
        if isinstance(value, list):
            value = value[0] if value else None
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    if isinstance(value, list):
        value = value[0] if value else None
    return value


def _present(value: Any) -> bool:
    return value not in (None, "", [], {})


def _as_text(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("name") or value.get("@id") or ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text[:SAMPLE_MAX_CHARS]


# -- microdata ------------------------------------------------------------


def _microdata_value(node: LexborNode) -> str:
    attrs = node.attributes
    if "content" in attrs:
        return attrs.get("content") or ""
    tag = node.tag
    if tag in ("a", "link", "area"):
        return attrs.get("href") or ""
    if tag in ("img", "audio", "video", "source", "iframe", "embed"):
        return attrs.get("src") or ""
    if tag == "meta":
        return attrs.get("content") or ""
    if tag in ("time",) and "datetime" in attrs:
        return attrs.get("datetime") or ""
    if tag in ("data", "meter") and "value" in attrs:
        return attrs.get("value") or ""
    return node.text(deep=True)


def _microdata_items(doc: HtmlDoc) -> list[tuple[list[str], dict[str, Any], bool]]:
    """Return (types, properties, is_top_level) for each itemscope element."""
    scopes: dict[int, tuple[LexborNode, dict[str, Any]]] = {}
    for node in doc.tree.css("[itemscope]"):
        scopes[node.mem_id] = (node, {})

    def owner(node: LexborNode) -> int | None:
        parent = node.parent
        while parent is not None:
            if parent.mem_id in scopes:
                return parent.mem_id
            parent = parent.parent
        return None

    for node in doc.tree.css("[itemprop]"):
        scope_id = owner(node)
        if scope_id is None:
            continue
        names = (node.attributes.get("itemprop") or "").split()
        if node.mem_id in scopes:
            value: Any = scopes[node.mem_id][1]
        else:
            value = _microdata_value(node)
        for name in names:
            scopes[scope_id][1].setdefault(name, value)

    items = []
    for node, props in scopes.values():
        types = _type_names((node.attributes.get("itemtype") or "").split())
        if types:
            items.append((types, props, "itemprop" not in node.attributes))
    return items


# -- report ----------------------------------------------------------------


def _summarise(
    report: StructuredDataReport,
    source: str,
    typed: list[tuple[str, dict[str, Any]]],
) -> None:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for name, item in typed:
        report.types[name] = report.types.get(name, 0) + 1
        grouped.setdefault(name, []).append(item)
    for name, items in grouped.items():
        if name not in KEY_TYPES:
            continue
        fields = FIELDS.get(FIELD_ALIASES.get(name, name), ())
        present = [path for path in fields if any(_present(_get(item, path)) for item in items)]
        sample = {}
        for path in present:
            if path in SAMPLE_FIELDS:
                value = _get(items[0], path)
                if _present(value):
                    sample[path] = _as_text(value)
        report.items.append(
            StructuredItem(
                type=name,
                source=source,  # type: ignore[arg-type]
                count=len(items),
                fields=present,
                sample=sample,
            )
        )


def detect(doc: HtmlDoc) -> StructuredDataReport:
    report = StructuredDataReport()
    typed: list[tuple[str, dict[str, Any]]] = []
    for script in doc.scripts:
        if script.type != "application/ld+json":
            continue
        report.jsonld_blocks += 1
        try:
            data = _loads_lenient(script.text)
        except (json.JSONDecodeError, ValueError, RecursionError):
            report.jsonld_invalid += 1
            continue
        typed.extend(_walk_typed(data))
    _summarise(report, "json-ld", typed)

    micro = _microdata_items(doc)
    report.microdata_items = sum(1 for _, _, top in micro if top)
    micro_typed = [(name, props) for types, props, _ in micro for name in types]
    _summarise(report, "microdata", micro_typed)

    order = {name: index for index, name in enumerate(sorted(report.types))}
    report.items.sort(key=lambda item: (-item.count, order.get(item.type, 0), item.source))
    report.key_types = sorted({item.type for item in report.items})
    return report

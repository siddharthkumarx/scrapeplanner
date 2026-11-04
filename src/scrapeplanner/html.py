"""One HTML parse per page, shared by the detectors."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property
from urllib.parse import urljoin, urlsplit

from selectolax.lexbor import LexborHTMLParser, LexborNode

_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class Script:
    attrs: dict[str, str]
    text: str

    @property
    def type(self) -> str:
        return self.attrs.get("type", "").strip().lower()

    @property
    def src(self) -> str:
        return self.attrs.get("src", "")

    @property
    def id(self) -> str:
        return self.attrs.get("id", "")


@dataclass(frozen=True)
class Link:
    rel: str
    type: str
    href: str
    title: str


def _attrs(node: LexborNode) -> dict[str, str]:
    return {key.lower(): (value or "") for key, value in node.attributes.items()}


class HtmlDoc:
    """Read-only helpers over a parsed HTML document."""

    def __init__(self, html: str, base_url: str) -> None:
        self.html = html
        self.base_url = base_url
        self.tree = LexborHTMLParser(html)

    def absolute(self, href: str) -> str:
        return urljoin(self.base_url, href.strip())

    @cached_property
    def title(self) -> str | None:
        node = self.tree.css_first("title")
        if node is None:
            return None
        text = _WS_RE.sub(" ", node.text()).strip()
        return text[:200] or None

    @cached_property
    def lang(self) -> str | None:
        node = self.tree.css_first("html")
        if node is None:
            return None
        return (node.attributes.get("lang") or "").strip() or None

    def meta(self, name: str) -> str | None:
        for node in self.tree.css("meta"):
            attrs = _attrs(node)
            if attrs.get("name", "").lower() == name or attrs.get("property", "").lower() == name:
                return attrs.get("content", "").strip() or None
        return None

    @cached_property
    def scripts(self) -> list[Script]:
        return [Script(_attrs(node), node.text(deep=True)) for node in self.tree.css("script")]

    @cached_property
    def script_srcs(self) -> list[str]:
        return [self.absolute(script.src) for script in self.scripts if script.src]

    @cached_property
    def links(self) -> list[Link]:
        result = []
        for node in self.tree.css("link[href]"):
            attrs = _attrs(node)
            result.append(
                Link(
                    rel=attrs.get("rel", "").lower(),
                    type=attrs.get("type", "").lower(),
                    href=self.absolute(attrs.get("href", "")),
                    title=attrs.get("title", ""),
                )
            )
        return result

    @cached_property
    def anchors(self) -> list[str]:
        hrefs = []
        for node in self.tree.css("a[href]"):
            href = (node.attributes.get("href") or "").strip()
            if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                hrefs.append(self.absolute(href))
        return hrefs

    def same_site_paths(self) -> list[str]:
        """Paths of links that stay on this host, in page order, deduplicated."""
        host = urlsplit(self.base_url).netloc.lower()
        seen: dict[str, None] = {}
        for href in self.anchors:
            parts = urlsplit(href)
            if parts.netloc.lower() == host and parts.path:
                seen.setdefault(parts.path, None)
        return list(seen)

    @cached_property
    def visible_text(self) -> str:
        """Text a reader would see without JavaScript (scripts, styles removed)."""
        clone = LexborHTMLParser(self.html)
        clone.strip_tags(["script", "style", "noscript", "template", "svg", "head"])
        body = clone.body
        text = body.text(separator=" ") if body is not None else ""
        return _WS_RE.sub(" ", text).strip()

    @cached_property
    def noscript_text(self) -> str:
        return " ".join(node.text(separator=" ") for node in self.tree.css("noscript"))

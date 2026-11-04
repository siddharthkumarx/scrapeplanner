"""Sitemap and sitemap-index parsing: URL count, lastmod range, sample URLs."""

from __future__ import annotations

import gzip
import io
import zlib
from typing import cast
from xml.etree.ElementTree import Element, ParseError, XMLPullParser

from scrapeplanner.models import SitemapReport

MAX_DECOMPRESSED = 60_000_000  # the sitemaps.org limit is 50 MB uncompressed
SAMPLE_SIZE = 5


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _maybe_gunzip(body: bytes) -> tuple[bytes, bool]:
    """Return (xml bytes, truncated)."""
    if not body.startswith(b"\x1f\x8b"):
        return body, False
    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        data = decompressor.decompress(body, MAX_DECOMPRESSED)
    except zlib.error:
        try:  # a cut-off gzip stream still yields its first part
            return gzip.GzipFile(fileobj=io.BytesIO(body)).read(MAX_DECOMPRESSED), True
        except (OSError, EOFError):
            return b"", True
    return data, bool(decompressor.unconsumed_tail) or not decompressor.eof


MAX_CHILDREN_KEPT = 500


def parse(body: bytes, *, truncated: bool = False) -> tuple[SitemapReport, list[str]]:
    """Parse sitemap XML (plain or gzipped). Never resolves entities or DTDs.

    Returns the report and, for a sitemap index, the child sitemap URLs (capped).
    """
    report = SitemapReport()
    locs: list[str] = []
    xml, cut = _maybe_gunzip(body)
    report.truncated = truncated or cut
    head = xml[:2048].lower()
    if b"<!doctype" in head or b"<!entity" in head:
        report.kind = "invalid"
        report.note = "DTD or entity declarations refused"
        return report, []
    parser: XMLPullParser[Element] = XMLPullParser(events=("start", "end"))
    root: str | None = None
    count = 0
    lastmods: list[str] = []
    sample: list[str] = []
    in_entry = False
    entry_has_loc = False  # image:loc and video:loc nest inside <url>; keep the first <loc>
    try:
        for offset in range(0, len(xml), 65536):
            parser.feed(xml[offset : offset + 65536])
            for item in parser.read_events():
                event, element = cast("tuple[str, object]", item)
                if not isinstance(element, Element):
                    continue
                tag = _local(str(element.tag))
                if event == "start":
                    if root is None:
                        root = tag
                    if tag in ("url", "sitemap"):
                        in_entry = True
                        entry_has_loc = False
                    continue
                if tag in ("url", "sitemap") and in_entry:
                    count += 1
                    in_entry = False
                    element.clear()
                elif tag == "loc" and in_entry and not entry_has_loc and element.text:
                    entry_has_loc = True
                    if len(sample) < SAMPLE_SIZE:
                        sample.append(element.text.strip())
                    if len(locs) < MAX_CHILDREN_KEPT:
                        locs.append(element.text.strip())
                elif tag == "lastmod" and in_entry and element.text:
                    lastmods.append(element.text.strip()[:10])
        parser.close()
    except ParseError:
        if count == 0 and root is None:
            report.kind = "invalid"
            report.note = "not XML"
            return report, []
        report.truncated = True
    if root == "urlset":
        report.kind = "urlset"
        report.url_count = count
    elif root == "sitemapindex":
        report.kind = "sitemapindex"
        report.child_sitemaps = count
    else:
        report.kind = "invalid"
        report.note = f"root element <{root}> is not a sitemap" if root else "empty"
        return report, []
    dated = sorted(value for value in lastmods if len(value) == 10 and value[4] == "-")
    report.with_lastmod = len(dated)
    if dated:
        report.newest_lastmod = dated[-1]
        report.oldest_lastmod = dated[0]
    report.sample_urls = sample
    return report, locs if root == "sitemapindex" else []


def pick_child(urls: list[str], hints: tuple[str, ...]) -> str | None:
    """From an index sample, prefer a child sitemap whose URL names the content type."""
    for hint in hints:
        for url in urls:
            if hint in url.lower():
                return url
    return urls[0] if urls else None

"""Is the key data in the raw HTML, in an embedded JSON blob, or only after JavaScript?"""

from __future__ import annotations

import re

from scrapeplanner.html import HtmlDoc
from scrapeplanner.models import EmbeddedStateReport, RenderingReport, StructuredDataReport

APP_ROOTS = ("#root", "#app", "#__next", "#__nuxt", "#___gatsby", "app-root", "#svelte")
MIN_TEXT_CHARS = 500
"""Below this much visible text a page is treated as thin."""
MIN_DATA_BLOB_BYTES = 5_000
_NOSCRIPT_RE = re.compile(
    r"enable javascript|javascript is (?:required|disabled)|requires javascript|"
    r"turn on javascript|need to enable javascript",
    re.IGNORECASE,
)


def detect(
    doc: HtmlDoc, structured: StructuredDataReport, embedded: EmbeddedStateReport
) -> RenderingReport:
    text = doc.visible_text
    report = RenderingReport(
        html_bytes=len(doc.html.encode("utf-8")),
        text_chars=len(text),
        links=len(doc.anchors),
        script_bytes=sum(len(script.text) for script in doc.scripts),
    )
    for selector in APP_ROOTS:
        node = doc.tree.css_first(selector)
        if node is not None and len(node.text(deep=True).strip()) < 50:
            report.app_shell = True
            report.reasons.append(f"empty app root {selector}")
            break
    if _NOSCRIPT_RE.search(doc.noscript_text):
        report.noscript_warning = True
        report.reasons.append("<noscript> asks for JavaScript")

    data_blobs = [blob for blob in embedded.blobs if blob.bytes >= MIN_DATA_BLOB_BYTES]
    thin = report.text_chars < MIN_TEXT_CHARS
    if structured.key_types:
        report.reasons.append("schema.org records in the HTML: " + ", ".join(structured.key_types))

    if thin and (report.app_shell or report.script_bytes > 10 * max(report.text_chars, 1)):
        if data_blobs:
            report.verdict = "embedded_json"
            report.reasons.append(f"data in {data_blobs[0].locator} ({data_blobs[0].bytes} bytes)")
        elif structured.key_types:
            report.verdict = "raw_html"
        else:
            report.verdict = "browser_likely"
            report.reasons.append(f"only {report.text_chars} characters of text without JavaScript")
    elif thin and not structured.key_types:
        report.verdict = "embedded_json" if data_blobs else "browser_likely"
        report.reasons.append(f"only {report.text_chars} characters of visible text")
    else:
        report.verdict = "raw_html"
        report.reasons.append(f"{report.text_chars} characters of text, {report.links} links")
        if data_blobs:
            report.reasons.append(f"also in {data_blobs[0].locator}")
    return report

#!/usr/bin/env python3
"""Render a Markdown file to PDF with the project's fonts (used for docs/private/explainer.pdf).

Usage::

    uv run --group visual python scripts/visuals/pdf.py docs/private/explainer.md
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from browser import chromium
from markdown_it import MarkdownIt
from svgkit import FONTS

CSS = """
@font-face{{font-family:'Instrument Sans';font-weight:400;
  src:url(data:font/woff2;base64,{sans400})}}
@font-face{{font-family:'Instrument Sans';font-weight:700;
  src:url(data:font/woff2;base64,{sans700})}}
@page{{size:A4;margin:20mm 18mm}}
body{{font-family:'Instrument Sans',sans-serif;font-size:11pt;line-height:1.5;color:#14211f}}
h1{{font-size:20pt;margin:0 0 6pt}} h2{{font-size:14pt;margin:18pt 0 6pt;color:#0f5e55}}
code{{font-family:'IBM Plex Mono',monospace;font-size:9.5pt;background:#eef4f2;padding:0 3px}}
li{{margin:3pt 0}} strong{{color:#0b1416}}
"""


def main(argv: list[str]) -> int:
    source = Path(argv[0])
    out = source.with_suffix(".pdf")
    fonts = {
        "sans400": base64.b64encode(
            (FONTS / "instrument-sans-latin-400-normal.woff2").read_bytes()
        ).decode(),
        "sans700": base64.b64encode(
            (FONTS / "instrument-sans-latin-700-normal.woff2").read_bytes()
        ).decode(),
    }
    body = MarkdownIt("commonmark").render(source.read_text(encoding="utf-8"))
    html = f"<!doctype html><meta charset='utf-8'><style>{CSS.format(**fonts)}</style>{body}"
    with chromium() as browser:
        page = browser.new_page()
        page.set_content(html)
        page.evaluate("document.fonts.ready")
        page.pdf(path=str(out), format="A4", print_background=True)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

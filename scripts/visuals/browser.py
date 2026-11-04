"""Headless Chromium helpers for rendering and checking the README visuals.

Set ``SCRAPEPLANNER_CHROMIUM`` to a Chromium binary to use a preinstalled browser;
otherwise Playwright's own (``uv run playwright install chromium``) is used.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from playwright.sync_api import Browser, Page, sync_playwright

Motion = Literal["reduce", "no-preference"]

# Seek every animation to the same point of its loop. ``at`` is a fraction of the loop.
SEEK_JS = """
(at) => {
  for (const a of document.getAnimations()) {
    const d = a.effect.getComputedTiming().duration;
    a.pause();
    a.currentTime = d * at;
  }
  return document.getAnimations().length;
}
"""


@contextmanager
def chromium() -> Iterator[Browser]:
    executable = os.environ.get("SCRAPEPLANNER_CHROMIUM") or None
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=executable)
        try:
            yield browser
        finally:
            browser.close()


def open_svg(browser: Browser, path: Path, *, motion: Motion, scale: float = 1.0) -> Page:
    """Load an SVG file as the whole page, sized to its width/height attributes."""
    text = path.read_text(encoding="utf-8")
    width = int(text.split('width="', 1)[1].split('"', 1)[0])
    height = int(text.split('height="', 1)[1].split('"', 1)[0])
    page = browser.new_page(
        viewport={"width": width, "height": height},
        device_scale_factor=scale,
        reduced_motion=motion,
    )
    page.goto(path.resolve().as_uri())
    page.evaluate("document.fonts.ready")
    return page


def seek(page: Page, at: float) -> int:
    """Pause all animations at fraction ``at`` of their loop; returns how many there are."""
    count = page.evaluate(SEEK_JS, at)
    assert isinstance(count, int)
    return count

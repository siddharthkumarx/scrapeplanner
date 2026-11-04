"""README visuals: size, self-containment, readability, and reduced motion.

Run with ``uv run --group visual pytest -m visual`` (Chromium needed: set
SCRAPEPLANNER_CHROMIUM or run ``uv run playwright install chromium``).
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")
from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "visuals"))

import browser as chromium_tools  # noqa: E402
import build  # noqa: E402

pytestmark = pytest.mark.visual
ANIMATED = ["hero", "ladder"]
ASSETS = ROOT / "assets"


def _png(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGB")


FAILURES = ROOT / "test-output" / "visual"


def _keep(name: str, **images: Image.Image) -> None:
    """Save the compared renders so a CI failure can be inspected (uploaded as artifact)."""
    FAILURES.mkdir(parents=True, exist_ok=True)
    for label, image in images.items():
        image.save(FAILURES / f"{name}-{label}.png")


def _diff(a: Image.Image, b: Image.Image) -> str:
    histogram = ImageChops.difference(a, b).convert("L").histogram()
    return f"pixels touched {sum(histogram[1:])}, above level 24: {sum(histogram[25:])}"


def _same(a: Image.Image, b: Image.Image) -> bool:
    """Equal up to antialiasing. Text in animated (composited) layers can be smoothed
    differently from static text, which changes edge pixels but nothing a reader sees.
    Both renders are compared as grayscale after a 1-pixel blur: a missing, moved or
    recoloured element still differs by far more than the 48-level threshold."""
    if a.size != b.size:
        return False
    soft_a = a.convert("L").filter(ImageFilter.BoxBlur(1))
    soft_b = b.convert("L").filter(ImageFilter.BoxBlur(1))
    histogram = ImageChops.difference(soft_a, soft_b).histogram()
    return sum(histogram[49:]) == 0


def test_assets_are_up_to_date() -> None:
    for path, text in build.build().items():
        assert path.read_text(encoding="utf-8") == text, f"{path.name} is stale: run build.py"


@pytest.mark.parametrize("name", [*ANIMATED, *(f"{n}-still" for n in ANIMATED)])
def test_svg_is_self_contained_and_small(name: str) -> None:
    path = ASSETS / f"{name}.svg"
    text = path.read_text(encoding="utf-8")
    assert path.stat().st_size < 1_000_000
    assert "<script" not in text
    # No external resources: only the SVG namespace may be an http(s) URL.
    urls = set(re.findall(r"""(?:href|src|url)\s*[=(]\s*["']?(https?://[^"')\s]+)""", text))
    assert urls == set()
    assert 'viewBox="0 0 1000 ' in text


@pytest.mark.parametrize("name", [*ANIMATED, *(f"{n}-still" for n in ANIMATED)])
def test_text_sizes(name: str) -> None:
    text = (ASSETS / f"{name}.svg").read_text(encoding="utf-8")
    sizes = [int(s) for s in re.findall(r'font-size="(\d+)"', text)]
    sizes += [int(s) for s in re.findall(r"font-size:(\d+)px", text)]
    assert sizes
    assert min(sizes) >= 30


@pytest.mark.parametrize("name", ANIMATED)
def test_reduced_motion_and_still_match_the_final_frame(name: str) -> None:
    with chromium_tools.chromium() as browser:
        final = chromium_tools.open_svg(browser, ASSETS / f"{name}.svg", motion="no-preference")
        assert chromium_tools.seek(final, 0.999) > 0
        final_png = _png(final.screenshot())
        early = _png((chromium_tools.seek(final, 0.05), final.screenshot())[1])

        reduced = chromium_tools.open_svg(browser, ASSETS / f"{name}.svg", motion="reduce")
        assert reduced.evaluate("document.getAnimations().length") == 0
        reduced_png = _png(reduced.screenshot())

        still = chromium_tools.open_svg(browser, ASSETS / f"{name}-still.svg", motion="reduce")
        still_png = _png(still.screenshot())

    ok = (
        not _same(early, final_png)
        and _same(reduced_png, final_png)
        and _same(still_png, final_png)
    )
    if not ok:
        _keep(name, early=early, final=final_png, reduced=reduced_png, still=still_png)
    assert not _same(early, final_png), "the animation should start from a different frame"
    assert _same(reduced_png, final_png), (
        f"reduced motion must show the final frame ({_diff(reduced_png, final_png)})"
    )
    assert _same(still_png, final_png), (
        f"the still must equal the final frame ({_diff(still_png, final_png)})"
    )

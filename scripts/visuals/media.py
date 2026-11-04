#!/usr/bin/env python3
"""Render the raster media from the built SVGs (needs Chromium and ffmpeg).

Usage::

    uv run --group visual python scripts/visuals/media.py             # PNG + MP4
    uv run --group visual python scripts/visuals/media.py --shots DIR # review screenshots

* ``assets/social-preview.png``  1280 x 640, from ``assets/src/social-preview.svg``
* ``media/linkedin-demo.mp4``    1080 x 1080, 30 fps, one 10 s loop of
  ``assets/src/linkedin-demo.svg`` (the same recorded run as the README hero)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from browser import chromium, open_svg, seek
from svgkit import BG, ROOT

FPS = 30
LOOP_SECONDS = 10.0


def social_png() -> Path:
    out = ROOT / "assets" / "social-preview.png"
    with chromium() as browser:
        page = open_svg(browser, ROOT / "assets" / "src" / "social-preview.svg", motion="reduce")
        page.screenshot(path=str(out))
    return out


def linkedin_mp4() -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise SystemExit("ffmpeg not found")
    out = ROOT / "media" / "linkedin-demo.mp4"
    out.parent.mkdir(exist_ok=True)
    frames = int(FPS * LOOP_SECONDS)
    with tempfile.TemporaryDirectory() as tmp, chromium() as browser:
        page = open_svg(
            browser, ROOT / "assets" / "src" / "linkedin-demo.svg", motion="no-preference"
        )
        for i in range(frames):
            seek(page, i / frames)
            page.screenshot(path=f"{tmp}/f{i:04d}.png")
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-loglevel",
                "error",
                "-framerate",
                str(FPS),
                "-i",
                f"{tmp}/f%04d.png",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-crf",
                "20",
                "-preset",
                "slow",
                "-movflags",
                "+faststart",
                "-metadata",
                "title=scrapeplanner: a recorded run",
                str(out),
            ],
            check=True,
        )
    return out


PAGE = """<!doctype html><meta charset="utf-8">
<style>body{{margin:0;background:{bg};padding:16px}}img{{width:100%;display:block;margin:0 0 24px}}
</style>{imgs}"""


def shots(directory: Path) -> list[Path]:
    """Each README visual inside a page at 390 and 1280 px, plus reduced-motion renders.

    The page uses the README's markup: a <picture> whose reduced-motion source is the
    still SVG (Chromium does not pass prefers-reduced-motion into SVG images)."""
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    with chromium() as browser:
        for name in ("hero", "ladder"):
            svg = ROOT / "assets" / f"{name}.svg"
            html = directory / f"{name}.html"
            still = ROOT / "assets" / f"{name}-still.svg"
            picture = (
                f'<picture><source media="(prefers-reduced-motion: reduce)" '
                f'srcset="{still.as_uri()}"><img src="{svg.as_uri()}" alt="{name}"></picture>'
            )
            html.write_text(PAGE.format(bg=BG, imgs=picture), "utf-8")
            for width in (390, 1280):
                for motion in ("no-preference", "reduce"):
                    page = browser.new_page(
                        viewport={"width": width, "height": 900}, reduced_motion=motion
                    )
                    page.goto(html.as_uri())
                    page.wait_for_timeout(9500 if motion == "no-preference" else 300)
                    path = directory / f"{name}-{width}-{motion}.png"
                    page.screenshot(path=str(path), full_page=True)
                    written.append(path)
                    page.close()
    return written


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shots", type=Path, help="write review screenshots to this directory")
    args = parser.parse_args(argv)
    if args.shots:
        for path in shots(args.shots):
            print(path)
        return 0
    print(social_png().relative_to(ROOT))
    print(linkedin_mp4().relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

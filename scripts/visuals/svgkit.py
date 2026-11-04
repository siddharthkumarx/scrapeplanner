"""Shared pieces for the README visuals: palette, embedded fonts, terminal text, animation.

Rules every visual follows (docs/decisions.md, D-013):

* 1000-px-wide viewBox; headings >= 36 px, terminal and body text >= 30 px;
* no external fonts or scripts: fonts are subset and embedded as base64 WOFF2;
* CSS animation only. The default style IS the final frame; animations live in
  ``@media (prefers-reduced-motion: no-preference)``, and under
  ``prefers-reduced-motion: reduce`` every animated element is also given its
  final-state styles explicitly, so reduced motion and the ``-still.svg`` twin
  both show the final frame.
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont
from rich.console import Console, RenderableType
from rich.segment import Segment

ROOT = Path(__file__).resolve().parents[2]
FONTS = ROOT / "assets" / "src" / "fonts"
ICONS = ROOT / "assets" / "src" / "icons"

BG = "#0B1416"
PANEL = "#0F1C1E"
BORDER = "#1D3331"
MAIN = "#EAF2F0"
BODY = "#C9D8D5"
QUIET = "#7E9996"
TEAL = "#2FBFAE"
AMBER = "#E9A93C"

SANS = "Instrument Sans"
MONO = "IBM Plex Mono"
FONT_FILES = {
    (SANS, 400): "instrument-sans-latin-400-normal.woff2",
    (SANS, 600): "instrument-sans-latin-600-normal.woff2",
    (SANS, 700): "instrument-sans-latin-700-normal.woff2",
    (MONO, 400): "IBMPlexMono-Regular.ttf",
    (MONO, 600): "IBMPlexMono-SemiBold.ttf",
}


@dataclass(frozen=True)
class Term:
    """Terminal text metrics. IBM Plex Mono's advance width is 600/1000 em."""

    size: int = 30
    columns: int = 50

    @property
    def line(self) -> float:
        return self.size * 1.4

    @property
    def char(self) -> float:
        return self.size * 0.6


TERM = Term()
"""30 px text, 50 columns: fits a 1000-px viewBox with 50 px side padding."""
TERM_SIZE = TERM.size
TERM_LINE = TERM.line
TERM_CHAR = TERM.char
TERM_COLUMNS = TERM.columns

_BOX = set("╭╮╰╯─│┌┐└┘├┤┬┴┼━┃")


def esc(text: str) -> str:
    return escape(text, {'"': "&quot;"})


@cache
def _subset_woff2(path: Path, text: str) -> bytes:
    font = TTFont(path, recalcTimestamp=False)  # keep output byte-stable across runs
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["kern", "liga"]
    options.hinting = False
    options.name_IDs = [0, 1, 2]  # copyright, family, subfamily
    options.notdef_outline = True
    subsetter = subset.Subsetter(options)
    subsetter.populate(text=text + " ")
    subsetter.subset(font)
    out = io.BytesIO()
    font.flavor = "woff2"
    font.save(out)
    return out.getvalue()


def font_css(used: dict[tuple[str, int], str]) -> str:
    """@font-face rules with only the glyphs each family/weight actually uses."""
    rules = []
    for (family, weight), text in sorted(used.items()):
        if not text:
            continue
        data = _subset_woff2(FONTS / FONT_FILES[(family, weight)], "".join(sorted(set(text))))
        b64 = base64.b64encode(data).decode("ascii")
        rules.append(
            f"@font-face{{font-family:'{family}';font-weight:{weight};"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}"
        )
    return "\n".join(rules)


@dataclass
class Canvas:
    """Collects SVG elements, the text each font needs, and per-element animations."""

    width: int
    height: int
    title: str
    desc: str
    duration: float
    body: list[str] = field(default_factory=list)
    used: dict[tuple[str, int], str] = field(default_factory=dict)
    keyframes: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    finals: list[str] = field(default_factory=list)
    statics: list[str] = field(default_factory=list)
    """Plain CSS rules; they hold each element's default (= final-frame) style."""
    term: Term = TERM
    _n: int = 0

    def text_use(self, family: str, weight: int, text: str) -> None:
        key = (family, weight)
        self.used[key] = self.used.get(key, "") + text

    def anim_class(self, frames: list[tuple[float, str]], easing: str = "linear") -> str:
        """A class whose animation passes through ``frames`` (time in s, CSS declarations).

        The last frame must equal the element's default (final) style; it is held
        to the end of the loop.
        """
        self._n += 1
        name = f"a{self._n}"
        steps = []
        for t, css in frames:
            pct = max(0.0, min(100.0, t / self.duration * 100))
            steps.append(f"{pct:.2f}%{{{css}}}")
        last_css = frames[-1][1]
        steps.append(f"100%{{{last_css}}}")
        self.keyframes.append(f"@keyframes {name}{{{''.join(steps)}}}")
        self.rules.append(f".{name}{{animation:{name} {self.duration}s {easing} infinite both}}")
        self.finals.append(f".{name}{{animation:none;{last_css}}}")
        return name

    def appear(self, at: float, fade: float = 0.25) -> str:
        """Hidden until ``at`` seconds, then fades in and stays."""
        return self.anim_class([(0, "opacity:0"), (at, "opacity:0"), (at + fade, "opacity:1")])

    def render(self, *, animated: bool) -> str:
        css = [
            font_css(self.used),
            f"text{{font-family:'{SANS}',sans-serif}}",
            f".m{{font-family:'{MONO}',monospace;font-size:{self.term.size}px}}",
            *self.statics,
        ]
        if animated:
            css.append(
                "@media (prefers-reduced-motion: no-preference){"
                + "".join(self.keyframes)
                + "".join(self.rules)
                + "}"
            )
            # Reduced motion: every animated element takes its final-state styles.
            css.append("@media (prefers-reduced-motion: reduce){" + "".join(self.finals) + "}")
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}" '
            f'width="{self.width}" height="{self.height}" role="img" '
            f'aria-labelledby="t d">\n'
            f'<title id="t">{esc(self.title)}</title>\n<desc id="d">{esc(self.desc)}</desc>\n'
            f"<style>{''.join(css)}</style>\n"
            f'<rect width="100%" height="100%" fill="{BG}"/>\n'
            + "\n".join(self.body)
            + "\n</svg>\n"
        )


def rich_lines(renderable: RenderableType, width: int = TERM_COLUMNS) -> list[list[Segment]]:
    console = Console(
        width=width,
        file=io.StringIO(),
        color_system="truecolor",
        force_terminal=True,
        legacy_windows=False,
    )
    lines = console.render_lines(renderable, console.options.update(width=width), pad=False)
    return [[seg for seg in line if seg.text] for line in lines]


def segment_style(seg: Segment) -> tuple[str, int]:
    """Map rich styles onto the palette: (fill, font weight)."""
    style = seg.style
    if seg.text and set(seg.text) <= _BOX | {" "} and seg.text.strip():
        return QUIET, 400
    if style is None:
        return BODY, 400
    weight = 600 if style.bold else 400
    color = style.color.name if style.color is not None else None
    if color in ("green", "bright_green"):
        return TEAL, weight
    if color in ("yellow", "red", "magenta", "bright_red", "bright_yellow"):
        return AMBER, weight
    if style.dim:
        return QUIET, weight
    if style.bold:
        return MAIN, weight
    return BODY, weight


def term_line(canvas: Canvas, segments: list[Segment], x: float, y: float, cls: str = "") -> str:
    """One terminal line as <text> with a <tspan> per styled segment."""
    char = canvas.term.char
    parts = []
    col = 0
    for seg in segments:
        fill, weight = segment_style(seg)
        canvas.text_use(MONO, weight, seg.text)
        attrs = f'fill="{fill}"' + (f' font-weight="{weight}"' if weight != 400 else "")
        parts.append(f'<tspan x="{x + col * char:.1f}" {attrs}>{esc(seg.text)}</tspan>')
        col += len(seg.text)
    klass = f"m {cls}".strip()
    return f'<text class="{klass}" y="{y:.1f}" xml:space="preserve">{"".join(parts)}</text>'


def window(
    canvas: Canvas, x: float, y: float, w: float, h: float, title: str, title_size: int = 30
) -> None:
    """Terminal window chrome: panel, border, three dots, title."""
    canvas.body.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="22" fill="{PANEL}" '
        f'stroke="{BORDER}" stroke-width="3"/>'
    )
    for i, color in enumerate((QUIET, QUIET, QUIET)):
        canvas.body.append(
            f'<circle cx="{x + 40 + i * 34}" cy="{y + 38}" r="10" fill="{color}" opacity="0.6"/>'
        )
    canvas.text_use(SANS, 600, title)
    canvas.body.append(
        f'<text x="{x + w / 2}" y="{y + 49}" text-anchor="middle" font-size="{title_size}" '
        f'font-weight="600" fill="{QUIET}">{esc(title)}</text>'
    )
    canvas.body.append(
        f'<line x1="{x}" y1="{y + 76}" x2="{x + w}" y2="{y + 76}" stroke="{BORDER}" '
        f'stroke-width="3"/>'
    )


def icon(name: str, x: float, y: float, size: float, fill: str) -> str:
    """A Simple Icons glyph (24x24 path) placed at (x, y) and scaled to ``size``."""
    svg = (ICONS / f"{name}.svg").read_text(encoding="utf-8")
    start = svg.index(' d="') + 4
    path = svg[start : svg.index('"', start)]
    scale = size / 24
    return (
        f'<path transform="translate({x:.1f} {y:.1f}) scale({scale:.4f})" fill="{fill}" '
        f'd="{path}"/>'
    )

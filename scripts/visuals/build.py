#!/usr/bin/env python3
"""Build the README visuals from a committed live run.

Usage::

    uv run --group visual python scripts/visuals/build.py           # write the SVGs
    uv run --group visual python scripts/visuals/build.py --check   # fail if they are stale

Every line of terminal output in these images is produced by the real report
renderer (``scrapeplanner.output.terminal``) from a committed ``report.json``,
and every count comes from that run's reports. Nothing is typed by hand.
``scripts/visuals/media.py`` turns the SVGs into the PNG and MP4 files.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rich.segment import Segment
from svgkit import (
    AMBER,
    BODY,
    BORDER,
    MAIN,
    MONO,
    PANEL,
    QUIET,
    ROOT,
    SANS,
    TEAL,
    Canvas,
    Term,
    esc,
    icon,
    rich_lines,
    term_line,
    window,
)

from scrapeplanner.models import Report
from scrapeplanner.output.terminal import renderables

RUN = "008-sites"
HERO_SITE = "deathwish-coffee"
ASSETS = ROOT / "assets"
MEDIA = ROOT / "media"


def load_report(site: str, run: str = RUN) -> Report:
    path = ROOT / "checks" / "results" / run / site / "report.json"
    return Report.model_validate_json(path.read_text(encoding="utf-8"))


def results_rows(run: str = RUN) -> list[Report]:
    summary = json.loads((ROOT / "checks" / "results" / run / "summary.json").read_text("utf-8"))
    reports = []
    for row in summary["rows"]:
        path = ROOT / "checks" / "results" / run / row["name"] / "report.json"
        if path.exists():
            reports.append(Report.model_validate_json(path.read_text(encoding="utf-8")))
    return reports


def _plain(line: list[Segment]) -> str:
    return "".join(seg.text for seg in line)


# -- the terminal scene: command typed, summary panel, then the plan -----------------


def terminal_scene(
    report: Report,
    site: str,
    *,
    width: int,
    term: Term,
    visible: int,
    title_size: int,
    caption_size: int,
    height: int | None = None,
    caption: str | None = None,
) -> Canvas:
    """A terminal window that types the command, prints the summary panel and then the
    plan panel, scrolling like a real terminal. The last frame shows the plan."""
    sections = renderables(report, term.columns)
    command = f"scrapeplanner {report.input_url}"
    summary = rich_lines(sections["summary"], term.columns)
    plan = rich_lines(sections["plan"], term.columns)
    # A command longer than the terminal wraps onto the next row, as in a real terminal.
    cmd_rows = -(-(2 + len(command)) // term.columns)
    lines: list[list[Segment]] = [*([[]] * cmd_rows), [], *summary, [], *plan]
    date = report.started_at[:10]

    win_x, win_y = 20, 20
    win_w = width - 2 * win_x
    # Whole-pixel positions: text in an animated (composited) layer is snapped to the
    # pixel grid, static text is not, so fractional positions render differently.
    text_x = round(win_x + (win_w - term.columns * term.char) / 2)
    first = round(win_y + 76 + term.size * 1.55)
    view_h = visible * term.line
    win_h = 76 + term.size * 0.55 + view_h + term.size * 0.6
    total_h = height or int(win_y + win_h + caption_size * 2.6)
    canvas = Canvas(
        width=width,
        height=total_h,
        title=f"scrapeplanner run on {report.site}",
        desc=(
            f"Animated terminal. The command '{command}' is typed, then the real report "
            f"appears: the summary panel (verdict {report.plan.verdict}, best method "
            f"{report.plan.recommended}, platform {report.platform.name}), then the plan panel "
            f"with each collection method cheapest first. Recorded run {RUN}, {date}."
        ),
        duration=10.0,
        term=term,
    )
    window(canvas, win_x, win_y, win_w, win_h, "scrapeplanner · recorded run", title_size)

    # Timeline (seconds). Everything settles at least 2 s before the loop restarts.
    t_type, per_char = 0.4, 0.035
    t_typed = t_type + len(command) * per_char
    times = [0.0] * cmd_rows + [t_typed + 0.3]
    t = t_typed + 0.5
    for _ in summary:
        times.append(t)
        t += 0.12
    t += 0.45
    times.append(t)  # blank line before the plan
    for _ in plan:
        times.append(t)
        t += 0.09
    # Scrolling: once more lines are printed than fit, the content moves up, like a
    # terminal. When everything is printed the view scrolls back to the top of the
    # plan, and the recommended method is highlighted.
    max_shift = max(0, len(lines) - visible) * term.line
    plan_top = cmd_rows + 1 + len(summary) + 1
    final_shift = min(max_shift, plan_top * term.line)
    t_back = t + 0.3
    t_highlight = t_back + (0.7 if final_shift < max_shift else 0.0)
    assert t_highlight + 0.4 <= canvas.duration - 2.0, "animation must settle 2 s before the end"
    frames = []
    for i, at in enumerate(times):
        shift = max(0, i + 1 - visible) * term.line
        frames.append((at, f"transform:translateY(-{shift:.1f}px)"))
    if final_shift < max_shift:
        frames.append(
            (
                t_back,
                f"transform:translateY(-{max_shift:.1f}px);animation-timing-function:ease-in-out",
            )
        )
        frames.append((t_back + 0.6, f"transform:translateY(-{final_shift:.1f}px)"))
    else:
        frames.append((t_back, f"transform:translateY(-{final_shift:.1f}px)"))
    scroll = canvas.anim_class(frames, easing="step-end")
    canvas.statics.append(f".{scroll}{{transform:translateY(-{final_shift:.1f}px)}}")

    clip_top = win_y + 76 + 3
    clip_h = (first - clip_top) + (visible - 1) * term.line + term.size * 0.4
    canvas.body.append(
        f'<clipPath id="view"><rect x="{win_x}" y="{clip_top}" width="{win_w}" '
        f'height="{clip_h:.1f}"/></clipPath>'
    )
    canvas.body.append(f'<g clip-path="url(#view)"><g class="{scroll}">')

    # Line 0: the prompt and the typed command.
    canvas.text_use(MONO, 600, "$")
    canvas.text_use(MONO, 400, command)

    def cell(index: int) -> tuple[float, float]:
        """Offset (x, y) of character cell ``index`` of the prompt line, wrapping."""
        return (index % term.columns) * term.char, (index // term.columns) * term.line

    chars = []
    for i, ch in enumerate(command):
        cls = canvas.appear(t_type + i * per_char, fade=0.01)
        dx, dy = cell(2 + i)
        chars.append(
            f'<tspan class="{cls}" x="{text_x + dx:.1f}" y="{first + dy:.1f}">{esc(ch)}</tspan>'
        )
    canvas.body.append(
        f'<text class="m" y="{first:.1f}" xml:space="preserve"><tspan x="{text_x:.1f}" '
        f'fill="{TEAL}" font-weight="600">$</tspan><tspan fill="{MAIN}">{"".join(chars)}'
        "</tspan></text>"
    )

    def move(index: int) -> str:
        dx, dy = cell(index)
        dx0, _ = cell(2)
        return f"transform:translate({dx - dx0:.1f}px,{dy:.1f}px)"

    end = move(2 + len(command))
    cursor_frames = [(0.0, f"opacity:1;{move(2)}")]
    for i in range(len(command) + 1):
        cursor_frames.append((t_type + i * per_char, f"opacity:1;{move(2 + i)}"))
    cursor_frames.append((t_typed + 0.3, f"opacity:0;{end}"))
    cursor = canvas.anim_class(cursor_frames, easing="step-end")
    canvas.statics.append(f".{cursor}{{opacity:0;{end}}}")
    canvas.body.append(
        f'<rect class="{cursor}" x="{text_x + 2 * term.char:.1f}" '
        f'y="{first - term.size * 0.86:.1f}" width="{term.char * 0.9:.1f}" '
        f'height="{term.size * 1.12:.1f}" fill="{TEAL}"/>'
    )

    # The report, line by line; the recommended method is highlighted last.
    rec_index = next((i for i, line in enumerate(lines) if "recommended" in _plain(line)), None)
    for i, line in enumerate(lines[cmd_rows + 1 :], start=cmd_rows + 1):
        y = first + i * term.line
        if i == rec_index:
            hl = canvas.anim_class(
                [(0, "opacity:0"), (t_highlight, "opacity:0"), (t_highlight + 0.4, "opacity:1")]
            )
            canvas.body.append(
                f'<rect class="{hl}" x="{text_x - 8:.1f}" y="{y - term.size * 1.02:.1f}" '
                f'width="{term.columns * term.char + 16:.1f}" height="{term.line:.1f}" rx="8" '
                f'fill="{TEAL}" fill-opacity="0.16" stroke="{TEAL}" stroke-width="2"/>'
            )
        if line:
            cls = canvas.appear(times[i], fade=0.15)
            canvas.body.append(term_line(canvas, line, text_x, y, cls))
    canvas.body.append("</g></g>")

    cap = caption or f"Recorded run {RUN} · {site} · {date}"
    canvas.text_use(SANS, 400, cap)
    canvas.body.append(
        f'<text x="{width / 2}" y="{win_y + win_h + caption_size * 1.75:.1f}" '
        f'text-anchor="middle" font-size="{caption_size}" fill="{QUIET}">{esc(cap)}</text>'
    )
    return canvas


def hero(report: Report, site: str) -> Canvas:
    return terminal_scene(
        report, site, width=1000, term=Term(30, 50), visible=19, title_size=30, caption_size=30
    )


def video_scene(report: Report, site: str) -> Canvas:
    """1080 x 1080 with 40 px terminal text, for media/linkedin-demo.mp4."""
    return terminal_scene(
        report,
        site,
        width=1080,
        term=Term(40, 40),
        visible=15,
        title_size=40,
        caption_size=40,
        height=1080,
        caption=f"Recorded run {RUN} · {report.site}",
    )


# -- method ladder ------------------------------------------------------------------

RUNGS = [
    (
        "feed_api",
        "Feed / API",
        "products.json, job-board APIs, RSS",
        ["shopify", "woocommerce", "wordpress", "rss"],
    ),
    ("structured_data", "Structured data", "JSON-LD and microdata", ["json"]),
    ("embedded_json", "Embedded JSON", "__NEXT_DATA__, Nuxt state", ["nextdotjs", "nuxt"]),
    ("html", "HTML", "CSS selectors on the raw page", ["html5", "python"]),
    ("browser", "Browser", "headless, last resort", ["googlechrome"]),
]


def method_counts(reports: list[Report]) -> tuple[Counter[str], int]:
    counts: Counter[str] = Counter(r.plan.recommended for r in reports if r.plan.recommended)
    not_fit = sum(1 for r in reports if r.plan.verdict == "not_a_fit")
    return counts, not_fit


def ladder(reports: list[Report]) -> Canvas:
    counts, not_fit = method_counts(reports)
    total = len(reports)
    row_h, gap, top = 156, 26, 150
    height = top + len(RUNGS) * (row_h + gap) + 120
    canvas = Canvas(
        width=1000,
        height=height,
        title="How scrapeplanner decides: the method ladder",
        desc=(
            "Five methods from cheapest to most expensive: feed or API, structured data, "
            "embedded JSON, HTML, headless browser. The first one that works is recommended. "
            f"Counts are the recommended method per site in run {RUN}: "
            + ", ".join(f"{label} {counts.get(key, 0)}" for key, label, _, _ in RUNGS)
            + f"; {not_fit} of {total} sites were not a fit."
        ),
        duration=8.0,
    )
    heading = "Cheapest first. The first rung that works wins."
    canvas.text_use(SANS, 700, heading)
    canvas.body.append(
        f'<text x="40" y="84" font-size="40" font-weight="700" fill="{MAIN}">{esc(heading)}</text>'
    )
    for i, (key, label, sub, icons) in enumerate(RUNGS):
        y = top + i * (row_h + gap)
        t = 0.5 + i * 0.7
        lit = canvas.anim_class(
            [
                (0, f"stroke:{BORDER}"),
                (t, f"stroke:{BORDER}"),
                (t + 0.2, f"stroke:{TEAL}"),
                (t + 0.9, f"stroke:{TEAL}"),
                (t + 1.2, f"stroke:{BORDER}"),
            ]
        )
        canvas.body.append(
            f'<rect class="{lit}" x="40" y="{y}" width="920" height="{row_h}" rx="20" '
            f'fill="{PANEL}" stroke="{BORDER}" stroke-width="4"/>'
        )
        canvas.text_use(MONO, 600, str(i + 1))
        canvas.body.append(
            f'<circle cx="104" cy="{y + row_h / 2}" r="34" fill="none" stroke="{TEAL}" '
            f'stroke-width="4"/><text class="m" x="104" y="{y + row_h / 2 + 11}" '
            f'text-anchor="middle" font-weight="600" fill="{TEAL}">{i + 1}</text>'
        )
        canvas.text_use(SANS, 700, label)
        canvas.text_use(SANS, 400, sub)
        canvas.body.append(
            f'<text x="168" y="{y + 66}" font-size="40" font-weight="700" fill="{MAIN}">'
            f"{esc(label)}</text>"
            f'<text x="168" y="{y + 114}" font-size="30" fill="{BODY}">{esc(sub)}</text>'
        )
        for j, name in enumerate(icons):
            canvas.body.append(icon(name, 900 - (len(icons) - j) * 62, y + 26, 48, BODY))
        n = counts.get(key, 0)
        stat = f"best on {n} of {total}"
        canvas.text_use(SANS, 600, stat)
        stat_cls = canvas.appear(4.4 + i * 0.25)
        canvas.body.append(
            f'<text class="{stat_cls}" x="932" y="{y + 126}" text-anchor="end" font-size="30" '
            f'font-weight="600" fill="{TEAL if n else QUIET}">{esc(stat)}</text>'
        )
        if i < len(RUNGS) - 1:
            canvas.body.append(
                f'<path d="M104 {y + row_h + 2} v{gap - 4}" stroke="{QUIET}" stroke-width="4"/>'
            )
    foot = f"{not_fit} of {total} not a fit: blocked, challenged or disallowed"
    canvas.text_use(SANS, 600, foot)
    foot_y = top + len(RUNGS) * (row_h + gap) + 24
    canvas.body.append(
        f'<text x="40" y="{foot_y}" font-size="30" font-weight="600" fill="{AMBER}">'
        f"{esc(foot)}</text>"
    )
    source = f"Counts: best method per site, run {RUN}"
    canvas.text_use(SANS, 400, source)
    canvas.body.append(
        f'<text x="40" y="{foot_y + 52}" font-size="30" fill="{QUIET}">{esc(source)}</text>'
    )
    return canvas


# -- social preview (rendered to PNG by media.py) -----------------------------------


def social(report: Report, reports: list[Report]) -> Canvas:
    total = len(reports)
    good = sum(1 for r in reports if r.plan.verdict == "good")
    requests = sum(r.requests_used for r in reports)
    canvas = Canvas(
        width=1280,
        height=640,
        title="scrapeplanner",
        desc="scrapeplanner social preview",
        duration=1.0,
        term=Term(20, 40),
    )
    canvas.body.append(
        f'<rect x="24" y="24" width="1232" height="592" rx="28" fill="none" '
        f'stroke="{BORDER}" stroke-width="3"/>'
    )
    title = "scrapeplanner"
    line1 = "Point it at a URL. It tells you the"
    line2 = "cheapest polite way to get the data."
    canvas.text_use(SANS, 700, title)
    canvas.text_use(SANS, 400, line1 + line2)
    canvas.body.append(
        f'<text x="72" y="166" font-size="76" font-weight="700" fill="{MAIN}">{title}</text>'
        f'<text x="72" y="236" font-size="30" fill="{BODY}">{esc(line1)}</text>'
        f'<text x="72" y="278" font-size="30" fill="{BODY}">{esc(line2)}</text>'
    )
    stats = [
        (str(total), "public sites"),
        (str(good), "good fit"),
        (str(requests), "requests in total"),
    ]
    for i, (num, label) in enumerate(stats):
        x = 72 + i * 170
        canvas.text_use(SANS, 700, num)
        canvas.text_use(SANS, 400, label)
        canvas.body.append(
            f'<text x="{x}" y="420" font-size="64" font-weight="700" fill="{TEAL}">{num}</text>'
            f'<text x="{x}" y="458" font-size="22" fill="{QUIET}">{esc(label)}</text>'
        )
    foot1 = "robots.txt first · about 10 requests"
    foot2 = "detection only, never evasion"
    canvas.text_use(SANS, 600, foot1 + foot2)
    canvas.body.append(
        f'<text x="72" y="532" font-size="24" font-weight="600" fill="{AMBER}">{esc(foot1)}</text>'
        f'<text x="72" y="566" font-size="24" font-weight="600" fill="{AMBER}">{esc(foot2)}</text>'
    )
    panel = rich_lines(renderables(report, 40)["summary"], 40)
    px, py = 700, 210
    canvas.body.append(
        f'<rect x="{px - 26}" y="{py - 58}" width="{40 * canvas.term.char + 52:.0f}" '
        f'height="{len(panel) * canvas.term.line + 64:.0f}" rx="18" fill="{PANEL}" '
        f'stroke="{BORDER}" stroke-width="3"/>'
    )
    for i, line in enumerate(panel):
        canvas.body.append(term_line(canvas, line, px, py + i * canvas.term.line))
    return canvas


# -- main ---------------------------------------------------------------------------


def build() -> dict[Path, str]:
    report = load_report(HERO_SITE)
    reports = results_rows()
    out: dict[Path, str] = {}
    for name, canvas in (("hero", hero(report, HERO_SITE)), ("ladder", ladder(reports))):
        out[ASSETS / f"{name}.svg"] = canvas.render(animated=True)
        out[ASSETS / f"{name}-still.svg"] = canvas.render(animated=False)
    out[ASSETS / "src" / "linkedin-demo.svg"] = video_scene(report, HERO_SITE).render(animated=True)
    out[ASSETS / "src" / "social-preview.svg"] = social(report, reports).render(animated=False)
    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the SVGs are stale")
    args = parser.parse_args(argv)
    stale = []
    for path, text in build().items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(str(path.relative_to(ROOT)))
            continue
        path.write_text(text, encoding="utf-8")
        print(f"{path.relative_to(ROOT)}  {len(text.encode('utf-8')) / 1024:.0f} KB")
    if stale:
        print("stale: " + ", ".join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

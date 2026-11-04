"""The default terminal report (rich)."""

from __future__ import annotations

from rich import box
from rich.console import Console, Group, RenderableType
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from scrapeplanner.models import METHOD_LABELS, METHOD_SHORT, Report, vendor_label
from scrapeplanner.planner import describe

VERDICT_STYLE = {
    "good": ("GOOD FIT", "bold green"),
    "caution": ("POSSIBLE, WITH CARE", "bold yellow"),
    "not_a_fit": ("NOT A FIT", "bold red"),
    "unknown": ("UNKNOWN", "bold magenta"),
}
RENDER_LABELS = {
    "raw_html": "data in the raw HTML",
    "embedded_json": "data in embedded JSON",
    "browser_likely": "needs a browser",
    "unknown": "not analysed",
}


def _kv(rows: list[tuple[str, RenderableType | str]]) -> Table:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim", no_wrap=True, max_width=28, overflow="ellipsis")
    table.add_column(overflow="fold", min_width=12)
    for key, value in rows:
        table.add_row(key, value)
    return table


def _yes(value: bool) -> Text:
    return Text("allowed", style="green") if value else Text("disallowed", style="red")


def _fmt_hours(hours: float | None) -> str:
    if hours is None:
        return "-"
    minutes = hours * 60
    if minutes < 1:
        return "< 1 min"
    if minutes < 90:
        return f"{minutes:.0f} min"
    return f"{hours:.1f} h"


def _summary(report: Report) -> Table:
    plan = report.plan
    label, style = VERDICT_STYLE[plan.verdict]
    antibot = ", ".join(
        vendor_label(hit.vendor, hit.status, hit.bot_management) for hit in report.antibot.vendors
    )
    rows: list[tuple[str, RenderableType | str]] = [
        ("Verdict", Text(label, style=style)),
        ("Best method", METHOD_LABELS[plan.recommended] if plan.recommended else "none"),
        ("Platform", describe(report.platform)),
        ("Anti-bot", antibot or "none seen"),
        ("Rendering", RENDER_LABELS[report.rendering.verdict]),
        (
            "Polite rate",
            f"1 request every {plan.rate.delay_seconds:g}s"
            + (
                f", max {plan.rate.max_requests_per_day:,}/day"
                if plan.rate.max_requests_per_day
                else ""
            ),
        ),
        (
            "This run",
            f"{report.requests_used}/{report.max_requests} requests, "
            f"{report.duration_seconds:.1f}s",
        ),
    ]
    if report.stopped:
        rows.append(("Stopped", Text(f"{report.stopped.detail}", style="red")))
    return _kv(rows)


def _methods(report: Report) -> Table:
    plan = report.plan
    table = Table(box=box.SIMPLE_HEAD, expand=True, pad_edge=False)
    table.add_column("#", justify="right", width=2)
    table.add_column("Method", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column(f"Req. for {plan.items:,}", justify="right", no_wrap=True)
    table.add_column("Time", justify="right", no_wrap=True)
    table.add_column("Details", overflow="fold", ratio=1)
    for index, method in enumerate(plan.methods, 1):
        if method.name == plan.recommended:
            status = Text("recommended", style="bold green")
        elif method.usable:
            status = Text("usable", style="green")
        else:
            status = Text("no", style="dim")
        details = method.summary
        if method.notes:
            details += "\n" + "\n".join(f"- {note}" for note in method.notes)
        table.add_row(
            str(index),
            METHOD_SHORT[method.name],
            status,
            f"{method.est_requests:,}" if method.est_requests is not None else "-",
            _fmt_hours(method.est_hours),
            details,
        )
    return table


def _methods_compact(report: Report) -> Group:
    """The plan as a list, for terminals narrower than ``NARROW`` columns."""
    plan = report.plan
    lines: list[RenderableType] = []
    for index, method in enumerate(plan.methods, 1):
        if method.name == plan.recommended:
            status = Text("recommended", style="bold green")
        elif method.usable:
            status = Text("usable", style="green")
        else:
            status = Text("no", style="dim")
        head = Text.assemble(
            (f"{index} ", "dim"), (METHOD_SHORT[method.name], "bold"), "  ", status
        )
        lines.append(head)
        if method.est_requests is not None:
            lines.append(
                _indent(
                    f"{method.est_requests:,} requests for {plan.items:,} · "
                    f"{_fmt_hours(method.est_hours)}"
                )
            )
        lines.append(_indent(method.summary, "" if method.usable else "dim"))
        for note in method.notes:
            lines.append(_indent(f"- {note}", "dim"))
    return Group(*lines)


def _indent(text: str, style: str = "", left: int = 2) -> Padding:
    return Padding(Text(text, style=style, overflow="fold"), (0, 0, 0, left))


def _robots(report: Report) -> Table:
    robots = report.robots
    if not robots.fetched:
        status = "not fetched"
    elif robots.found:
        status = f"found (HTTP {robots.status})"
    else:
        status = robots.note or f"HTTP {robots.status}"
    rows: list[tuple[str, RenderableType | str]] = [("robots.txt", status)]
    if robots.crawl_delay is not None:
        rows.append(("crawl-delay", f"{robots.crawl_delay:g}s"))
    if robots.request_rate:
        rows.append(("request-rate", robots.request_rate))
    for path, allowed in list(robots.paths.items())[:8]:
        rows.append((f"  {path[:60]}", _yes(allowed)))
    sitemap = report.sitemap
    if sitemap.url:
        if sitemap.kind == "urlset":
            what = f"{sitemap.url_count:,} URLs" + (" (truncated)" if sitemap.truncated else "")
        elif sitemap.kind == "sitemapindex":
            what = f"index of {sitemap.child_sitemaps:,} sitemaps"
        else:
            what = sitemap.note or (f"HTTP {sitemap.status}" if sitemap.status else "not read")
        if sitemap.newest_lastmod:
            what += f", newest lastmod {sitemap.newest_lastmod}"
        rows.append(("Sitemap", f"{what}\n{sitemap.url}"))
        child = sitemap.child
        if child is not None:
            if child.url_count is not None:
                child_text = f"{child.url_count:,} URLs"
                if child.newest_lastmod:
                    child_text += f", newest lastmod {child.newest_lastmod}"
            else:
                child_text = child.note or "not read"
            rows.append(("  child", f"{child_text}\n{child.url}"))
    return _kv(rows)


def _data(report: Report) -> Table:
    rows: list[tuple[str, RenderableType | str]] = []
    s = report.structured
    if s.items:
        for item in s.items[:6]:
            fields = ", ".join(item.fields[:8]) or "-"
            rows.append((f"{item.type} x{item.count}", f"{item.source}: {fields}"))
    elif s.types:
        rows.append(("Structured", "no record types (" + ", ".join(sorted(s.types)[:6]) + ")"))
    else:
        rows.append(("Structured", "none"))
    for blob in report.embedded.blobs[:4]:
        keys = ", ".join(blob.keys[:6])
        rows.append((blob.locator, f"{blob.bytes:,} bytes" + (f": {keys}" if keys else "")))
    for candidate in report.feeds.candidates[:6]:
        status = candidate.status.replace("_", " ")
        if candidate.items_seen is not None:
            noun = "item" if candidate.items_seen == 1 else "items"
            status += f", {candidate.items_seen} {noun}"
        if candidate.total_items is not None:
            status += f" of {candidate.total_items:,}"
        style = "green" if candidate.status == "ok" else "dim"
        rows.append((candidate.kind, Text(f"{status}\n{candidate.url}", style=style)))
    if report.rendering.reasons:
        rows.append(("Rendering", "; ".join(report.rendering.reasons[:3])))
    return _kv(rows)


def _list(items: list[str], style: str) -> RenderableType:
    if not items:
        return Text("none", style="dim")
    return Group(*(_hanging(f"- {item}", style) for item in items))


def _hanging(text: str, style: str) -> Text:
    """A list item whose wrapped lines start under the first word."""
    return Text(text, style=style, overflow="fold")


NARROW = 80
"""Below this many columns the report switches to a stacked layout."""


def render(report: Report, console: Console) -> None:
    narrow = console.width < NARROW
    if narrow:
        title = f"[bold]scrapeplanner[/] · {report.site}"
    else:
        title = f"[bold]scrapeplanner[/] {report.tool.version}  ·  {report.input_url}"
    console.print(Panel(_summary(report), title=title, title_align="left", box=box.ROUNDED))
    plan_view: RenderableType = _methods_compact(report) if narrow else _methods(report)
    console.print(
        Panel(plan_view, title="Plan (cheapest first)", title_align="left", box=box.ROUNDED)
    )
    console.print(Panel(_robots(report), title="Rules", title_align="left", box=box.ROUNDED))
    console.print(Panel(_data(report), title="Data found", title_align="left", box=box.ROUNDED))
    console.print(
        Panel(
            Group(
                Text("Risks", style="bold"),
                _list(report.plan.risks, "yellow"),
                Text(""),
                Text("Next steps", style="bold"),
                _list(report.plan.next_steps, ""),
            ),
            box=box.ROUNDED,
        )
    )
    if narrow:
        console.print(Text("Requests", style="bold"))
        for index, entry in enumerate(report.requests, 1):
            status = str(entry.status) if entry.status is not None else "error"
            console.print(
                Text.assemble(
                    (f"{index:>2} ", "dim"), (f"{status} ", ""), (f"{entry.purpose}", "dim")
                )
            )
            console.print(_indent(entry.url, "dim", left=3))
        return
    log = Table(box=box.SIMPLE, pad_edge=False, show_header=True, header_style="dim")
    log.add_column("#", justify="right", style="dim")
    log.add_column("Status", justify="right")
    log.add_column("Purpose", no_wrap=True)
    log.add_column("ms", justify="right", style="dim")
    log.add_column("URL", overflow="fold")
    for index, entry in enumerate(report.requests, 1):
        log.add_row(
            str(index),
            str(entry.status) if entry.status is not None else (entry.error or "error")[:20],
            entry.purpose,
            str(entry.elapsed_ms),
            entry.url,
        )
    console.print(log)

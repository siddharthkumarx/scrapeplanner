#!/usr/bin/env python3
"""Write docs/results.md from one committed live run (checks/results/<id>/).

Usage::

    uv run python scripts/make_results.py <check-id>

Every number in the output is read from that run's report.json files; nothing
is typed by hand. The README may only quote numbers that appear here.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scrapeplanner.models import (  # noqa: E402
    METHOD_SHORT,
    NOT_CHECKED,
    PLATFORM_LABELS,
    VENDOR_LABELS,
    Report,
    platform_label,
    vendor_label,
)

VERDICT_LABELS = {
    "good": "good fit",
    "caution": "with care",
    "not_a_fit": "not a fit",
    "unknown": "unknown",
}


def platform_cell(report: Report) -> str:
    if not report.platform.checked and report.platform.name == "unknown":
        return NOT_CHECKED
    return PLATFORM_LABELS[report.platform.name]


def _why(report: Report) -> str:
    """Short reason for the verdict, from the report itself."""
    if report.stopped is not None and report.plan.verdict == "not_a_fit":
        return report.stopped.detail
    robots = report.robots
    if robots.disallow_all:
        return "robots.txt unreadable: treated as disallow-all"
    if not report.page.fetched and robots.paths and not all(robots.paths.values()):
        return "page disallowed by robots.txt"
    method = next((m for m in report.plan.methods if m.name == report.plan.recommended), None)
    why = method.summary if method else "-"
    if report.stopped is not None:
        why += f"; run stopped at {report.stopped.detail} on {report.stopped.url}"
    return why


def _row(name: str, category: str, report: Report) -> dict[str, Any]:
    plan = report.plan
    return {
        "name": name,
        "category": category,
        "url": report.input_url,
        "platform": platform_cell(report),
        "frameworks": [platform_label(n) for n in report.platform.frameworks],
        "method": METHOD_SHORT[plan.recommended] if plan.recommended else "-",
        "antibot": [
            vendor_label(hit.vendor, hit.status, hit.bot_management)
            for hit in report.antibot.vendors
        ],
        "vendors": list(report.antibot.vendors),
        "verdict": plan.verdict,
        "requests": report.requests_used,
        "seconds": report.duration_seconds,
        "why": _why(report),
    }


def platform_accuracy(rows: list[dict[str, Any]]) -> list[str]:
    """Coverage, and agreement with the labels written in request.yml before the run."""
    checked = [row for row in rows if row["checked"]]
    named = [row for row in checked if row["platform_key"] != "unknown"]
    labelled = [row for row in rows if row["expected"]]
    labelled_checked = [row for row in labelled if row["checked"]]
    matched = [row for row in labelled_checked if row["platform_key"] == row["expected"]]
    missed = [row for row in labelled_checked if row["platform_key"] != row["expected"]]
    lines = [
        f"- A platform was named on {len(named)} of the {len(checked)} sites that served a "
        f"page; {len(rows) - len(checked)} sites served no page to look at (blocked, "
        "challenged or disallowed).",
        f"- {len(labelled)} sites carry an expected platform written in `checks/request.yml` "
        "before the run (from the URL, the software a portal publicly runs on, or public "
        f"knowledge). Of the {len(labelled_checked)} of them that served a page, "
        f"{len(matched)} matched.",
    ]
    if missed:
        lines.append(
            "- Mismatches: "
            + ", ".join(
                f"{row['name']} (expected {platform_label(row['expected'])}, "
                f"found {row['platform']})"
                for row in missed
            )
        )
    return lines


def build(check_id: str) -> str:
    run_dir = ROOT / "checks" / "results" / check_id
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    meta = summary["meta"]
    rows: list[dict[str, Any]] = []
    failed: list[str] = []
    for entry in summary["rows"]:
        report_path = run_dir / entry["name"] / "report.json"
        if not report_path.exists():
            failed.append(entry["name"])
            continue
        report = Report.model_validate_json(report_path.read_text(encoding="utf-8"))
        row = _row(entry["name"], entry.get("category", ""), report)
        row["expected"] = entry.get("expected_platform")
        row["platform_key"] = report.platform.name
        row["checked"] = report.platform.checked
        rows.append(row)

    total = len(rows)
    verdicts = Counter(row["verdict"] for row in rows)
    platforms = Counter(row["platform"] for row in rows)
    methods = Counter(row["method"] for row in rows if row["method"] != "-")
    vendor_names: Counter[str] = Counter()
    challenged: Counter[str] = Counter()
    for row in rows:
        for hit in row["vendors"]:
            vendor_names[VENDOR_LABELS[hit.vendor]] += 1
            if hit.status == "challenge":
                challenged[VENDOR_LABELS[hit.vendor]] += 1
    requests = [row["requests"] for row in rows]
    seconds = sorted(row["seconds"] for row in rows)
    median = seconds[len(seconds) // 2] if seconds else 0.0
    max_requests = max(requests) if requests else 0
    accuracy = platform_accuracy(rows)

    lines = [
        "# Results",
        "",
        f"Generated by `scripts/make_results.py {check_id}` from the committed run",
        f"[`checks/results/{check_id}/`](../checks/results/{check_id}/). Do not edit by hand.",
        "",
        f"- scrapeplanner {meta['version']}, commit `{meta['commit'][:12]}`",
        f"- GitHub Actions runner ({meta['runner']}), Python {meta['python']}",
        f"- run started {meta['started_at']}, finished {meta['finished_at']} (UTC)",
        f"- options: {', '.join(f'{k}={v}' for k, v in sorted(meta['options'].items()))}",
        "- one homepage or public listing page per site; the tool read robots.txt first",
        "  and stopped at the first block or challenge",
        "",
        "Requests counts every HTTP request the tool sent for that site, robots.txt",
        "and redirect hops included. Time is the tool's own wall time, including",
        "the polite delay between requests (and robots.txt crawl-delay where set).",
        "",
        "## Summary",
        "",
        f"- Sites analysed: {total}"
        + (f" ({len(failed)} failed: {', '.join(failed)})" if failed else ""),
        "- Verdicts: "
        + ", ".join(f"{VERDICT_LABELS[k]} {verdicts[k]}" for k in VERDICT_LABELS if verdicts[k]),
        "- Platforms: " + ", ".join(f"{name} {count}" for name, count in platforms.most_common()),
        "- Recommended method: "
        + ", ".join(f"{name} {count}" for name, count in methods.most_common()),
        "- Anti-bot vendor seen: "
        + (", ".join(f"{name} {count}" for name, count in vendor_names.most_common()) or "none")
        + "; challenge page served: "
        + (", ".join(f"{name} {count}" for name, count in challenged.most_common()) or "none"),
        f"- Requests per site: {min(requests) if requests else 0} to {max_requests}, "
        f"{sum(requests)} in total; median time {median:.1f} s",
        "",
        "## Platform detection",
        "",
        *accuracy,
        "",
        "## Per site",
        "",
        "| Site | Category | Platform | Expected | Method found | Anti-bot vendor | Verdict | "
        "Requests | Time (s) | Why |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        platform = row["platform"]
        if row["frameworks"]:
            platform += " (" + ", ".join(row["frameworks"]) + ")"
        why = str(row["why"]).replace("|", "/")
        lines.append(
            f"| [{row['name']}]({row['url']}) | {row['category']} | {platform} "
            f"| {platform_label(row['expected']) if row['expected'] else '-'} | {row['method']} "
            f"| {', '.join(row['antibot']) or 'none'} | {VERDICT_LABELS[row['verdict']]} "
            f"| {row['requests']} | {row['seconds']:.1f} | {why} |"
        )
    notes_path = ROOT / "scripts" / "results_notes.yml"
    notes = yaml.safe_load(notes_path.read_text(encoding="utf-8")) or {}
    names = {row["name"] for row in rows}
    footnotes = [f"- **{name}**: {text}" for name, text in notes.items() if name in names]
    if footnotes:
        lines += ["", "### Notes", "", *footnotes]
    lines += [
        "",
        "Per-site details: `checks/results/" + check_id + "/<site>/report.txt` (terminal report)",
        "and `report.json` (full JSON). Labels: *CDN only* means only CDN headers were",
        "seen, not bot management; *challenge* means the vendor served a block or",
        "interstitial page and the run stopped there.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    out = ROOT / "docs" / "results.md"
    out.write_text(build(argv[0]), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

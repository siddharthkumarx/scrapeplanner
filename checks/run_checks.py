"""Run the live checks described in checks/request.yml (GitHub Actions only).

For each target this runs the real CLI::

    scrapeplanner URL --json --record <dir>/exchanges [options]

and writes ``checks/results/<id>/``:

* ``<target>/report.json``  the CLI's JSON output
* ``<target>/report.txt``   the terminal report rendered from that JSON
* ``<target>/exchanges/``   every HTTP exchange (input for the golden tests)
* ``<target>/run.json``     exit code, wall time, stderr tail
* ``summary.json`` / ``summary.md``  one row per target

A request id that already has results is skipped, so re-pushing the same
request never repeats traffic.
"""

from __future__ import annotations

import io
import json
import os
import platform
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console

from scrapeplanner import __version__
from scrapeplanner.models import (
    METHOD_SHORT,
    NOT_CHECKED,
    PLATFORM_LABELS,
    Report,
    platform_label,
    vendor_label,
)
from scrapeplanner.output.terminal import render

ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "checks" / "request.yml"
RESULTS = ROOT / "checks" / "results"
SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
TARGET_TIMEOUT = 240
ALLOWED_OPTIONS = {"max_requests", "delay", "items"}


def platform_cell(report: Report) -> str:
    if not report.platform.checked and report.platform.name == "unknown":
        return NOT_CHECKED
    return PLATFORM_LABELS[report.platform.name]


def load_request(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("request.yml: expected a mapping")
    if not SLUG.match(str(data.get("id", ""))):
        raise SystemExit("request.yml: 'id' must be a slug")
    options = data.get("options") or {}
    unknown = set(options) - ALLOWED_OPTIONS
    if unknown:
        raise SystemExit(f"request.yml: unknown options {sorted(unknown)}")
    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise SystemExit("request.yml: 'targets' must be a non-empty list")
    names = set()
    for target in targets:
        if not SLUG.match(str(target.get("name", ""))) or not target.get("url"):
            raise SystemExit(f"request.yml: bad target {target!r}")
        if target["name"] in names:
            raise SystemExit(f"request.yml: duplicate target {target['name']}")
        names.add(target["name"])
    return data


def render_text(report: Report) -> str:
    buffer = io.StringIO()
    console = Console(file=buffer, width=100, force_terminal=False, color_system=None)
    render(report, console)
    return buffer.getvalue()


def cli_args(url: str, options: dict[str, Any], exchanges: Path) -> list[str]:
    args = [sys.executable, "-m", "scrapeplanner", url, "--json", "--record", str(exchanges)]
    if "max_requests" in options:
        args += ["--max-requests", str(int(options["max_requests"]))]
    if "delay" in options:
        args += ["--delay", str(float(options["delay"]))]
    if "items" in options:
        args += ["--items", str(int(options["items"]))]
    return args


def summary_row(
    target: dict[str, Any], run: dict[str, Any], report: Report | None
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "name": target["name"],
        "category": target.get("category", ""),
        "url": target["url"],
        "exit_code": run["exit_code"],
        "wall_seconds": run["wall_seconds"],
    }
    if report is None:
        row["error"] = run.get("stderr_tail", "")[-300:]
        return row
    vendors = [
        vendor_label(hit.vendor, hit.status, hit.bot_management) for hit in report.antibot.vendors
    ]
    row.update(
        {
            "verdict": report.plan.verdict,
            "platform": platform_cell(report),
            "frameworks": [platform_label(n) for n in report.platform.frameworks],
            "method": METHOD_SHORT[report.plan.recommended] if report.plan.recommended else None,
            "antibot": vendors,
            "rendering": report.rendering.verdict,
            "page_status": report.page.status,
            "requests_used": report.requests_used,
            "duration_seconds": report.duration_seconds,
            "stopped": report.stopped.detail if report.stopped else None,
        }
    )
    return row


def write_markdown(path: Path, meta: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    lines = [
        f"# Check {meta['id']}",
        "",
        f"- scrapeplanner {meta['version']} at commit `{meta['commit'][:12]}`",
        f"- runner: {meta['runner']}, Python {meta['python']}",
        f"- started {meta['started_at']}, finished {meta['finished_at']}",
        "",
        "| Target | Category | Verdict | Platform | Method | Anti-bot | Requests | Time (s) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        if "error" in row:
            lines.append(f"| {row['name']} | {row['category']} | error | | | | | |")
            continue
        lines.append(
            "| {name} | {category} | {verdict} | {platform} | {method} | {antibot} | "
            "{requests_used} | {duration_seconds} |".format(
                **{
                    **row,
                    "method": row["method"] or "-",
                    "antibot": ", ".join(row["antibot"]) or "none",
                }
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    request = load_request(REQUEST)
    out = RESULTS / request["id"]
    if (out / "summary.json").exists():
        print(f"results for {request['id']} already exist; nothing to do")
        return 0
    out.mkdir(parents=True, exist_ok=True)
    options = request.get("options") or {}
    started = datetime.now(UTC)
    rows = []
    for target in request["targets"]:
        target_dir = out / target["name"]
        target_dir.mkdir(parents=True, exist_ok=True)
        exchanges = target_dir / "exchanges"
        t0 = time.monotonic()
        try:
            proc = subprocess.run(
                cli_args(str(target["url"]), options, exchanges),
                capture_output=True,
                text=True,
                timeout=TARGET_TIMEOUT,
                check=False,
                env={**os.environ, "COLUMNS": "100"},
            )
            exit_code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as exc:
            exit_code, stdout, stderr = -1, "", f"timeout after {exc.timeout}s"
        run = {
            "exit_code": exit_code,
            "wall_seconds": round(time.monotonic() - t0, 2),
            "stderr_tail": stderr[-2000:],
        }
        (target_dir / "run.json").write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
        report = None
        if exit_code == 0 and stdout.strip():
            (target_dir / "report.json").write_text(stdout, encoding="utf-8")
            report = Report.model_validate_json(stdout)
            (target_dir / "report.txt").write_text(render_text(report), encoding="utf-8")
        row = summary_row(target, run, report)
        rows.append(row)
        print(json.dumps(row))
    meta = {
        "id": request["id"],
        "version": __version__,
        "commit": os.environ.get("GITHUB_SHA", "local"),
        "runner": f"{platform.system()} {platform.release()} ({os.environ.get('RUNNER_OS', '?')})",
        "python": platform.python_version(),
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "options": options,
    }
    (out / "summary.json").write_text(
        json.dumps({"meta": meta, "rows": rows}, indent=2) + "\n", encoding="utf-8"
    )
    write_markdown(out / "summary.md", meta, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())

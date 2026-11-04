#!/usr/bin/env python3
"""Copy a recorded target from checks/results into tests/fixtures.

Usage::

    uv run python scripts/import_fixture.py <check-id> <target> [<target> ...]

The recording is copied byte for byte. ``meta.json`` notes where it came from,
so every fixture can be traced to a committed live run.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def import_target(check_id: str, target: str) -> Path:
    source = ROOT / "checks" / "results" / check_id / target
    report = json.loads((source / "report.json").read_text(encoding="utf-8"))
    summary = json.loads(
        (ROOT / "checks" / "results" / check_id / "summary.json").read_text(encoding="utf-8")
    )
    options = summary["meta"].get("options", {})
    dest = ROOT / "tests" / "fixtures" / target
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source / "exchanges", dest / "exchanges")
    meta = {
        "url": report["input_url"],
        "recorded_at": report["started_at"],
        "source": f"checks/results/{check_id}/{target}",
        "commit": summary["meta"].get("commit"),
        "options": {
            key: options[key] for key in ("max_requests", "delay", "items") if key in options
        },
    }
    (dest / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return dest


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    for target in argv[1:]:
        print(import_target(argv[0], target))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

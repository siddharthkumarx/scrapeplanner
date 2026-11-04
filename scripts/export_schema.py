#!/usr/bin/env python3
"""Write docs/report.schema.json, the JSON Schema of ``scrapeplanner --json``."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from scrapeplanner.models import SCHEMA_VERSION, Report

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "report.schema.json"


def schema_text() -> str:
    schema = Report.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = (
        "https://github.com/siddharthkumarx/scrapeplanner/blob/main/docs/report.schema.json"
    )
    schema["description"] = (
        f"Output of `scrapeplanner URL --json`, schema_version {SCHEMA_VERSION}."
    )
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def main() -> int:
    OUT.write_text(schema_text(), encoding="utf-8")
    print(OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())

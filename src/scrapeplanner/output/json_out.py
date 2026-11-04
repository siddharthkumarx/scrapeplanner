"""``--json``: the full report as JSON (schema in models.Report)."""

from __future__ import annotations

from scrapeplanner.models import Report


def to_json(report: Report) -> str:
    return report.model_dump_json(indent=2) + "\n"

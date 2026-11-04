"""Replay a recorded fixture through the real analyzer, offline and deterministic."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from scrapeplanner.analyze import Options, analyze
from scrapeplanner.record import ReplayTransport

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"
EXPECTED = ROOT / "tests" / "golden" / "expected"
SECTIONS = (
    "page",
    "robots",
    "sitemap",
    "platform",
    "antibot",
    "structured",
    "embedded",
    "rendering",
    "feeds",
    "plan",
    "requests",
    "skipped",
    "stopped",
)
"""One golden comparison per detector section of the report."""


def fixture_names() -> list[str]:
    return sorted(p.parent.name for p in FIXTURES.glob("*/meta.json"))


def load_meta(name: str) -> dict[str, Any]:
    data = json.loads((FIXTURES / name / "meta.json").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def replay(name: str) -> tuple[dict[str, Any], list[str]]:
    """Return (normalised report dict, URLs the analyzer asked for that were not recorded)."""
    meta = load_meta(name)
    transport = ReplayTransport(FIXTURES / name / "exchanges")
    options = Options(**meta.get("options", {}))
    report = analyze(
        meta["url"],
        options,
        transport=transport,
        sleep=lambda _: None,
        now=datetime.fromisoformat(meta["recorded_at"]),
    )
    data = report.model_dump(mode="json")
    data.pop("duration_seconds")
    data.pop("tool")
    for entry in data["requests"]:
        entry.pop("elapsed_ms")
    return data, transport.misses

"""docs/report.schema.json must match the models (regenerate with scripts/export_schema.py)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_schema_file_is_current() -> None:
    spec = importlib.util.spec_from_file_location(
        "export_schema", ROOT / "scripts" / "export_schema.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    current = (ROOT / "docs" / "report.schema.json").read_text(encoding="utf-8")
    assert current == module.schema_text(), "run: uv run python scripts/export_schema.py"

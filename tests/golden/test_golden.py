"""Golden tests: every detector on real saved pages (tests/fixtures/).

Fixtures were recorded by the checks workflow (checks/results/<id>/<target>/exchanges)
and imported with scripts/import_fixture.py. After an intended change, run
``uv run python scripts/update_golden.py`` and review the diff.
"""

from __future__ import annotations

import json
from functools import cache
from typing import Any

import pytest

from tests.golden.replay import EXPECTED, SECTIONS, fixture_names, replay

NAMES = fixture_names()


@cache
def _actual(name: str) -> tuple[dict[str, Any], tuple[str, ...]]:
    data, misses = replay(name)
    return data, tuple(misses)


def _expected(name: str) -> dict[str, Any]:
    data = json.loads((EXPECTED / f"{name}.json").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_fixtures_present() -> None:
    assert NAMES, "no fixtures in tests/fixtures"
    for name in NAMES:
        assert (EXPECTED / f"{name}.json").exists(), f"missing golden file for {name}"


@pytest.mark.parametrize("name", NAMES)
def test_replay_is_complete(name: str) -> None:
    """The analyzer asks for exactly what was recorded: no new live URLs."""
    _, misses = _actual(name)
    assert misses == ()


@pytest.mark.parametrize("section", SECTIONS)
@pytest.mark.parametrize("name", NAMES)
def test_section(name: str, section: str) -> None:
    actual, _ = _actual(name)
    assert actual[section] == _expected(name)[section]

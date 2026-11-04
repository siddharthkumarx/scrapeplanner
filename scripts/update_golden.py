#!/usr/bin/env python3
"""Regenerate tests/golden/expected/<fixture>.json by replaying each fixture.

Review the diff before committing: a golden change is a behaviour change.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.golden.replay import EXPECTED, fixture_names, replay  # noqa: E402


def main() -> int:
    EXPECTED.mkdir(parents=True, exist_ok=True)
    failed = False
    for name in fixture_names():
        data, misses = replay(name)
        if misses:
            failed = True
            print(f"{name}: not recorded: {misses}", file=sys.stderr)
        path = EXPECTED / f"{name}.json"
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"{name}: {data['platform']['name']}, plan {data['plan']['recommended']}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

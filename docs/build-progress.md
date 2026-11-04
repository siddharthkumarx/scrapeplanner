# Build progress

Status: `todo` · `doing` · `done` · `blocked`. Update this file in the same
commit as the work. "Continue here" in CLAUDE.md points at the first item
that is not `done`.

| # | Item | Status | Notes |
|---|---|---|---|
| 1 | Name check, planning docs (CLAUDE.md, architecture, decisions, progress, incidents, readme-plan) | done | D-001 |
| 2 | Commit-message policy: checker script, `.githooks/commit-msg`, tests | done | `scripts/check_commit_msg.py`, `.githooks/commit-msg`, `tests/test_commit_policy.py` |
| 3 | Project scaffold: pyproject (uv, hatchling), src layout, py.typed, ruff/mypy/pytest config, `uv.lock` | done | `uv.lock` committed; `scripts/check.sh` runs the local checks |
| 4 | CI workflow: ruff, mypy, pytest matrix, gitleaks, pip-audit, commit policy | done | all jobs green on first run; actions pinned to commit SHAs (temporary `action-pins` job prints current tags) |
| 5 | Models (`models.py`): every report section as pydantic | done | `Report` is the `--json` schema (`schema_version` 1) |
| 6 | Polite fetcher (`fetch.py`) and record/replay (`record.py`) with unit tests | done | `tests/unit/test_fetch.py` |
| 7 | Live checks: `checks/request.yml`, `checks/run_checks.py`, `checks.yml` workflow; prove the round trip | done | round trip proven with `checks/results/001-smoke` (3 sites) |
| 8 | `html.py` shared parse helpers | done |  |
| 9 | Detector: robots | done | unit tests in `tests/unit/`; golden tests come with item 23 |
| 10 | Detector: sitemaps | done | unit tests in `tests/unit/`; golden tests come with item 23 |
| 11 | Detector: platform | done | unit tests in `tests/unit/`; golden tests come with item 23 |
| 12 | Detector: anti-bot | done | D-007; unit tests in `tests/unit/`; golden tests come with item 23 |
| 13 | Detector: structured data (JSON-LD, microdata) | done | D-002; unit tests in `tests/unit/`; golden tests come with item 23 |
| 14 | Detector: embedded state | done | unit tests in `tests/unit/`; golden tests come with item 23 |
| 15 | Detector: rendering (raw HTML vs browser) | done | unit tests in `tests/unit/`; golden tests come with item 23 |
| 16 | Detector: feeds (probes + linked feeds) | done | unit tests in `tests/unit/`; golden tests come with item 23 |
| 17 | Planner | done | unit tests in `tests/unit/`; golden tests come with item 23 |
| 18 | Analyzer (orchestration, budget use) | done | unit tests in `tests/unit/`; golden tests come with item 23 |
| 19 | Output: terminal report | done | unit tests in `tests/unit/`; golden tests come with item 23 |
| 20 | Output: `--json` | done | unit tests in `tests/unit/`; golden tests come with item 23 |
| 21 | Output: `--profile` (starter profile.yaml) | done | unit tests in `tests/unit/`; golden tests come with item 23 |
| 22 | CLI wiring (`cli.py`), console script | done | unit tests in `tests/unit/`; golden tests come with item 23 |
| 23 | Fixture run through checks workflow, import to `tests/fixtures/`, golden tests per detector + end-to-end replay | doing | request `002-sites` running; tooling: `scripts/import_fixture.py`, `scripts/update_golden.py`, `tests/golden/` |
| 24 | Results run on 30 public sites, `docs/results.md` | todo |  |
| 25 | Packaging: build, metadata, wheel smoke test; `release.yml` (Trusted Publishing, off) | doing | CI `build` job builds, runs `twine check --strict`, smoke-tests the wheel; `release.yml` written with `pypi` job `if: false` |
| 26 | Repo files: LICENSE, CONTRIBUTING, SECURITY, CHANGELOG, CODE_OF_CONDUCT, issue templates | done |  |
| 27 | README and animated terminal SVG of a real run | blocked | waits for the maintainer's README rules; notes in docs/readme-plan.md |

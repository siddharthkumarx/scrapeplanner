# Build progress

Status: `todo` · `doing` · `done` · `blocked`. Update this file in the same
commit as the work. "Continue here" in CLAUDE.md points at the first item
that is not `done`.

| # | Item | Status | Notes |
|---|---|---|---|
| 1 | Name check, planning docs (CLAUDE.md, architecture, decisions, progress, incidents, readme-plan) | done | D-001 |
| 2 | Commit-message policy: checker script, `.githooks/commit-msg`, tests | todo | D-008 |
| 3 | Project scaffold: pyproject (uv, hatchling), src layout, py.typed, ruff/mypy/pytest config, `uv.lock` | todo | D-003 |
| 4 | CI workflow: ruff, mypy, pytest matrix, gitleaks, pip-audit, commit policy | todo | |
| 5 | Models (`models.py`): every report section as pydantic | todo | |
| 6 | Polite fetcher (`fetch.py`) and record/replay (`record.py`) with unit tests | todo | D-006 |
| 7 | Live checks: `checks/request.yml`, `checks/run_checks.py`, `checks.yml` workflow; prove the round trip | todo | D-004 |
| 8 | `html.py` shared parse helpers | todo | |
| 9 | Detector: robots | todo | |
| 10 | Detector: sitemaps | todo | |
| 11 | Detector: platform | todo | |
| 12 | Detector: anti-bot | todo | D-007 |
| 13 | Detector: structured data (JSON-LD, microdata) | todo | D-002 |
| 14 | Detector: embedded state | todo | |
| 15 | Detector: rendering (raw HTML vs browser) | todo | |
| 16 | Detector: feeds (probes + linked feeds) | todo | |
| 17 | Planner | todo | |
| 18 | Analyzer (orchestration, budget use) | todo | |
| 19 | Output: terminal report | todo | |
| 20 | Output: `--json` | todo | |
| 21 | Output: `--profile` (starter profile.yaml) | todo | |
| 22 | CLI wiring (`cli.py`), console script | todo | |
| 23 | Fixture run through checks workflow, import to `tests/fixtures/`, golden tests per detector + end-to-end replay | todo | |
| 24 | Results run on 30 public sites, `docs/results.md` | todo | |
| 25 | Packaging: build, metadata, wheel smoke test; `release.yml` (Trusted Publishing, off) | todo | D-009 |
| 26 | Repo files: LICENSE, CONTRIBUTING, SECURITY, CHANGELOG, CODE_OF_CONDUCT, issue templates | todo | |
| 27 | README and animated terminal SVG of a real run | blocked | waits for the maintainer's README rules; notes in docs/readme-plan.md |

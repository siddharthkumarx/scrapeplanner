# Incidents

Anything that went wrong or surprised us during the build: what happened,
impact, fix, and what to do next time. Newest last.

## I-001 · 2026-11-04 · Connectivity probe from the sandbox

**What**: while checking whether PyPI was reachable from the dev sandbox,
two plain `curl` requests also went to `https://example.com` and
`https://www.shopify.com` (both answered 200). That was a connectivity test,
not part of a check, and it was done outside the checks workflow.

**Impact**: two requests, no data kept, nothing in the docs depends on them.

**Fix / rule**: all live requests to target sites go through the checks
workflow (D-004). The sandbox only talks to PyPI and GitHub.

## I-002 · 2026-11-04 · Lint job red after a scripted edit

**What**: a `sed` edit to test signatures made two lines longer than 100
characters, and the commit went out without re-running ruff. The `lint` job
failed on `db062d5`.

**Impact**: one red CI run; nothing shipped.

**Fix / rule**: `scripts/check.sh` runs ruff, ruff format, mypy and pytest.
Run it before every commit, including after mechanical edits.

## I-003 · 2026-11-04 · Smoke run: text report empty, small page misjudged

**What**: in `checks/results/001-smoke`, `report.txt` files were empty (rich
`Console.capture()` swallowed the recording), and example.com (577 bytes,
no scripts) was judged "needs a browser" only because its text is short.
react.dev's plan recommended its RSS feed, which holds only the latest 24
posts, for 1,000 items.

**Fix**: the runner renders into a `StringIO` console. A thin page counts as
browser-dependent only with an app shell or heavy scripts. Methods that
reach only part of N are marked `partial` and are recommended only when
nothing else works. (Commit `911e622`.)

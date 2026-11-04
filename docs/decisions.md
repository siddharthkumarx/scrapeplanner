# Decisions

Each entry: date, decision, why. Newest last. Do not rewrite old entries;
add a new one that supersedes them.

## D-001 · 2026-11-04 · Name: `scrapeplanner`

Checked on 2026-11-04 (14:31 UTC):

| Check | Result |
|---|---|
| `https://pypi.org/pypi/scrapeplanner/json` | 404 (free) |
| `https://pypi.org/pypi/scrape-planner/json` | 404 (free) |
| `https://pypi.org/pypi/scrape_planner/json` | 404 (free) |
| `https://pypi.org/pypi/scrape.planner/json` | 404 (free) |
| `https://pypi.org/simple/scrapeplanner/` and `/scrape-planner/` | 404 (free) |
| `https://test.pypi.org/simple/` for the same three spellings | 404 (free) |
| GitHub repository search `scrapeplanner` | only `siddharthkumarx/scrapeplanner-wip` (this repo) |
| GitHub repository search `scrape-planner in:name` (17 hits) | none named exactly `scrape-planner` / `scrape_planner` |
| GitHub user/org search `scrapeplanner`, `scrape-planner` | 0 |

PyPI normalises `-`, `_` and `.` to the same name (PEP 503), so the four
spellings are one name and it is free. Distribution name `scrapeplanner`,
import name `scrapeplanner`, console script `scrapeplanner`.

Re-check right before the first real upload. A squatter can register it in
between.

## D-002 · 2026-11-04 · Stack and versions

Latest releases on PyPI on 2026-11-04, with licenses:

| Package | Version | License | Role |
|---|---|---|---|
| httpx | 0.28.1 | BSD-3-Clause | HTTP client (streaming, MockTransport for replay) |
| selectolax | 1.0.2 | MIT | HTML parsing (Lexbor engine, typed, fast) |
| protego | 0.7.0 | BSD-3-Clause | robots.txt (RFC 9309, typed) |
| typer | 0.27.3 | MIT | CLI |
| rich | 15.0.0 | MIT | terminal report |
| pydantic | 2.14.2 | MIT | report models, JSON output |
| PyYAML | 6.0.3 | MIT | profile.yaml output, checks/request.yml |
| ruff | 0.17.3 | MIT | lint and format (dev) |
| mypy | 2.4.1 | MIT | type checking, `--strict` (dev) |
| pytest | 9.2.0 | MIT | tests (dev) |
| pip-audit | 2.10.1 | Apache-2.0 | dependency audit (CI) |
| types-PyYAML | 6.0.12.20261103 | Apache-2.0 | stubs (dev) |
| hatchling | 1.33.0 | MIT | build backend |

All are permissive and compatible with MIT. Runtime floor pins are set to
these versions' major/minor in `pyproject.toml`. `uv.lock` pins exact
versions for CI and pip-audit.

Not used:

- **parsel**: needs lxml and cssselect. selectolax alone covers CSS
  selection and text extraction.
- **extruct** (0.18.0, BSD): pulls lxml, rdflib, mf2py, html-text,
  jstyleson and w3lib for formats we do not need (RDFa, microformats,
  OpenGraph). We need JSON-LD and microdata only, so we have our own small
  parser (`detectors/structured.py`) on top of the selectolax tree. Fewer
  dependencies, one HTML parse per page.
- **respx**: `httpx.MockTransport` is enough for tests and replay.

## D-003 · 2026-11-04 · Python 3.11+, src layout, uv, hatchling

Python 3.11 is the floor the brief asks for. CI tests 3.11, 3.12, 3.13 and
3.14. `uv` manages the env and lockfile; `hatchling` builds (pure Python,
no build step). Version lives in `src/scrapeplanner/__init__.py`.

## D-004 · 2026-11-04 · Live checks only through GitHub Actions

The dev sandbox cannot reach most sites, and live traffic should come from
one documented place. `checks/request.yml` + `checks.yml` workflow is the
only way the project makes live requests during development. Results are
committed under `checks/results/<id>/` so every number in the docs points
at a committed run.

## D-005 · 2026-11-04 · One request log, recorded and replayable

The CLI has `--record DIR`. The same run that produces a results row also
produces the fixture for the golden tests. Bodies are stored gzipped to
keep the repo small. Only pages the tool fetched on its own (robots.txt,
one public page, one sitemap, feed probes) are stored, never personal data.
Fixtures keep the original bytes; they are not edited by hand.

## D-006 · 2026-11-04 · Politeness defaults

10 requests per site per run, at least 1 s between requests (more if
crawl-delay says so), honest UA with the project URL, robots.txt checked
for every URL, stop at the first block or challenge, no cookie jar, no
proxies (`trust_env=False`), no JavaScript execution. `--max-requests` can
raise the budget to at most 50. There is no flag to ignore robots.txt and
none will be added.

## D-007 · 2026-11-04 · Anti-bot handling is naming, not bypassing

The tool names the vendor and the evidence, and plans around it: slower
rate, fewer pages, ask the owner, or "not a fit". The code and docs contain
no evasion techniques (no header spoofing, no TLS fingerprint tricks, no
CAPTCHA services, no residential proxies). Pull requests adding them are
declined (CONTRIBUTING.md).

## D-008 · 2026-11-04 · Commit-message policy

No trailers except `Signed-off-by`, and no "Generated with" footer.
Enforced by `scripts/check_commit_msg.py` (stdlib only), run by the
`.githooks/commit-msg` hook (`git config core.hooksPath .githooks`) and by
the `commit-policy` CI job on every commit of the branch.

## D-009 · 2026-11-04 · Release: Trusted Publishing, switched off

`release.yml` runs on tags `v*`: build sdist and wheel with `uv build`,
check them, smoke-test the wheel. The `pypi` job uses Trusted Publishing
(OIDC, `id-token: write`, environment `pypi`); no token is stored anywhere.
It is switched off (`if: false`) until the maintainer says publish. A
manual `workflow_dispatch` run can publish to TestPyPI once a TestPyPI
trusted publisher is registered for this repo.

## D-010 · 2026-11-04 · Actions pinned to commit SHAs

Every `uses:` names a full commit SHA with the tag in a comment. Versions
current on 2026-11-04, read with `git ls-remote` from a CI job (the dev
sandbox cannot reach other repositories), and checked to be commits, not
annotated-tag objects:

| Action / tool | Version | Commit |
|---|---|---|
| actions/checkout | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| astral-sh/setup-uv | v10.3.3 | `68559e99cc807c1eb7e9238fd43a15bba460eec2` |
| actions/upload-artifact | v7.0.2 | `cf430e030ddbb5b0abf93d22962f4752f3646cd9` |
| actions/download-artifact | v8.0.2 | `9000827ccba6bdab643e8b6fd33ac0654aef8333` |
| pypa/gh-action-pypi-publish | v1.14.3 | `7245906fb61fa33a13554f9d5fb856fe61758086` |
| gitleaks (binary) | 8.30.1 | release tarball verified against its checksums file |

gitleaks runs as the released binary, not the gitleaks GitHub Action, so no
license key is needed if the repository moves to an organisation.

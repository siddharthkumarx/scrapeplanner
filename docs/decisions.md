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
| GitHub repository search `scrapeplanner` | only this repository (then private, under a work-in-progress name) |
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

## D-011 · 2026-11-04 · What a refusal means for the verdict

Any 401/403/429/503 or challenge stops the run (rule unchanged). For the
verdict: a challenge anywhere, or a refusal of the page itself, gives "not a
fit". A plain 403/429 on one optional probe gives "caution": the page we
already have is still evidence, the refused endpoint is unusable, and the
risk says a collector must stop at any 403/429. A 429 also raises the
planned delay to 5 s. Reason: gymshark.com and allbirds.com in the live runs
(I-004, I-005).

## D-012 · 2026-11-04 · Fixtures: all 30 sites of the results run

`tests/fixtures/` holds the exchanges of every site in the results run, byte for
byte. Git stores identical blobs once, so this adds no size on top of
`checks/results/`. Only pages the tool fetched itself are stored (robots.txt,
one public page, sitemaps, feed probes); cookie values are redacted at
record time. When a detector changes on purpose, regenerate the golden files
and review the diff; when the web changes, record a new run instead of
editing fixtures.

## D-013 · 2026-11-04 · Platform groups, "not checked", job boards and data portals

Platforms are chosen group by group: platforms that decide which public
feeds exist (commerce; hosted job boards Greenhouse, Lever, Ashby; data
portals CKAN, Socrata), then site builders and CMSs, then documentation
generators, then meta-frameworks, then client-side libraries. Libraries a
platform always brings are not repeated. When no page was served (block,
challenge, robots.txt) the platform is "not checked", not "unknown": nothing
was looked at. Job boards and CKAN get their documented public APIs probed,
because those return every record in one or a few requests.

## D-014 · 2026-11-04 · The public results set and platform labels

The public table holds sites a typical client brings and that are fine to
name: independent stores, company job boards, open-data portals, news and
docs sites, and scraping practice sites (I-007). Verdicts are published as
they come out. To measure platform detection, `expected_platform` is
written in `checks/request.yml` before a run, only where the platform is
known independently of this tool (the URL of a hosted board, the software a
portal publicly runs on, public knowledge). Labels are never edited after a
run; a wrong label gets a footnote (`scripts/results_notes.yml`). The
labelled set is small and not held out from development, so the README
quotes it as "matched N of M", not as an accuracy rate.

## D-015 · 2026-11-04 · README visuals

- Every terminal line in a visual is rendered by the real report renderer
  from a committed `report.json`; every count is computed from that run
  (`scripts/visuals/build.py`). The README shows no drawn output, so no
  "EXAMPLE" label is needed; the ladder is a diagram of the real decision
  order with real counts and names its run.
- SVG only, no external fonts or scripts: Instrument Sans and IBM Plex Mono
  are subset and embedded as WOFF2 (font timestamps pinned so the files are
  byte-stable). CSS animation, 8 to 10 s loops, final frame held at least
  2 s. The default style is the final frame; animations apply under
  `prefers-reduced-motion: no-preference`, and under `reduce` every
  animated element is given its final-state styles explicitly.
- Chromium does not pass `prefers-reduced-motion` into an SVG used as an
  image, so the README wraps each visual in `<picture>` with a
  `-still.svg` source for reduced motion.
- 1000-px viewBox, headings 36 px or more, all other text 30 px or more; the
  terminal report has a stacked layout below 80 columns so it stays readable
  at 50 columns.
- A `visual` CI job (Playwright, Chromium) checks the assets are current,
  self-contained, under 1 MB, use no text under 30 px, and that the
  reduced-motion render and the still match the final frame. Renders use
  grayscale antialiasing and whole-pixel text positions so animated and
  static layers rasterise alike; the comparison tolerates sub-pixel
  smoothing only (I-010).

## D-016 · 2026-11-04 · What a top-tier CLI repository has, and what was added

Added beyond the brief: a JSON Schema of `--json` kept current by a test
(`docs/report.schema.json`), `docs/output-formats.md`, `CITATION.cff`,
`.editorconfig`, Dependabot for actions and uv (monthly, grouped), a pull
request template, `python -m scrapeplanner`, a stacked terminal layout for
narrow terminals, `docs/repo-settings.md` and `docs/publish-checklist.md`.
Not added on purpose: a docs website (the README and `docs/` are enough for
one command), shell completion (one positional argument), telemetry (never).

## D-017 · 2026-11-04 · Fewer probes when one answer is enough

A probe is sent only when its answer can change the plan. The first case:
the Shopify per-product `.js` probe is skipped once `/products.json` has
returned products (I-009). The budget of 10 is a ceiling, not a target.

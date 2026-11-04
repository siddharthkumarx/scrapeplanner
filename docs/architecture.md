# Architecture

`scrapeplanner` takes one URL, makes a small number of polite HTTP requests
(10 by default), and reports the cheapest reliable way to collect that site's
data. It detects and plans. It never bypasses anything.

## Data flow

```
URL
 │
 ▼
PoliteFetcher  (fetch.py)    robots gate · per-site budget · delay · UA ·
 │                           manual redirects · size cap · stop on block
 │  every response is a FetchedPage (models.py); optional Recorder saves it
 ▼
Analyzer  (analyze.py)       decides which URLs to request, in this order:
 │   1. /robots.txt                       → detectors/robots.py
 │   2. the target page                   → platform, antibot, structured,
 │                                          embedded, rendering, links
 │   3. one sitemap (from robots or /sitemap.xml) → detectors/sitemaps.py
 │   4. feed probes picked from the platform     → detectors/feeds.py
 │      (stops early when the budget or a block says so)
 ▼
Planner  (planner.py)        ranks methods cheapest first, sets the polite
 │                           rate, estimates requests and time for N items,
 │                           lists risks, gives a fit verdict
 ▼
Report (models.Report, pydantic)
 ├── output/terminal.py   rich report (default)
 ├── output/json_out.py   --json  (Report.model_dump_json, schema_version)
 └── output/profile.py    --profile PATH  (starter profile.yaml)
```

Detectors are pure functions. They take parsed inputs (a `FetchedPage`, an
`HtmlDoc`, robots text) and return a pydantic model. They never do I/O.
Only the analyzer talks to the fetcher. That keeps every detector testable
offline against saved pages.

## Package layout

```
src/scrapeplanner/
  __init__.py        __version__
  py.typed
  cli.py             typer app, console script `scrapeplanner`
  config.py          defaults: USER_AGENT, PROJECT_URL, MAX_REQUESTS=10,
                     DELAY=1.0s, TIMEOUT, MAX_BODY_BYTES
  models.py          all pydantic models (the JSON schema of --json)
  fetch.py           PoliteFetcher, Budget, BlockedError, BudgetExceeded,
                     RobotsDisallowed
  record.py          Recorder (write exchanges) and ReplayTransport (read them)
  html.py            HtmlDoc: one selectolax parse shared by detectors,
                     helpers for scripts, links, visible text
  analyze.py         analyze(url, options, transport=None) -> Report
  planner.py         build_plan(...) -> Plan
  detectors/
    robots.py        parse robots.txt (protego): allowed paths, crawl-delay,
                     sitemaps listed
    sitemaps.py      parse a sitemap or sitemap index (count, newest lastmod)
    platform.py      Shopify, WooCommerce, Magento, BigCommerce, Wix,
                     Squarespace, Next.js, Nuxt, else unknown
    antibot.py       Cloudflare, Akamai, DataDome, HUMAN/PerimeterX,
                     Imperva, Kasada: presence vs active challenge
    structured.py    JSON-LD and microdata (own parser, see decisions)
    embedded.py      __NEXT_DATA__, Next flight data, Nuxt state, other
                     inline JSON state blobs
    rendering.py     is the key data in the raw HTML, or does it need a
                     browser
    feeds.py         candidate feeds per platform plus feeds linked from the
                     page; validates probe responses
  output/
    terminal.py  json_out.py  profile.py
```

## The polite fetcher (fetch.py)

All network I/O goes through one `PoliteFetcher` per run.

- **User-Agent**: `scrapeplanner/<version> (+https://github.com/siddharthkumarx/scrapeplanner)`.
- **robots.txt first**: the first request of every run is `/robots.txt`.
  Every later URL is checked with protego for our UA token `scrapeplanner`
  before it is requested. Disallowed URL: no request, the analyzer records
  `skipped: robots`. A robots.txt of 401/403 means "assume everything is
  disallowed" (the conservative reading of RFC 9309 §2.3.1.3). 404 or other
  4xx means no rules. 5xx or a network error means "assume disallowed".
- **Budget**: `max_requests` (default 10) per site per run, counted per
  HTTP request, including each redirect hop. Raising it is a CLI flag
  (`--max-requests`), capped at 50.
- **Delay**: at least `delay` seconds (default 1.0) between requests to the
  same site. If robots.txt sets `Crawl-delay` higher, that wins (capped at
  30 s; above the cap the run stops and says so).
- **Redirects**: handled by hand, at most 5 hops. Each hop is counted and
  checked against robots. Cross-site redirects are followed for the target
  page only (e.g. `example.com` → `www.example.com`); the site key moves to
  the final host.
- **Size and time caps**: bodies are streamed and cut at `MAX_BODY_BYTES`
  (5 MB); timeout 15 s per request.
- **Stop at the first block**: after each response, `detectors.antibot`
  classifies it. A challenge page, a 403/429 with vendor markers, or any
  429 sets `fetcher.blocked`. Every later `fetch()` raises `BlockedError`
  without touching the network. The report says where and why it stopped.
- **No cookies sent back**: the client keeps no cookie jar between requests
  (cookies are read for detection only). No proxies (`trust_env=False`),
  no logins, no CAPTCHA, no JavaScript execution.

## Recording and replay (record.py)

`--record DIR` writes each exchange: `DIR/exchanges.json` (method, URL,
status, headers, elapsed, body file name) plus gzipped bodies. Replay feeds
these back through an `httpx.MockTransport`, keyed by URL, so the analyzer
runs offline exactly as it did live. A URL that was not recorded returns a
synthetic 599 and fails tests loudly. Golden tests use replay. Live runs
happen only in GitHub Actions (see Live checks).

## Detection rules (summary)

Each detector returns `evidence`: short strings naming the signal that
fired (e.g. `header x-shopid`, `script cdn.shopify.com`). Confidence comes
from signal weights: `high` (one decisive signal or 2+ strong ones),
`medium`, `low`. The full signal tables live in the detector modules as
data, so they can be extended without touching the logic.

- Platform: commerce platforms win over frameworks (a headless Shopify on
  Next.js reports `shopify`, with `nextjs` listed under `frameworks`).
- Anti-bot: `present` (sensor, cookie or header seen, page served) or
  `challenge` (block or interstitial page). Cloudflare as a plain CDN
  (`server: cloudflare`, `cf-ray`) counts as present, not as a challenge.
- Rendering verdict: `raw_html` (key data in the HTML), `embedded_json`
  (data in an inline state blob), `browser_likely` (empty app shell, little
  visible text, no structured data), `unknown` (page not fetched).

## Planner (planner.py)

Candidate methods, cheapest first:

1. `feed_api`: a public feed or JSON endpoint that responded with valid
   data (Shopify products.json, WooCommerce Store API, JSON/RSS feed).
2. `structured_data`: JSON-LD or microdata of the key type.
3. `embedded_json`: `__NEXT_DATA__`, Nuxt payload, other inline state.
4. `html`: CSS selectors on the raw HTML.
5. `browser`: a headless browser. Last resort, highest cost.

Only methods with evidence are listed as usable. Others appear as `not
found`. The request estimate for N items (`--items`, default 1000) uses the
page size of the method (e.g. 250 per products.json page, 100 per Store API
page, 1 detail page per item for HTML or structured data, plus listing or
sitemap pages to find them). Time = requests × polite delay.

Polite delay: max(1 s, crawl-delay). With an anti-bot vendor present it is
raised to 5 s and the plan caps pages per day. With a challenge seen, the
verdict is `not_a_fit`: the advice is to ask the site owner for access or a
data export, never to get past the check.

## Live checks

The dev sandbox cannot reach most sites. Live runs go through
`.github/workflows/checks.yml`:

1. Edit `checks/request.yml` (an `id`, options, a list of targets) and push.
2. The workflow runs `checks/run_checks.py`, which calls the CLI on each
   target with `--json --record`, and writes `checks/results/<id>/`:
   `summary.json`, `summary.md`, and per target `report.json`,
   `report.txt`, `exchanges/`.
3. It commits the results to the same branch (`permissions: contents:
   write`). Pull to read them.

Fixtures for tests are copied from `checks/results/<id>/<target>/exchanges`
into `tests/fixtures/<target>/` with `scripts/import_fixture.py`.

## Tests

- `tests/unit/`: small hand-written inputs, one file per module.
- `tests/golden/`: real saved pages from `tests/fixtures/`, each detector's
  output compared with `tests/golden/expected/<site>.json`. Regenerate with
  `uv run python scripts/update_golden.py` and review the diff.
- `tests/test_commit_policy.py`: the commit-message checker.

## CI (.github/workflows/ci.yml)

ruff check, ruff format --check, mypy --strict, pytest on 3.11 to 3.14,
gitleaks (full history), pip-audit (locked deps), commit-message policy on
every commit of the branch. `release.yml` builds on tags `v*` and publishes
with PyPI Trusted Publishing. The publish job is switched off until the
maintainer says publish.

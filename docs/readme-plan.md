# README plan

The README is written last, after the maintainer sends the README rules.
Until then, collect material here.

## Hard rules already known

- Every number and claim in the README comes from `docs/results.md`
  (which comes from a committed run under `checks/results/`). Link the run.
- The animated terminal SVG must be a recording of a real run, not a mock.
- Detection and planning only. No wording that suggests bypassing anti-bot
  systems.

## Material to use

- One-line pitch: give it a URL, get the cheapest reliable, polite way to
  collect that site's data.
- Install: `pipx install scrapeplanner` / `uv tool install scrapeplanner`
  (only after the PyPI release; before that, install from git).
- Usage: `scrapeplanner URL`, `--json`, `--profile profile.yaml`,
  `--items N`, `--max-requests`, `--delay`.
- What it detects (list from docs/architecture.md).
- Politeness section (D-006), anti-bot stance (D-007).
- Results table summary: counts per platform and method, taken from
  docs/results.md.

## Claims the results table supports (docs/results.md, run 003-sites)

Quote these only with a link to docs/results.md. Re-check after any new run.

- 30 public sites (e-commerce 8, jobs 6, news 6, docs 5, listings 5), one
  page each, 1 to 8 requests per site, 103 requests in total, median 3.8 s
  per site.
- Verdicts: 14 good fit, 4 with care, 12 not a fit.
- Recommended methods: HTML 10, embedded JSON 5, structured data 2, feed /
  API 1.
- Anti-bot vendors named: Cloudflare 10 (5 challenge pages), HUMAN 2,
  Akamai 1 (CDN only), DataDome 1 (challenge), AWS WAF 1 (challenge).
- Politeness, in the tool's own numbers: Reuters and LinkedIn `/jobs/`
  disallowed by robots.txt, so one request each (robots.txt only); Hacker
  News crawl-delay 30 s respected (4 requests in 91 s); Best Buy robots.txt
  timed out, treated as disallow-all.
- Shopify example: allbirds.com, `/products.json` returned 250 products per
  page, plan of 4 requests for 1,000 products.

Do not claim accuracy percentages: the table shows what was detected, not a
labelled ground truth.

## Animated terminal SVG (later)

Record a real run in the checks workflow (asciinema `rec` of
`scrapeplanner <url>`), convert to SVG there, commit the .cast and the .svg
under `docs/assets/`, and name the run id in the caption. No staged output.

## Open questions for the maintainer

- Badges wanted? (CI, PyPI version, license, Python versions)
- Tone and length limits.
- Mention of siddharthkumar.com: where and how.

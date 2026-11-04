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

## I-004 · 2026-11-04 · First 30-site run (002-sites): four planner bugs

**What**: reviewing every row of `checks/results/002-sites` against its
recorded exchanges showed:

1. A travel site answered the page with HTTP 202 and an AWS WAF challenge
   page; the tool did not recognise it and went on to fetch two sitemaps.
   That broke "stop at the first challenge".
2. gymshark.com answered `/products.json` with 403; the whole site was
   marked "not a fit" although the page (with a 760 KB `__NEXT_DATA__`) had
   been served.
3. A marketplace's `server: AkamaiGHost` header alone was reported as Akamai
   bot management.
4. woocommerce.com: a WordPress per-page `/wp-json/` link was treated as a
   feed, and the child-sitemap choice picked `product_updates-sitemap.xml`.

Also, two requests that timed out (one sitemap, one robots.txt) were not
recorded, so they could not be replayed.

**Fix**: commit `0c4ae55` (see D-011), then a fresh run `003-sites` on the
fixed code. (Runs 002 to 005 used an earlier list of sites and were later
removed from the tree; see I-007.)

## I-005 · 2026-11-04 · allbirds.com answered 429 in the second run

**What**: in `003-sites` (about seven minutes after `002-sites`, both from
GitHub Actions), allbirds.com answered the sixth request
(`/products/<handle>.js`) with 429 at 1 s spacing. The run stopped there as
designed; the plan kept recommending 1 s.

**Fix**: commit after `89c3bcc`: a 429 during the run raises the planned
delay to 5 s. Golden files carry the new rate; the committed live report
keeps the old one, which is the only difference between replay and live.

## I-006 · 2026-11-04 · A site's own bot check was not recognised (004-sites)

**What**: in `004-sites` a large retailer answered the homepage with HTTP 200
and a 3.8 KB page: "Click the button below to continue shopping" and a form
posting to `/errors_page/validateCaptcha`. No vendor header or cookie was present, so
the tool did not see a challenge, went on to request `/sitemap.xml` (HTTP
500) and planned "good fit, HTML" on 142 characters of text. That broke the
"stop at the first challenge" rule.

**Fix**: a vendor-less `own_check` signal group (CAPTCHA forms and widgets,
"are you a robot" texts, validateCaptcha forms). Like every
challenge marker it counts only on a small or 4xx/5xx page, and these
signals are ignored entirely on a normal large page, so a newsletter
reCAPTCHA does not mark a site as bot-managed (replaying 003 and 004 showed
that false positive on allbirds.com and techcrunch.com before the guard).
Regression tests use the shape of the recorded page.

## I-007 · 2026-11-04 · Public results set replaced

**What**: the first results set included twelve large consumer sites. The
maintainer decided the public table should hold sites a typical client
brings and that are fine to name: independent stores, company job boards,
open-data portals, news and docs sites, and scraping practice sites.

**Fix**: run `005-sites` was cancelled mid-run, runs 002 to 004 were removed
from the tree, and `006-sites` became the public set. Fixtures and golden
files come from 006 only.

## I-008 · 2026-11-04 · 006-sites: Lever API over the size cap; one outdated label

**What**: two findings from reviewing `checks/results/006-sites` row by row.

1. `api.lever.co/v0/postings/palantir?mode=json` returned every posting with
   its full description: more than 5 MB. The body was cut at the size cap,
   did not parse, and the probe was reported as `invalid`, so the plan fell
   back to HTML.
2. catalog.data.gov was labelled `expected_platform: ckan` before the run,
   from public knowledge that Data.gov's catalog runs CKAN. The recorded page
   shows no CKAN markers at all (no generator, no `/api/3/action/` links, no
   CKAN assets; the front end is USWDS with htmx), so the tool's `unknown` is
   consistent with what was served and the label is out of date.

**Fix**: the Lever probe asks for `limit=100` and the plan pages with `skip`;
a truncated response that does not parse now says so in the report. The
label was not changed after the fact: `scripts/results_notes.yml` adds a
footnote to the table instead. Run `007-sites` repeats the same targets and
labels on the fixed code.

## I-009 · 2026-11-04 · Two Shopify stores answered 429 in 007-sites

**What**: `007-sites` ran about eight minutes after `006-sites` from GitHub
Actions. allbirds.com and ugmonk.com answered the sixth request, the
`/products/<handle>.js` probe, with 429; in 006 both had answered it with 200.
The run stopped there as designed, the plan raised its delay to 5 s, and both
sites are "with care" in the published table.

**Follow-up (not done yet)**: when `/products.json` already answered with
products, the per-product `.js` probe adds nothing to the plan. Skipping it
would save one request per Shopify store and avoid this 429. It changes the
requests of every Shopify fixture, so it needs its own results run.

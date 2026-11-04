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

1. booking.com answered the page with HTTP 202 and an AWS WAF challenge
   page; the tool did not recognise it and went on to fetch two sitemaps.
   That broke "stop at the first challenge".
2. gymshark.com answered `/products.json` with 403; the whole site was
   marked "not a fit" although the page (with a 760 KB `__NEXT_DATA__`) had
   been served.
3. eBay's `server: AkamaiGHost` alone was reported as Akamai bot management.
4. woocommerce.com: a WordPress per-page `/wp-json/` link was treated as a
   feed, and the child-sitemap choice picked `product_updates-sitemap.xml`.

Also, two requests that timed out (Amazon sitemap, Best Buy robots.txt) were
not recorded, so they could not be replayed.

**Fix**: commit `0c4ae55` (see D-011), then a fresh run `003-sites` on the
fixed code. That run is the source of `docs/results.md` and of
`tests/fixtures/`.

## I-005 · 2026-11-04 · allbirds.com answered 429 in the second run

**What**: in `003-sites` (about seven minutes after `002-sites`, both from
GitHub Actions), allbirds.com answered the sixth request
(`/products/<handle>.js`) with 429 at 1 s spacing. The run stopped there as
designed; the plan kept recommending 1 s.

**Fix**: commit after `89c3bcc`: a 429 during the run raises the planned
delay to 5 s. Golden files carry the new rate; the committed live report
keeps the old one, which is the only difference between replay and live.

## I-006 · 2026-11-04 · Amazon's own bot check was not recognised (004-sites)

**What**: in `004-sites` amazon.com answered the homepage with HTTP 200 and a
3.8 KB page: "Click the button below to continue shopping" and a form posting
to `/errors_page/validateCaptcha`. No vendor header or cookie was present, so
the tool did not see a challenge, went on to request `/sitemap.xml` (HTTP
500) and planned "good fit, HTML" on 142 characters of text. That broke the
"stop at the first challenge" rule.

**Fix**: a vendor-less `own_check` signal group (CAPTCHA forms and widgets,
"are you a robot" texts, Amazon's validateCaptcha form). Like every
challenge marker it counts only on a small or 4xx/5xx page, and these
signals are ignored entirely on a normal large page, so a newsletter
reCAPTCHA does not mark a site as bot-managed (replaying 003 and 004 showed
that false positive on allbirds.com and techcrunch.com before the guard).
Regression tests use the shape of the recorded page. The results table was
re-run as `005-sites`.

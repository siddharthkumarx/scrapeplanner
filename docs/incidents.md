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

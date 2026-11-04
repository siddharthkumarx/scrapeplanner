# Security policy

## Supported versions

Only the latest release receives fixes.

## Reporting a vulnerability

Please do not open a public issue. Use GitHub's private reporting:
**Security → Report a vulnerability** on this repository. You will get an
answer within 7 days. Once a fix is released, the report is credited in the
changelog unless you ask otherwise.

In scope: anything that makes `scrapeplanner` send requests it should not
(ignoring robots.txt, exceeding the request budget, following a block),
leak data from the machine it runs on, or execute content from a fetched
page. Parsing is done without executing scripts, and XML with DTDs or
entity declarations is refused.

## Out of scope

Requests to add ways around anti-bot systems, CAPTCHAs or logins are not
security reports and will be declined (see CONTRIBUTING.md).

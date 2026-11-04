# Repository settings

Values for GitHub → the repository's About panel and Settings, set when the
public repository is created (docs/publish-checklist.md).

## About (description)

> Point it at a URL; it reports the cheapest polite way to collect that site's data. Python CLI: reads robots.txt and sitemaps, detects the platform, public feeds and APIs, JSON-LD, embedded JSON and anti-bot vendors in about 10 requests, then plans the method, rate and request count. Detection only.

(299 characters; GitHub allows 350.)

## Website

`https://siddharthkumar.com`

## Topics (14)

```
web-scraping
scraping
crawler
robots-txt
sitemap
json-ld
structured-data
shopify
data-collection
data-engineering
python
cli
polite-crawling
web-data
```

## Social preview

Settings → General → Social preview → upload `assets/social-preview.png`
(1280 × 640).

## Other settings

- Features: Issues on, Discussions optional, Wiki off, Projects off.
- Pull requests: allow squash merging only; delete head branches after merge.
- Code security: private vulnerability reporting on (SECURITY.md relies on
  it), secret scanning on, Dependabot alerts and security updates on.
- Branch protection for `main`: require the `ci` workflow's jobs, require
  linear history, no force pushes.
- Releases: create them from tags `v*`; the `release` workflow builds them.

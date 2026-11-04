# Changelog

All notable changes are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/). The JSON output has its own
`schema_version`; a breaking change to it is a major version.

## [Unreleased]

### Added

- `scrapeplanner URL`: terminal report, `--json`, `--profile PATH`.
- Polite fetcher: robots.txt read first and checked for every URL, 10 requests
  per run by default (every redirect hop counts), at least 1 s between
  requests or the robots.txt crawl-delay, clear User-Agent, stop at the
  first block or challenge, no cookie jar, no proxies.
- Detectors: robots.txt, sitemaps, platform (Shopify, WooCommerce, Magento,
  BigCommerce, Wix, Squarespace, Next.js, Nuxt), public feeds (Shopify
  products.json and product .js, WooCommerce Store API, WordPress REST,
  RSS/Atom/JSON feeds linked from the page), JSON-LD and microdata,
  embedded state, rendering (raw HTML or browser), anti-bot vendor
  (Cloudflare, Akamai, DataDome, HUMAN, Imperva, Kasada).
- Planner: methods cheapest first, polite rate, request and time estimate
  for N items, risks and next steps.
- `--record DIR` saves every exchange for offline replay.
- Platforms: WordPress, Drupal, Webflow, Salesforce Commerce Cloud, Greenhouse,
  Lever, Ashby, CKAN, Socrata, Hugo, Sphinx, Docusaurus, Gatsby, Remix,
  SvelteKit, Astro, Angular, React, Vue, Lit. "not checked" when no page was
  served.
- Feeds: Greenhouse, Lever and Ashby job-board APIs; CKAN `package_search`.
- Anti-bot: AWS WAF, and a site's own CAPTCHA / "are you a robot" page.
- Stacked report layout for terminals narrower than 80 columns.
- JSON Schema of the `--json` output in `docs/report.schema.json`.

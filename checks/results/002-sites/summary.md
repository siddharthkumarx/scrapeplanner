# Check 002-sites

- scrapeplanner 0.1.0.dev0 at commit `db062d5d0b2b`
- runner: Linux 7.0.0-1017-azure (Linux), Python 3.12.3
- started 2026-11-04T14:57:05+00:00, finished 2026-11-04T15:00:46+00:00

| Target | Category | Verdict | Platform | Method | Anti-bot | Requests | Time (s) |
|---|---|---|---|---|---|---|---|
| allbirds | e-commerce | good | Shopify | Feed / API | Cloudflare (CDN only) | 6 | 6.3 |
| gymshark | e-commerce | not_a_fit | Shopify | - | none | 4 | 4.65 |
| amazon | e-commerce | good | unknown | HTML | none | 3 | 17.96 |
| ebay | e-commerce | not_a_fit | unknown | - | Akamai (present) | 2 | 1.38 |
| etsy | e-commerce | not_a_fit | unknown | - | DataDome (challenge) | 2 | 1.25 |
| walmart | e-commerce | caution | Next.js | Embedded JSON | HUMAN (PerimeterX) (present) | 3 | 3.2 |
| bestbuy | e-commerce | not_a_fit | unknown | - | none | 1 | 15.08 |
| woocommerce | e-commerce | good | WooCommerce | HTML | none | 4 | 3.37 |
| indeed | jobs | not_a_fit | unknown | - | Cloudflare (challenge) | 2 | 1.19 |
| linkedin-jobs | jobs | not_a_fit | unknown | - | Cloudflare (present) | 1 | 0.14 |
| glassdoor | jobs | not_a_fit | unknown | - | Cloudflare (present) | 2 | 1.1 |
| remoteok | jobs | good | unknown | Structured data | Cloudflare (CDN only) | 8 | 9.59 |
| weworkremotely | jobs | not_a_fit | unknown | - | Cloudflare (challenge) | 2 | 1.16 |
| himalayas | jobs | not_a_fit | unknown | - | Cloudflare (challenge) | 2 | 1.45 |
| bbc-news | news | good | Next.js | Embedded JSON | none | 3 | 2.23 |
| guardian | news | good | unknown | HTML | none | 7 | 6.99 |
| reuters | news | not_a_fit | unknown | - | none | 1 | 0.33 |
| apnews | news | not_a_fit | unknown | - | Cloudflare (challenge) | 2 | 1.09 |
| techcrunch | news | good | unknown | HTML | Cloudflare (CDN only) | 5 | 4.37 |
| hacker-news | news | good | unknown | HTML | none | 4 | 90.71 |
| python-docs | docs | good | unknown | HTML | none | 3 | 2.07 |
| mdn | docs | good | unknown | HTML | none | 5 | 4.57 |
| react-dev | docs | good | Next.js | HTML | none | 4 | 3.29 |
| nuxt-docs | docs | good | Nuxt | Structured data | none | 5 | 4.71 |
| kubernetes-docs | docs | good | unknown | HTML | none | 4 | 3.93 |
| craigslist-sf | listings | good | unknown | HTML | none | 6 | 6.4 |
| zillow | listings | caution | Next.js | Embedded JSON | HUMAN (PerimeterX) (present) | 4 | 4.48 |
| airbnb | listings | good | unknown | Embedded JSON | none | 4 | 6.84 |
| booking | listings | caution | unknown | Browser | none | 4 | 4.21 |
| producthunt | listings | not_a_fit | unknown | - | Cloudflare (challenge) | 2 | 1.22 |

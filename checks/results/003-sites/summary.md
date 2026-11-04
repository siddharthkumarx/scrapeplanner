# Check 003-sites

- scrapeplanner 0.1.0.dev0 at commit `67918dd65fdd`
- runner: Linux 7.0.0-1017-azure (Linux), Python 3.12.3
- started 2026-11-04T15:04:22+00:00, finished 2026-11-04T15:08:06+00:00

| Target | Category | Verdict | Platform | Method | Anti-bot | Requests | Time (s) |
|---|---|---|---|---|---|---|---|
| allbirds | e-commerce | caution | Shopify | Feed / API | Cloudflare (CDN only) | 6 | 6.76 |
| gymshark | e-commerce | caution | Shopify | Embedded JSON | none | 4 | 4.67 |
| amazon | e-commerce | good | unknown | HTML | none | 3 | 12.66 |
| ebay | e-commerce | not_a_fit | unknown | - | Akamai (CDN only) | 2 | 1.53 |
| etsy | e-commerce | not_a_fit | unknown | - | DataDome (challenge) | 2 | 1.18 |
| walmart | e-commerce | caution | Next.js | Embedded JSON | HUMAN/PerimeterX (present) | 3 | 3.76 |
| bestbuy | e-commerce | not_a_fit | unknown | - | none | 1 | 15.21 |
| woocommerce | e-commerce | good | WooCommerce | HTML | none | 4 | 8.43 |
| indeed | jobs | not_a_fit | unknown | - | Cloudflare (challenge) | 2 | 1.42 |
| linkedin-jobs | jobs | not_a_fit | unknown | - | Cloudflare (present) | 1 | 0.23 |
| glassdoor | jobs | not_a_fit | unknown | - | Cloudflare (present) | 2 | 1.1 |
| remoteok | jobs | good | unknown | Structured data | Cloudflare (CDN only) | 8 | 11.43 |
| weworkremotely | jobs | not_a_fit | unknown | - | Cloudflare (challenge) | 2 | 1.18 |
| himalayas | jobs | not_a_fit | unknown | - | Cloudflare (challenge) | 2 | 1.52 |
| bbc-news | news | good | Next.js | Embedded JSON | none | 3 | 2.34 |
| guardian | news | good | unknown | HTML | none | 7 | 7.04 |
| reuters | news | not_a_fit | unknown | - | none | 1 | 0.33 |
| apnews | news | not_a_fit | unknown | - | Cloudflare (challenge) | 2 | 1.11 |
| techcrunch | news | good | unknown | HTML | Cloudflare (CDN only) | 5 | 4.4 |
| hacker-news | news | good | unknown | HTML | none | 4 | 91.23 |
| python-docs | docs | good | unknown | HTML | none | 3 | 2.16 |
| mdn | docs | good | unknown | HTML | none | 5 | 5.19 |
| react-dev | docs | good | Next.js | HTML | none | 4 | 3.4 |
| nuxt-docs | docs | good | Nuxt | Structured data | none | 5 | 4.57 |
| kubernetes-docs | docs | good | unknown | HTML | none | 4 | 3.81 |
| craigslist-sf | listings | good | unknown | HTML | none | 6 | 5.78 |
| zillow | listings | caution | Next.js | Embedded JSON | HUMAN/PerimeterX (present) | 4 | 5.76 |
| airbnb | listings | good | unknown | Embedded JSON | none | 4 | 4.49 |
| booking | listings | not_a_fit | unknown | - | AWS WAF (challenge) | 2 | 1.33 |
| producthunt | listings | not_a_fit | unknown | - | Cloudflare (challenge) | 2 | 1.11 |

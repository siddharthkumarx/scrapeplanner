# Check 004-sites

- scrapeplanner 0.1.0.dev0 at commit `02ffbb9e288c`
- runner: Linux 7.0.0-1017-azure (Linux), Python 3.12.3
- started 2026-11-04T18:01:32+00:00, finished 2026-11-04T18:05:09+00:00

| Target | Category | Verdict | Platform | Method | Anti-bot | Requests | Time (s) |
|---|---|---|---|---|---|---|---|
| allbirds | e-commerce | good | Shopify | Feed / API | Cloudflare (CDN only) | 6 | 6.99 |
| gymshark | e-commerce | caution | Shopify | Embedded JSON | none | 4 | 5.12 |
| amazon | e-commerce | good | unknown | HTML | none | 3 | 7.41 |
| ebay | e-commerce | not_a_fit | not checked | - | Akamai (CDN only) | 2 | 1.36 |
| etsy | e-commerce | not_a_fit | not checked | - | DataDome (challenge) | 2 | 1.25 |
| walmart | e-commerce | caution | Next.js | Embedded JSON | HUMAN/PerimeterX (present) | 3 | 3.36 |
| bestbuy | e-commerce | not_a_fit | not checked | - | none | 1 | 15.13 |
| woocommerce | e-commerce | good | WooCommerce | HTML | none | 4 | 4.34 |
| indeed | jobs | not_a_fit | not checked | - | Cloudflare (challenge) | 2 | 1.17 |
| linkedin-jobs | jobs | not_a_fit | not checked | - | Cloudflare (present) | 1 | 0.2 |
| glassdoor | jobs | not_a_fit | not checked | - | Cloudflare (present) | 2 | 1.1 |
| remoteok | jobs | good | unknown | Structured data | Cloudflare (CDN only) | 8 | 14.6 |
| weworkremotely | jobs | not_a_fit | not checked | - | Cloudflare (challenge) | 2 | 1.15 |
| himalayas | jobs | not_a_fit | not checked | - | Cloudflare (challenge) | 2 | 1.61 |
| bbc-news | news | good | Next.js | Embedded JSON | none | 3 | 2.4 |
| guardian | news | good | unknown | HTML | none | 7 | 7.0 |
| reuters | news | not_a_fit | not checked | - | none | 1 | 0.2 |
| apnews | news | not_a_fit | not checked | - | Cloudflare (challenge) | 2 | 1.1 |
| techcrunch | news | good | WordPress | HTML | Cloudflare (CDN only) | 5 | 4.47 |
| hacker-news | news | good | unknown | HTML | none | 4 | 90.66 |
| python-docs | docs | good | Sphinx | HTML | none | 3 | 2.08 |
| mdn | docs | good | Lit | HTML | none | 5 | 4.84 |
| react-dev | docs | good | Next.js | HTML | none | 4 | 3.32 |
| nuxt-docs | docs | good | Nuxt | Structured data | none | 5 | 4.78 |
| kubernetes-docs | docs | good | Hugo | HTML | none | 4 | 3.99 |
| craigslist-sf | listings | good | unknown | HTML | none | 6 | 6.1 |
| zillow | listings | caution | Next.js | Embedded JSON | HUMAN/PerimeterX (present) | 4 | 6.84 |
| airbnb | listings | good | React | Embedded JSON | none | 4 | 4.82 |
| booking | listings | not_a_fit | not checked | - | AWS WAF (challenge) | 2 | 1.41 |
| producthunt | listings | not_a_fit | not checked | - | Cloudflare (challenge) | 2 | 1.18 |

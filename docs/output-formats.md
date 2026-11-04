# Output formats

`scrapeplanner URL` prints a terminal report. Two flags write machine-readable
output: `--json` (the full report) and `--profile PATH` (a starter
`profile.yaml`). Examples below come from the recorded run
`checks/results/007-sites/deathwish-coffee/`.

## `--json`

The JSON Schema is [report.schema.json](report.schema.json) (generated from
`src/scrapeplanner/models.py` by `scripts/export_schema.py`; a test keeps it
current). `schema_version` changes only on a breaking change, which is also a
major version of the package.

| Key | Type | Meaning |
|---|---|---|
| `schema_version` | `"1"` | Version of this format |
| `tool` | object | `name`, `version`, `user_agent` sent with every request |
| `input_url`, `site` | string | The URL as normalised, and the host that answered |
| `started_at`, `duration_seconds` | string, number | UTC start time; wall time including polite delays |
| `max_requests`, `requests_used` | integer | The budget and how much of it was used |
| `requests` | list | Every request sent: `url`, `purpose`, `status`, `elapsed_ms`, `bytes`, `error` |
| `skipped` | list | Requests not sent, with `reason`: `robots`, `budget`, `blocked`, `crawl_delay` |
| `stopped` | object or null | Why the run stopped early: `reason`, `url`, `detail` |
| `page` | object | The analysed page: status, final URL, content type, size, title, language |
| `robots` | object | robots.txt status, `paths` (path → allowed), `crawl_delay`, `request_rate`, listed `sitemaps` |
| `sitemap` | object | The sitemap read: `kind`, `url_count` or `child_sitemaps`, `newest_lastmod`, `sample_urls`, and one `child` |
| `platform` | object | `name`, `confidence`, `evidence`, other `frameworks`, `generator`, `checked` |
| `antibot` | object | `vendors` (each `present` or `challenge`, `bot_management`, `evidence`), `challenged` |
| `structured` | object | JSON-LD / microdata counts, `types`, `items` (fields present per type), `key_types` |
| `embedded` | object | Inline state blobs: `kind`, `locator`, `bytes`, top-level `keys` |
| `rendering` | object | `verdict` (`raw_html`, `embedded_json`, `browser_likely`), text and script sizes, reasons |
| `feeds` | object | `candidates`: each feed or API with `status` (`ok`, `not_found`, `invalid`, `skipped_robots`, `skipped_budget`, `blocked`, `linked`), items seen, total, fields |
| `plan` | object | `verdict`, `recommended`, `items`, `rate`, `methods` (each with `usable`, `partial`, `urls`, `fields`, `est_requests`, `est_hours`, `notes`), `risks`, `next_steps` |

Example, the top of a report:

```json
{
  "schema_version": "1",
  "tool": {
    "name": "scrapeplanner",
    "version": "0.1.0.dev0",
    "user_agent": "scrapeplanner/0.1.0.dev0 (+https://github.com/siddharthkumarx/scrapeplanner)"
  },
  "input_url": "https://www.deathwishcoffee.com/",
  "site": "www.deathwishcoffee.com",
  "started_at": "2026-11-04T18:22:44+00:00",
  "duration_seconds": 6.55,
  "max_requests": 10,
  "requests_used": 6,
  "stopped": null
}
```

and its plan summary (`jq -c '.plan | {verdict, recommended, items, rate}'`):

```json
{"verdict":"good","recommended":"feed_api","items":1000,"rate":{"delay_seconds":1.0,"concurrency":1,"max_requests_per_day":null,"reason":"default 1s between requests"}}
```

## `--profile PATH`

A starting point for a collector, written from one analysis run. Review it;
re-run to refresh it.

| Key | Meaning |
|---|---|
| `profile_version` | Version of this format (1) |
| `generated_by`, `generated_at`, `site`, `verdict` | Where the profile came from |
| `method` | The recommended method (`feed_api`, `structured_data`, `embedded_json`, `html`, `browser`), or null when the site is not a fit |
| `source.urls` | URLs to start from; `{page}` / `{offset}` placeholders for pagination |
| `source.pagination` | `param`, `start`, `stop_when`, when the source pages |
| `source.discover_from_sitemap` | Sitemap to find detail pages, for page-based methods |
| `fields` | Fields the source showed in this run |
| `rate` | `delay_seconds`, `concurrency`, `max_requests_per_day`, and the `reason` |
| `politeness` | `user_agent`, `respect_robots_txt`, `crawl_delay`, `stop_on` (challenge, 401, 403, 429, 503), and what a collector must not use |
| `estimate` | `items`, `requests`, `hours` for the recommended method |
| `notes` | Method notes and the plan's risks |

For a site that is not a fit, `method` is null, `source.urls` is empty and
`notes` carries the reason and the next step (ask the owner).

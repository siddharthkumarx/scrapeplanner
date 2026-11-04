# README plan

The README is written last, after the maintainer sends the README rules.
Until then, collect material here.

## Hard rules already known

- Every number and claim in the README comes from `docs/results.md`
  (which comes from a committed run under `checks/results/`). Link the run.
- The animated terminal SVG must be a recording of a real run, not a mock.
- Detection and planning only. No wording that suggests bypassing anti-bot
  systems.

## Material to use

- One-line pitch: give it a URL, get the cheapest reliable, polite way to
  collect that site's data.
- Install: `pipx install scrapeplanner` / `uv tool install scrapeplanner`
  (only after the PyPI release; before that, install from git).
- Usage: `scrapeplanner URL`, `--json`, `--profile profile.yaml`,
  `--items N`, `--max-requests`, `--delay`.
- What it detects (list from docs/architecture.md).
- Politeness section (D-006), anti-bot stance (D-007).
- Results table summary: counts per platform and method, taken from
  docs/results.md.

## Claims the results table supports

Written into the README from docs/results.md (run 006-sites) only. Re-check
after any new run.

## Animated terminal SVG (later)

Record a real run in the checks workflow (asciinema `rec` of
`scrapeplanner <url>`), convert to SVG there, commit the .cast and the .svg
under `docs/assets/`, and name the run id in the caption. No staged output.

## Open questions for the maintainer

- Badges wanted? (CI, PyPI version, license, Python versions)
- Tone and length limits.
- Mention of siddharthkumar.com: where and how.

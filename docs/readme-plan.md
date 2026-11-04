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

## Open questions for the maintainer

- Badges wanted? (CI, PyPI version, license, Python versions)
- Tone and length limits.
- Mention of siddharthkumar.com: where and how.

# Contributing

Thanks for helping. Bug reports, new platform signals and fixture pages are
the most useful contributions.

## Ground rules

`scrapeplanner` detects and plans. It never bypasses anything. Pull requests
that add any of the following are declined, however they are framed:

- ways around anti-bot systems, CAPTCHAs, logins or paywalls;
- proxies, IP rotation, browser or TLS fingerprint spoofing;
- options to ignore robots.txt or raise the request budget past its cap;
- collection of personal data.

Every number in the docs must come from a committed run (`checks/results/`).

## Development

```bash
git clone https://github.com/siddharthkumarx/scrapeplanner
cd scrapeplanner
git config core.hooksPath .githooks   # commit-message policy
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy
```

Tests run offline. Do not add tests that reach the network.

## Adding or changing a detector signal

1. Signals live as data tables at the top of each module in
   `src/scrapeplanner/detectors/` (`platform.py`, `antibot.py`, ...). Add a
   row: the name, where to look (`header`, `cookie`, `html`, `generator`,
   `url`), a regular expression, a weight (3 = decisive, 2 = strong,
   1 = hint) and a short label that reads well in a report.
2. A new platform also needs a name in `PlatformName` and `PLATFORM_LABELS`
   (`src/scrapeplanner/models.py`) and a place in `GROUPS` (`platform.py`).
   If it has a public feed, add the candidate in `detectors/feeds.py`
   (`candidates()` and `evaluate()`) and its estimate in `planner.py`.
3. Add a unit test in `tests/unit/test_detectors.py` with a minimal input,
   and one negative case that must not match.
4. Run `./scripts/check.sh`. If golden files change, run
   `uv run python scripts/update_golden.py` and explain the diff in the
   pull request.
5. If you have a public page that shows the signal, mention it; the
   maintainer can record it through the checks workflow and add it to
   `tests/fixtures/`. Please do not attach pages with personal data.

## Visuals

`assets/*.svg`, `assets/social-preview.png` and `media/linkedin-demo.mp4` are
built from a committed run:

```bash
uv sync --group visual
uv run playwright install chromium
uv run python scripts/visuals/build.py     # SVGs
uv run python scripts/visuals/media.py     # PNG and MP4 (needs ffmpeg)
uv run pytest -m visual
```

## Commit messages

Short imperative subject, a body that says why. No trailers except
`Signed-off-by`, and no "Generated with" footers; the `commit-msg` hook and
CI check this.

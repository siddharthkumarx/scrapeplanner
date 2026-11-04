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
   `src/scrapeplanner/detectors/`. Add a row with a clear label.
2. Add a unit test in `tests/unit/test_detectors.py` with a minimal input.
3. If you have a real page that shows the signal, the maintainer can record
   it through the checks workflow and add it to `tests/fixtures/`. Please do
   not attach pages that contain personal data.
4. If golden files change, run `uv run python scripts/update_golden.py` and
   explain the diff in the pull request.

## Commit messages

Short imperative subject, a body that says why. No trailers except
`Signed-off-by`, and no "Generated with" footers; the `commit-msg` hook and
CI check this.

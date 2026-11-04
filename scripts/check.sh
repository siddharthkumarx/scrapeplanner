#!/bin/sh
# Run every local check CI runs (except gitleaks and pip-audit). Use before each commit.
set -eu
cd "$(dirname "$0")/.."
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -q

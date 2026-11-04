"""Defaults that define how polite the tool is. See docs/decisions.md (D-006)."""

from __future__ import annotations

from typing import Final

from scrapeplanner import __version__

PROJECT_URL: Final = "https://github.com/siddharthkumarx/scrapeplanner"
UA_TOKEN: Final = "scrapeplanner"
USER_AGENT: Final = f"{UA_TOKEN}/{__version__} (+{PROJECT_URL})"

MAX_REQUESTS: Final = 10
"""Default request budget per site per run (every redirect hop counts)."""
MAX_REQUESTS_CAP: Final = 50
"""Hard ceiling for ``--max-requests``."""
DELAY_SECONDS: Final = 1.0
"""Minimum gap between two requests to the same site."""
MAX_CRAWL_DELAY: Final = 30.0
"""A robots.txt crawl-delay above this stops the run instead of waiting."""
TIMEOUT_SECONDS: Final = 15.0
MAX_BODY_BYTES: Final = 5_000_000
MAX_REDIRECTS: Final = 5
DEFAULT_ITEMS: Final = 1000
"""Default N for the request estimate."""

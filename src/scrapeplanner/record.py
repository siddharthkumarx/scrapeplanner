"""Save HTTP exchanges during a live run and replay them offline.

Layout of a recording directory::

    exchanges.json    [{"index", "method", "url", "status", "headers",
                        "elapsed_ms", "truncated", "body"}]
    000.body.gz       response body, gzipped (decoded, as the tool saw it)

Cookie values in ``set-cookie`` headers are replaced by ``<redacted>``: only
cookie names matter for detection, and values can be session identifiers.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from scrapeplanner.fetch import FetchedPage

INDEX_FILE = "exchanges.json"
REDACTED = "<redacted>"
# Headers that describe the transfer, not the content: dropped on replay because
# the stored body is already decoded.
_TRANSFER_HEADERS = frozenset({"content-encoding", "content-length", "transfer-encoding"})


def redact_set_cookie(value: str) -> str:
    name, sep, rest = value.partition("=")
    if not sep:
        return value
    _, semi, attributes = rest.partition(";")
    return f"{name}={REDACTED}{semi}{attributes}"


class Recorder:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.entries: list[dict[str, Any]] = []

    def save(self, page: FetchedPage) -> None:
        index = len(self.entries)
        body_name = f"{index:03d}.body.gz"
        # mtime=0 keeps the gzip bytes stable across runs.
        (self.directory / body_name).write_bytes(gzip.compress(page.body, mtime=0))
        headers = [
            [key, redact_set_cookie(value) if key.lower() == "set-cookie" else value]
            for key, value in page.headers.multi_items()
        ]
        self.entries.append(
            {
                "index": index,
                "method": "GET",
                "url": page.final_url,
                "purpose": page.purpose,
                "status": page.status,
                "headers": headers,
                "elapsed_ms": page.elapsed_ms,
                "truncated": page.truncated,
                "body": body_name,
            }
        )
        self._flush()

    def _flush(self) -> None:
        path = self.directory / INDEX_FILE
        path.write_text(json.dumps(self.entries, indent=1) + "\n", encoding="utf-8")


def load_exchanges(directory: Path) -> list[dict[str, Any]]:
    data = json.loads((directory / INDEX_FILE).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{directory / INDEX_FILE}: expected a list")
    return data


def load_body(directory: Path, entry: dict[str, Any]) -> bytes:
    return gzip.decompress((directory / str(entry["body"])).read_bytes())


class ReplayTransport(httpx.BaseTransport):
    """Serve recorded responses by URL. Unknown URLs get a 599 and are listed in ``misses``."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._queue: dict[str, list[dict[str, Any]]] = {}
        for entry in load_exchanges(directory):
            self._queue.setdefault(str(entry["url"]), []).append(entry)
        self.misses: list[str] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        queue = self._queue.get(url)
        if not queue:
            self.misses.append(url)
            return httpx.Response(599, text=f"not recorded: {url}", request=request)
        entry = queue.pop(0) if len(queue) > 1 else queue[0]
        headers = [
            (str(key), str(value))
            for key, value in entry["headers"]
            if str(key).lower() not in _TRANSFER_HEADERS
        ]
        return httpx.Response(
            int(entry["status"]),
            headers=headers,
            content=load_body(self.directory, entry),
            request=request,
        )

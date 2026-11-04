"""Embedded state: data that frameworks serialise into the page for hydration."""

from __future__ import annotations

import json
import re
from typing import Any

from scrapeplanner.html import HtmlDoc, Script
from scrapeplanner.models import EmbeddedBlob, EmbeddedStateReport

MIN_JSON_SCRIPT_BYTES = 1_000
"""Smaller application/json scripts are usually config, not data."""
MAX_KEYS = 15
MAX_BLOBS = 10

_WINDOW_STATE = re.compile(
    r"window\.(__APOLLO_STATE__|__INITIAL_STATE__|__PRELOADED_STATE__|__REDUX_STATE__|"
    r"__INITIAL_DATA__|__STATE__|__DATA__|__APP_STATE__|__SERVER_DATA__)\s*=\s*"
)
_NUXT2 = re.compile(r"window\.__NUXT__\s*=")
_NEXT_FLIGHT = "self.__next_f.push("


def _keys(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [str(key) for key in list(value)[:MAX_KEYS]]
    return []


def _json_after(text: str, start: int) -> Any:
    """Parse the JSON value that starts at ``text[start:]`` (raw_decode stops at its end)."""
    try:
        value, _ = json.JSONDecoder().raw_decode(text[start:].lstrip())
    except (json.JSONDecodeError, RecursionError):
        return None
    return value


def _apollo_keys(state: Any) -> list[str]:
    """Apollo normalised cache: summarise by typename ('Product:123' -> 'Product')."""
    if not isinstance(state, dict):
        return []
    counts: dict[str, int] = {}
    for key in state:
        name = str(key).split(":", 1)[0]
        counts[name] = counts.get(name, 0) + 1
    ranked = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return [f"{name} x{count}" for name, count in ranked[:MAX_KEYS]]


def _locator(script: Script) -> str:
    if script.id:
        return f"script#{script.id}"
    for attr in sorted(script.attrs):
        if attr.startswith("data-"):
            return f"script[{attr}]"
    return f"script[type={script.type}]"


def detect(doc: HtmlDoc) -> EmbeddedStateReport:
    blobs: list[EmbeddedBlob] = []
    flight_chunks = 0
    flight_bytes = 0
    for script in doc.scripts:
        text = script.text
        size = len(text.encode("utf-8"))
        if script.id == "__NEXT_DATA__":
            data = _json_after(text, 0)
            details = {}
            if isinstance(data, dict):
                for key in ("page", "buildId"):
                    if isinstance(data.get(key), str):
                        details[key] = data[key]
                props = data.get("props")
                page_props = props.get("pageProps") if isinstance(props, dict) else None
            else:
                page_props = None
            blobs.append(
                EmbeddedBlob(
                    kind="next_data",
                    locator="script#__NEXT_DATA__",
                    bytes=size,
                    keys=_keys(page_props),
                    details=details,
                )
            )
        elif script.id == "__NUXT_DATA__":
            blobs.append(
                EmbeddedBlob(
                    kind="nuxt_data",
                    locator="script#__NUXT_DATA__",
                    bytes=size,
                    details={"format": "devalue (Nuxt 3)"},
                )
            )
        elif _NEXT_FLIGHT in text:
            flight_chunks += text.count(_NEXT_FLIGHT)
            flight_bytes += size
        elif _NUXT2.search(text):
            match = _NUXT2.search(text)
            value = _json_after(text, match.end()) if match else None
            blobs.append(
                EmbeddedBlob(
                    kind="nuxt_state",
                    locator="window.__NUXT__",
                    bytes=size,
                    keys=_keys(value),
                    details={"format": "json" if value is not None else "javascript (Nuxt 2)"},
                )
            )
        elif match := _WINDOW_STATE.search(text):
            name = match.group(1)
            value = _json_after(text, match.end())
            apollo = name == "__APOLLO_STATE__"
            blobs.append(
                EmbeddedBlob(
                    kind="apollo_state" if apollo else "redux_state",
                    locator=f"window.{name}",
                    bytes=size,
                    keys=_apollo_keys(value) if apollo else _keys(value),
                    details={"format": "json" if value is not None else "javascript"},
                )
            )
        elif script.type in ("application/json", "text/json") and size >= MIN_JSON_SCRIPT_BYTES:
            value = _json_after(text, 0)
            blobs.append(
                EmbeddedBlob(
                    kind="json_script", locator=_locator(script), bytes=size, keys=_keys(value)
                )
            )
    if flight_chunks:
        blobs.append(
            EmbeddedBlob(
                kind="next_flight",
                locator="self.__next_f.push",
                bytes=flight_bytes,
                details={"chunks": str(flight_chunks), "format": "React Server Components"},
            )
        )
    blobs.sort(key=lambda blob: -blob.bytes)
    return EmbeddedStateReport(blobs=blobs[:MAX_BLOBS])

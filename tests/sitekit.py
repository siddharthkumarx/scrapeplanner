"""Tiny fake sites for unit tests (served through httpx.MockTransport)."""

from __future__ import annotations

from collections.abc import Callable, Mapping

import httpx

Route = tuple[int, Mapping[str, str], str | bytes]


def transport(routes: Mapping[str, Route], seen: list[str] | None = None) -> httpx.MockTransport:
    """Serve ``routes`` keyed by full URL; anything else is a 404."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if seen is not None:
            seen.append(url)
        if url not in routes:
            return httpx.Response(404, text="not found")
        status, headers, body = routes[url]
        content = body.encode("utf-8") if isinstance(body, str) else body
        return httpx.Response(status, headers=headers, content=content)

    return httpx.MockTransport(handler)


def no_sleep() -> tuple[list[float], Callable[[float], None]]:
    slept: list[float] = []
    return slept, slept.append

"""Request: a lazy view over `scope` + `receive`.

The body is *not* read until you ask for it, and it's read exactly once:
`receive()` is a queue, not a file, so a second read would hang. Starlette
caches for the same reason (`Request._body`).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from typing import Any
from urllib.parse import parse_qsl

from .types import Receive, Scope


class Headers(Mapping[str, str]):
    """Case-insensitive, read-only view over ASGI's `list[tuple[bytes, bytes]]`."""

    def __init__(self, raw: list[tuple[bytes, bytes]]) -> None:
        self._items = [(k.decode("latin-1").lower(), v.decode("latin-1")) for k, v in raw]

    def __getitem__(self, key: str) -> str:
        key = key.lower()
        for k, v in self._items:
            if k == key:
                return v
        raise KeyError(key)

    def __iter__(self) -> Any:
        return iter(dict(self._items))

    def __len__(self) -> int:
        return len(dict(self._items))

    def getlist(self, key: str) -> list[str]:
        key = key.lower()
        return [v for k, v in self._items if k == key]


class Request:
    def __init__(self, scope: Scope, receive: Receive) -> None:
        assert scope["type"] == "http"
        self.scope = scope
        self._receive = receive
        self._body: bytes | None = None
        self._stream_consumed = False

    @property
    def method(self) -> str:
        return str(self.scope["method"])

    @property
    def path(self) -> str:
        return str(self.scope["path"])

    @property
    def headers(self) -> Headers:
        return Headers(self.scope["headers"])

    @property
    def query_params(self) -> dict[str, str]:
        return dict(parse_qsl(self.scope.get("query_string", b"").decode("latin-1")))

    @property
    def path_params(self) -> dict[str, Any]:
        return dict(self.scope.get("path_params", {}))

    @property
    def state(self) -> dict[str, Any]:
        """Per-connection scratch space; middleware writes here, handlers read."""
        return self.scope.setdefault("state", {})  # type: ignore[no-any-return]

    async def stream(self) -> AsyncIterator[bytes]:
        if self._body is not None:
            yield self._body
            return
        if self._stream_consumed:
            raise RuntimeError("stream consumed")
        self._stream_consumed = True
        while True:
            message = await self._receive()
            if message["type"] == "http.request":
                chunk = message.get("body", b"")
                if chunk:
                    yield chunk
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                raise ClientDisconnect

    async def body(self) -> bytes:
        if self._body is None:
            chunks = [c async for c in self.stream()]
            self._body = b"".join(chunks)
        return self._body

    async def json(self) -> Any:
        return json.loads(await self.body())


class ClientDisconnect(Exception):
    pass

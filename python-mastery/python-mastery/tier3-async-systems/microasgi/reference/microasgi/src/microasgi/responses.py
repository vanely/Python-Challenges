"""Responses are ASGI apps: `await response(scope, receive, send)`.

That's the trick that makes composition uniform — a handler returns something
that knows how to send itself, and the router just awaits it.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterable, Iterable
from typing import Any

from .background import BackgroundTask
from .types import Receive, Scope, Send


class Response:
    media_type: str | None = None
    charset = "utf-8"

    def __init__(
        self,
        content: Any = b"",
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        self.status_code = status_code
        self.media_type = media_type or self.media_type
        self.background = background
        self.body = self.render(content)
        self.raw_headers = self._build_headers(headers or {})

    def render(self, content: Any) -> bytes:
        if content is None:
            return b""
        if isinstance(content, bytes):
            return content
        return str(content).encode(self.charset)

    def _build_headers(self, headers: dict[str, str]) -> list[tuple[bytes, bytes]]:
        raw = [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()]
        keys = {k for k, _ in raw}
        if b"content-length" not in keys and not isinstance(self, StreamingResponse):
            raw.append((b"content-length", str(len(self.body)).encode()))
        if b"content-type" not in keys and self.media_type:
            ct = self.media_type
            if ct.startswith("text/"):
                ct += f"; charset={self.charset}"
            raw.append((b"content-type", ct.encode("latin-1")))
        return raw

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await send(
            {"type": "http.response.start", "status": self.status_code, "headers": self.raw_headers}
        )
        await send({"type": "http.response.body", "body": self.body, "more_body": False})
        if self.background is not None:
            await self.background()


class PlainTextResponse(Response):
    media_type = "text/plain"


class HTMLResponse(Response):
    media_type = "text/html"


class JSONResponse(Response):
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        return json.dumps(content, separators=(",", ":")).encode("utf-8")


class StreamingResponse(Response):
    """Send chunks as they're produced. Each `send` awaits the server's transport,
    so a slow client naturally slows the generator: backpressure for free."""

    def __init__(
        self,
        content: AsyncIterable[bytes | str] | Iterable[bytes | str],
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        self.iterator = content
        super().__init__(b"", status_code, headers, media_type, background)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await send(
            {"type": "http.response.start", "status": self.status_code, "headers": self.raw_headers}
        )
        if isinstance(self.iterator, AsyncIterable):
            async for chunk in self.iterator:
                await self._send_chunk(send, chunk)
        else:
            for chunk in self.iterator:
                await self._send_chunk(send, chunk)
        await send({"type": "http.response.body", "body": b"", "more_body": False})
        if self.background is not None:
            await self.background()

    async def _send_chunk(self, send: Send, chunk: bytes | str) -> None:
        data = chunk if isinstance(chunk, bytes) else chunk.encode(self.charset)
        await send({"type": "http.response.body", "body": data, "more_body": True})

"""Testing = drive the app through httpx's ASGI transport, plus run lifespan by hand.

httpx's `ASGITransport` does *not* run lifespan (neither does Starlette's TestClient
unless used as a context manager), so `lifespan()` here is a small manual driver.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from .types import ASGIApp, Message, Scope


async def _run(
    app: ASGIApp,
    scope: Scope,
    inbox: asyncio.Queue[Message],
    outbox: asyncio.Queue[Message],
) -> None:
    await app(scope, inbox.get, outbox.put)


def client(app: ASGIApp, base_url: str = "http://test", root_path: str = "") -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, root_path=root_path)
    return httpx.AsyncClient(transport=transport, base_url=base_url)


@asynccontextmanager
async def lifespan(app: ASGIApp) -> AsyncIterator[None]:
    inbox: asyncio.Queue[Message] = asyncio.Queue()
    outbox: asyncio.Queue[Message] = asyncio.Queue()
    scope: Scope = {"type": "lifespan", "asgi": {"version": "3.0"}}
    task = asyncio.create_task(_run(app, scope, inbox, outbox))
    await inbox.put({"type": "lifespan.startup"})
    msg = await outbox.get()
    if msg["type"] != "lifespan.startup.complete":
        await task
        raise RuntimeError(msg)
    try:
        yield
    finally:
        await inbox.put({"type": "lifespan.shutdown"})
        await outbox.get()
        await task


class WebSocketTester:
    """Drive a websocket route directly with queues — enough to test echo servers."""

    def __init__(self, app: ASGIApp, path: str) -> None:
        self.app = app
        self.path = path
        self.to_app: asyncio.Queue[Message] = asyncio.Queue()
        self.from_app: asyncio.Queue[Message] = asyncio.Queue()
        self.task: asyncio.Task[None] | None = None

    async def __aenter__(self) -> WebSocketTester:
        scope: Scope = {"type": "websocket", "path": self.path, "headers": [], "query_string": b""}
        self.task = asyncio.create_task(_run(self.app, scope, self.to_app, self.from_app))
        await self.to_app.put({"type": "websocket.connect"})
        msg = await self.from_app.get()
        assert msg["type"] == "websocket.accept", msg
        return self

    async def send_text(self, text: str) -> None:
        await self.to_app.put({"type": "websocket.receive", "text": text})

    async def receive_text(self) -> str:
        msg = await self.from_app.get()
        assert msg["type"] == "websocket.send", msg
        return str(msg["text"])

    async def __aexit__(self, *exc: object) -> None:
        await self.to_app.put({"type": "websocket.disconnect", "code": 1000})
        assert self.task is not None
        await self.task

"""T3 w1 — a complete ASGI app with no framework.  uvicorn 01_asgi_by_hand:app --port 8000

    curl localhost:8000/            -> hello
    curl localhost:8000/items/42    -> path param
    curl -d 'hi' localhost:8000/echo
    curl -N localhost:8000/stream   -> chunked
"""
from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from typing import Any

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]

STATE: dict[str, Any] = {}


async def read_body(receive: Receive) -> bytes:
    chunks = []
    while True:
        msg = await receive()
        if msg["type"] == "http.disconnect":
            raise ConnectionError
        chunks.append(msg.get("body", b""))
        if not msg.get("more_body", False):
            return b"".join(chunks)


async def send_response(send: Send, status: int, body: bytes, content_type: bytes = b"text/plain") -> None:
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", content_type), (b"content-length", str(len(body)).encode())]})
    await send({"type": "http.response.body", "body": body})


async def stream(send: Send) -> None:
    await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"text/plain")]})
    for i in range(5):
        await send({"type": "http.response.body", "body": f"chunk {i}\n".encode(), "more_body": True})
        await asyncio.sleep(0.3)           # send() awaits the server: backpressure is free
    await send({"type": "http.response.body", "body": b"", "more_body": False})


ROUTES: list[tuple[str, re.Pattern[str]]] = [
    ("home", re.compile(r"^/$")),
    ("item", re.compile(r"^/items/(?P<id>\d+)$")),
    ("echo", re.compile(r"^/echo$")),
    ("stream", re.compile(r"^/stream$")),
]


async def http(scope: Scope, receive: Receive, send: Send) -> None:
    for name, pat in ROUTES:
        if m := pat.match(scope["path"]):
            break
    else:
        return await send_response(send, 404, b"not found")
    if name == "home":
        await send_response(send, 200, f"hello (started at {STATE['started']})\n".encode())
    elif name == "item":
        await send_response(send, 200, json.dumps({"id": int(m["id"])}).encode(), b"application/json")
    elif name == "echo":
        if scope["method"] != "POST":
            return await send_response(send, 405, b"POST only")
        await send_response(send, 200, await read_body(receive))
    elif name == "stream":
        await stream(send)


async def lifespan(scope: Scope, receive: Receive, send: Send) -> None:
    while True:
        msg = await receive()
        if msg["type"] == "lifespan.startup":
            STATE["started"] = asyncio.get_running_loop().time()
            await send({"type": "lifespan.startup.complete"})
        elif msg["type"] == "lifespan.shutdown":
            STATE.clear()
            await send({"type": "lifespan.shutdown.complete"})
            return


async def app(scope: Scope, receive: Receive, send: Send) -> None:
    if scope["type"] == "lifespan":
        await lifespan(scope, receive, send)
    elif scope["type"] == "http":
        await http(scope, receive, send)
    else:
        raise NotImplementedError(scope["type"])


if __name__ == "__main__":
    # drive it without a server: this is exactly what a TestClient does
    async def main() -> None:
        sent: list[dict[str, Any]] = []

        async def receive() -> dict[str, Any]:
            return {"type": "http.request", "body": b"ping", "more_body": False}

        async def send(msg: dict[str, Any]) -> None:
            sent.append(msg)

        STATE["started"] = 0
        await app({"type": "http", "method": "POST", "path": "/echo", "headers": []}, receive, send)
        print(sent)

    asyncio.run(main())

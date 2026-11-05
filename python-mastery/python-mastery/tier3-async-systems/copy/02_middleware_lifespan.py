"""T3 w2 — pure-ASGI middleware, a dispatch-style adapter, background tasks, tested via httpx.
Run: python 02_middleware_lifespan.py   (uses httpx.ASGITransport — no server needed)
"""
from __future__ import annotations

import asyncio
import contextvars
import logging
import time
import uuid
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

import httpx

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        return True


log = logging.getLogger("app")
logging.basicConfig(level=logging.INFO, format="%(request_id)s %(message)s")
for h in logging.getLogger().handlers:
    h.addFilter(RequestIdFilter())          # on the HANDLER: applies to every logger (httpx logs too)


# --- 1. pure-ASGI middleware: wrap send to add a header + time the request -------------------------
class TimingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        t0 = time.perf_counter()

        async def send_wrapper(msg: Message) -> None:
            if msg["type"] == "http.response.start":
                ms = (time.perf_counter() - t0) * 1000
                msg["headers"] = [*msg.get("headers", []), (b"x-elapsed-ms", f"{ms:.2f}".encode())]
            await send(msg)

        await self.app(scope, receive, send_wrapper)


class RequestIdMiddleware:
    """Sets a contextvar for the whole downstream call — works because we're the same task."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        rid = dict(scope["headers"]).get(b"x-request-id", uuid.uuid4().hex[:8].encode()).decode()
        token = request_id.set(rid)
        try:
            await self.app(scope, receive, send)
        finally:
            request_id.reset(token)


class ErrorMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        started = False

        async def send_wrapper(msg: Message) -> None:
            nonlocal started
            started = started or msg["type"] == "http.response.start"
            await send(msg)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            log.exception("unhandled")
            if not started:                  # can't change status after headers went out
                body = b"internal error"
                await send({"type": "http.response.start", "status": 500, "headers": [(b"content-length", str(len(body)).encode())]})
                await send({"type": "http.response.body", "body": body})
            else:
                raise


# --- 2. a dispatch(request, call_next) adapter — and why it's leaky ---------------------------------------
class DispatchMiddleware:
    """Starlette-style convenience. The inner app runs in a *separate task*, so contextvars set
    inside `dispatch` after call_next won't be seen by it, and streaming is buffered through a queue."""

    def __init__(self, app: ASGIApp, dispatch: Callable[[Scope, Callable[[], Awaitable[Message]]], Awaitable[Message]]) -> None:
        self.app, self.dispatch = app, dispatch

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        queue: asyncio.Queue[Message] = asyncio.Queue()

        async def call_next() -> Message:
            async def inner() -> None:
                await self.app(scope, receive, queue.put)

            task = asyncio.create_task(inner())
            # If the inner app raises *before* sending response.start, nothing ever lands in
            # the queue and `await queue.get()` hangs forever. This exact bug was Starlette
            # #1022; the fix is to wait on both the task and the queue.
            getter = asyncio.ensure_future(queue.get())
            done, _ = await asyncio.wait({task, getter}, return_when=asyncio.FIRST_COMPLETED)
            if task in done and getter not in done:
                getter.cancel()
                task.result()  # re-raises the inner exception
            start = await getter
            body = b""
            while True:
                msg = await queue.get()
                body += msg.get("body", b"")
                if not msg.get("more_body"):
                    break
            await task
            return {**start, "body": body}

        resp = await self.dispatch(scope, call_next)
        await send({"type": "http.response.start", "status": resp["status"], "headers": resp["headers"]})
        await send({"type": "http.response.body", "body": resp["body"]})


# --- 3. the app, with lifespan and a background task -----------------------------------------------------
BACKGROUND: set[asyncio.Task[None]] = set()
STATE: dict[str, Any] = {}


async def app(scope: Scope, receive: Receive, send: Send) -> None:
    if scope["type"] == "lifespan":
        while True:
            msg = await receive()
            if msg["type"] == "lifespan.startup":
                STATE["db"] = "connected"
                await send({"type": "lifespan.startup.complete"})
            else:
                await asyncio.gather(*BACKGROUND, return_exceptions=True)   # drain on shutdown
                await send({"type": "lifespan.shutdown.complete"})
                return
    path = scope["path"]
    if path == "/boom":
        raise RuntimeError("boom")
    if path == "/work":
        async def later() -> None:
            await asyncio.sleep(0.05)
            log.info("background job done (contextvar still visible: task copied the context)")
        t = asyncio.create_task(later())
        BACKGROUND.add(t)
        t.add_done_callback(BACKGROUND.discard)
    log.info("handling %s", path)
    body = f"ok {path} db={STATE.get('db')}".encode()
    await send({"type": "http.response.start", "status": 200, "headers": [(b"content-length", str(len(body)).encode())]})
    await send({"type": "http.response.body", "body": body})


async def upper_dispatch(scope: Scope, call_next: Callable[[], Awaitable[Message]]) -> Message:
    resp = await call_next()
    return {**resp, "body": resp["body"].upper()}


stack: ASGIApp = ErrorMiddleware(RequestIdMiddleware(TimingMiddleware(DispatchMiddleware(app, upper_dispatch))))


async def main() -> None:
    STATE["db"] = "connected"               # ASGITransport doesn't run lifespan; call it yourself in tests
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=stack), base_url="http://t") as c:
        r = await c.get("/hello", headers={"x-request-id": "abc123"})
        print(r.status_code, r.text, r.headers["x-elapsed-ms"])
        r = await c.get("/boom")
        print(r.status_code, r.text)
        r = await c.get("/work")
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.run(main())

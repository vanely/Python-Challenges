"""Pure-ASGI middleware: an app that wraps an app.

Every middleware is `class M: __init__(self, app, **opts)` + `async __call__(scope, receive, send)`.
No task-spawning, no memory channels — so contextvars set here are visible to the
handler, and streaming responses stream. That's the design lesson of Starlette's
`BaseHTTPMiddleware` issue history, applied.
"""

from __future__ import annotations

import contextvars
import logging
import time
import traceback
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from .exceptions import HTTPException
from .requests import Request
from .responses import JSONResponse, PlainTextResponse, Response
from .types import ASGIApp, Message, Receive, Scope, Send

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
log = logging.getLogger("microasgi")


class Middleware:
    """Declarative wrapper so `App(middleware=[Middleware(Cls, opt=1)])` can build the stack."""

    def __init__(self, cls: type[Any], **options: Any) -> None:
        self.cls = cls
        self.options = options

    def wrap(self, app: ASGIApp) -> ASGIApp:
        return self.cls(app, **self.options)  # type: ignore[no-any-return]


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp, header: str = "x-request-id") -> None:
        self.app = app
        self.header = header.encode("latin-1")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        rid = next((v.decode() for k, v in scope["headers"] if k == self.header), None)
        rid = rid or uuid.uuid4().hex[:12]
        token = request_id_var.set(rid)
        scope.setdefault("state", {})["request_id"] = rid

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [*message.get("headers", []), (self.header, rid.encode())]
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            request_id_var.reset(token)


class TimingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start = time.perf_counter()
        status = 0

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                ms = (time.perf_counter() - start) * 1000
                message["headers"] = [
                    *message.get("headers", []),
                    (b"server-timing", f"app;dur={ms:.1f}".encode()),
                ]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            log.info(
                "%s %s -> %s %.1fms rid=%s",
                scope["method"],
                scope["path"],
                status,
                (time.perf_counter() - start) * 1000,
                request_id_var.get(),
            )


ExcHandler = Callable[[Request, Exception], Awaitable[Response]]


class ExceptionMiddleware:
    """Turns `HTTPException` (and registered types) into responses. Sits *inside* the
    user middleware so those middlewares see the real status code."""

    def __init__(self, app: ASGIApp, handlers: dict[type[Exception], ExcHandler] | None = None):
        self.app = app
        self.handlers: dict[type[Exception], ExcHandler] = {HTTPException: _http_exc_handler}
        self.handlers.update(handlers or {})

    def _lookup(self, exc: Exception) -> ExcHandler | None:
        for cls in type(exc).__mro__:
            if cls in self.handlers:
                return self.handlers[cls]
        return None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def sender(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, sender)
        except Exception as exc:
            handler = self._lookup(exc)
            if handler is None or started:
                raise
            response = await handler(Request(scope, receive), exc)
            await response(scope, receive, send)


async def _http_exc_handler(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, HTTPException)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


class ServerErrorMiddleware:
    """Outermost. Anything that escapes becomes a 500 (with traceback in debug),
    and is re-raised so the server logs it."""

    def __init__(self, app: ASGIApp, debug: bool = False) -> None:
        self.app = app
        self.debug = debug

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def sender(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, sender)
        except Exception:
            if not started:
                body = traceback.format_exc() if self.debug else "Internal Server Error"
                await PlainTextResponse(body, 500)(scope, receive, send)
            raise


CallNext = Callable[[Request], Awaitable[Response]]


class DispatchMiddleware:
    """`dispatch(request, call_next)` convenience — the shape people like.

    Implemented *without* spawning a task: `call_next` runs the inner app with a
    capturing `send`, so contextvars propagate. The cost, which you should be able
    to state after reading Starlette's version: the inner response is fully
    buffered, so it's wrong for streaming endpoints. Use pure-ASGI for those.
    """

    def __init__(self, app: ASGIApp, dispatch: Callable[[Request, CallNext], Awaitable[Response]]):
        self.app = app
        self.dispatch = dispatch

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def call_next(request: Request) -> Response:
            status = 200
            headers: dict[str, str] = {}
            chunks: list[bytes] = []

            async def capture(message: Message) -> None:
                nonlocal status
                if message["type"] == "http.response.start":
                    status = message["status"]
                    for k, v in message.get("headers", []):
                        headers[k.decode("latin-1")] = v.decode("latin-1")
                elif message["type"] == "http.response.body":
                    chunks.append(message.get("body", b""))

            await self.app(scope, receive, capture)
            headers.pop("content-length", None)
            return Response(b"".join(chunks), status, headers)

        response = await self.dispatch(Request(scope, receive), call_next)
        await response(scope, receive, send)

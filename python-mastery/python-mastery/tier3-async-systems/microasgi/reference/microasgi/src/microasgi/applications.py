"""App = lifespan handling + a middleware stack around a Router.

Stack (outer -> inner), built lazily on first call like Starlette:
    ServerErrorMiddleware -> user middleware... -> ExceptionMiddleware -> Router
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

from .middleware import ExceptionMiddleware, ExcHandler, Middleware, ServerErrorMiddleware
from .routing import Handler, Mount, Route, Router, WebSocketRoute, WSHandler
from .types import ASGIApp, Receive, Scope, Send

Lifespan = Callable[["App"], AbstractAsyncContextManager[None]]


@asynccontextmanager
async def _noop_lifespan(app: App) -> AsyncIterator[None]:
    yield


class App:
    def __init__(
        self,
        routes: list[Route | WebSocketRoute | Mount] | None = None,
        middleware: list[Middleware] | None = None,
        exception_handlers: dict[type[Exception], ExcHandler] | None = None,
        lifespan: Lifespan | None = None,
        debug: bool = False,
    ) -> None:
        self.router = Router(routes)
        self.user_middleware = list(middleware or [])
        self.exception_handlers = dict(exception_handlers or {})
        self.lifespan = lifespan or _noop_lifespan
        self.debug = debug
        self.state: dict[str, Any] = {}
        self._stack: ASGIApp | None = None

    # --- decorators -------------------------------------------------------
    def route(self, path: str, methods: list[str] | None = None) -> Callable[[Handler], Handler]:
        def decorator(fn: Handler) -> Handler:
            self.router.routes.append(Route(path, fn, methods))
            self._stack = None
            return fn

        return decorator

    def get(self, path: str) -> Callable[[Handler], Handler]:
        return self.route(path, ["GET"])

    def post(self, path: str) -> Callable[[Handler], Handler]:
        return self.route(path, ["POST"])

    def websocket(self, path: str) -> Callable[[WSHandler], WSHandler]:
        def decorator(fn: WSHandler) -> WSHandler:
            self.router.routes.append(WebSocketRoute(path, fn))
            self._stack = None
            return fn

        return decorator

    def add_middleware(self, cls: type[Any], **options: Any) -> None:
        self.user_middleware.insert(0, Middleware(cls, **options))
        self._stack = None

    # --- stack ------------------------------------------------------------
    def build_stack(self) -> ASGIApp:
        app: ASGIApp = ExceptionMiddleware(self.router, self.exception_handlers)
        for mw in reversed(self.user_middleware):
            app = mw.wrap(app)
        return ServerErrorMiddleware(app, debug=self.debug)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope["app"] = self
        if scope["type"] == "lifespan":
            await self._handle_lifespan(scope, receive, send)
            return
        if self._stack is None:
            self._stack = self.build_stack()
        await self._stack(scope, receive, send)

    async def _handle_lifespan(self, scope: Scope, receive: Receive, send: Send) -> None:
        msg = await receive()
        assert msg["type"] == "lifespan.startup"
        try:
            async with self.lifespan(self):
                await send({"type": "lifespan.startup.complete"})
                msg = await receive()
                assert msg["type"] == "lifespan.shutdown"
        except Exception as exc:
            # If startup failed, the server should refuse to start; if shutdown
            # failed, report it — the server exits either way.
            phase = "startup" if msg["type"] == "lifespan.startup" else "shutdown"
            await send({"type": f"lifespan.{phase}.failed", "message": repr(exc)})
            raise
        await send({"type": "lifespan.shutdown.complete"})

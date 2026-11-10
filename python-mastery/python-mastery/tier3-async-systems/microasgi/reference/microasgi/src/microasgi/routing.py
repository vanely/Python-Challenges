"""Routing: `/items/{id:int}` -> compiled regex + convertors.

Same design as Starlette's `compile_path`. A router is itself an ASGI app, so
you can mount one inside another.
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Awaitable, Callable
from typing import Any

from .exceptions import HTTPException
from .requests import Request
from .responses import PlainTextResponse, Response
from .types import ASGIApp, Receive, Scope, Send
from .websockets import WebSocket

Handler = Callable[..., Awaitable[Response]]
WSHandler = Callable[[WebSocket], Awaitable[None]]

_CONVERTORS: dict[str, tuple[str, Callable[[str], Any]]] = {
    "str": (r"[^/]+", str),
    "int": (r"[0-9]+", int),
    "float": (r"[0-9]+(\.[0-9]+)?", float),
    "path": (r".*", str),
}
_PARAM_RE = re.compile(r"{([a-zA-Z_][a-zA-Z0-9_]*)(?::([a-zA-Z_]+))?}")


def compile_path(path: str) -> tuple[re.Pattern[str], dict[str, Callable[[str], Any]]]:
    regex = "^"
    idx = 0
    convertors: dict[str, Callable[[str], Any]] = {}
    for m in _PARAM_RE.finditer(path):
        name, conv = m.group(1), m.group(2) or "str"
        pattern, fn = _CONVERTORS[conv]
        regex += re.escape(path[idx : m.start()]) + f"(?P<{name}>{pattern})"
        convertors[name] = fn
        idx = m.end()
    regex += re.escape(path[idx:]) + "$"
    return re.compile(regex), convertors


def get_route_path(scope: Scope) -> str:
    """The part of `path` this app routes on. ASGI `path` is the full request target and
    is never rewritten; `root_path` is the prefix the app is mounted under (by a `Mount`
    or `uvicorn --root-path`). Same as Starlette's `get_route_path`."""
    path: str = scope["path"]
    root: str = scope.get("root_path", "")
    if root and path.startswith(root) and path[len(root) : len(root) + 1] in ("", "/"):
        return path[len(root) :] or "/"
    return path


class Route:
    def __init__(self, path: str, endpoint: Handler, methods: list[str] | None = None) -> None:
        self.path = path
        self.endpoint = endpoint
        self.methods = {m.upper() for m in (methods or ["GET"])}
        if "GET" in self.methods:
            self.methods.add("HEAD")
        self.regex, self.convertors = compile_path(path)
        params = inspect.signature(endpoint).parameters
        self._wants_request = "request" in params
        self._param_names = [p for p in params if p != "request"]

    def match(self, scope: Scope) -> tuple[bool, bool, dict[str, Any]]:
        """Returns (path_matched, method_allowed, path_params)."""
        if scope["type"] != "http":
            return False, False, {}
        m = self.regex.match(get_route_path(scope))
        if not m:
            return False, False, {}
        params = {k: self.convertors[k](v) for k, v in m.groupdict().items()}
        return True, scope["method"] in self.methods, params

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope, receive)
        kwargs = {k: v for k, v in scope["path_params"].items() if k in self._param_names}
        if self._wants_request:
            response = await self.endpoint(request=request, **kwargs)
        else:
            response = await self.endpoint(**kwargs)
        await response(scope, receive, send)


class WebSocketRoute:
    def __init__(self, path: str, endpoint: WSHandler) -> None:
        self.path = path
        self.endpoint = endpoint
        self.regex, self.convertors = compile_path(path)

    def match(self, scope: Scope) -> tuple[bool, bool, dict[str, Any]]:
        if scope["type"] != "websocket":
            return False, False, {}
        m = self.regex.match(get_route_path(scope))
        if not m:
            return False, False, {}
        return True, True, {k: self.convertors[k](v) for k, v in m.groupdict().items()}

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.endpoint(WebSocket(scope, receive, send))


class Mount:
    """Delegate everything under a prefix to another ASGI app (a sub-Router, a static
    file server, a whole other framework)."""

    def __init__(self, path: str, app: ASGIApp) -> None:
        self.path = path.rstrip("/")
        self.app = app
        self.regex = re.compile("^" + re.escape(self.path) + r"(/.*)?$")

    def match(self, scope: Scope) -> tuple[bool, bool, dict[str, Any]]:
        if scope["type"] not in ("http", "websocket"):
            return False, False, {}
        m = self.regex.match(get_route_path(scope))
        return (True, True, {}) if m else (False, False, {})

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        child = dict(scope)
        child["root_path"] = scope.get("root_path", "") + self.path   # `path` stays the full target
        await self.app(child, receive, send)


class Router:
    def __init__(self, routes: list[Route | WebSocketRoute | Mount] | None = None) -> None:
        self.routes: list[Route | WebSocketRoute | Mount] = list(routes or [])

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            # Bare routers don't own lifespan; the App does.
            return
        partial: Route | WebSocketRoute | Mount | None = None
        for route in self.routes:
            matched, allowed, params = route.match(scope)
            if matched and allowed:
                scope["path_params"] = {**scope.get("path_params", {}), **params}
                await route.handle(scope, receive, send)
                return
            if matched:
                partial = route
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1000})
            return
        if partial is not None:
            raise HTTPException(405)
        raise HTTPException(404)


async def not_found(request: Request) -> Response:  # pragma: no cover - example
    return PlainTextResponse("Not Found", 404)

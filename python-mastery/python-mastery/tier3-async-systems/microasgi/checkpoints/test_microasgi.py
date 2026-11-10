from __future__ import annotations

import asyncio
import contextvars
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest

from microasgi import (
    App,
    BackgroundTask,
    DispatchMiddleware,
    HTTPException,
    JSONResponse,
    Middleware,
    Mount,
    PlainTextResponse,
    Request,
    RequestIdMiddleware,
    Response,
    Route,
    Router,
    StreamingResponse,
    TimingMiddleware,
    WebSocket,
    WebSocketDisconnect,
    request_id_var,
)
from microasgi.middleware import CallNext
from microasgi.routing import compile_path, get_route_path
from microasgi.testclient import WebSocketTester, client, lifespan


def test_compile_path() -> None:
    regex, conv = compile_path("/users/{uid:int}/files/{rest:path}")
    m = regex.match("/users/42/files/a/b/c.txt")
    assert m and conv["uid"](m["uid"]) == 42 and m["rest"] == "a/b/c.txt"
    assert regex.match("/users/x/files/y") is None


async def test_routing_and_params() -> None:
    app = App()

    @app.get("/items/{item_id:int}")
    async def item(item_id: int) -> Response:
        return JSONResponse({"id": item_id, "double": item_id * 2})

    async with client(app) as c:
        r = await c.get("/items/21")
        assert r.status_code == 200 and r.json() == {"id": 21, "double": 42}
        assert r.headers["content-type"] == "application/json"
        assert (await c.get("/items/abc")).status_code == 404
        assert (await c.post("/items/21")).status_code == 405
        assert (await c.head("/items/21")).status_code == 200


async def test_body_json_and_query() -> None:
    app = App()

    @app.post("/echo")
    async def echo(request: Request) -> Response:
        data = await request.json()
        again = await request.body()  # cached, does not hang
        assert again
        return JSONResponse(
            {"got": data, "q": request.query_params, "ua": request.headers["user-agent"]}
        )

    async with client(app) as c:
        r = await c.post("/echo?x=1&y=two", json={"a": 1}, headers={"User-Agent": "t"})
        assert r.json() == {"got": {"a": 1}, "q": {"x": "1", "y": "two"}, "ua": "t"}


async def test_http_exception_and_custom_handler() -> None:
    class Teapot(Exception):
        pass

    async def teapot_handler(request: Request, exc: Exception) -> Response:
        return PlainTextResponse("short and stout", 418)

    app = App(exception_handlers={Teapot: teapot_handler})

    @app.get("/nope")
    async def nope() -> Response:
        raise HTTPException(403, "no")

    @app.get("/tea")
    async def tea() -> Response:
        raise Teapot

    @app.get("/boom")
    async def boom() -> Response:
        raise ValueError("unhandled")

    async with client(app) as c:
        assert (await c.get("/nope")).json() == {"detail": "no"}
        r = await c.get("/tea")
        assert r.status_code == 418 and r.text == "short and stout"
        with pytest.raises(ValueError):
            # ServerErrorMiddleware sends a 500 then re-raises; ASGITransport surfaces the raise.
            await c.get("/boom")


async def test_contextvars_propagate_through_pure_asgi_middleware() -> None:
    seen: dict[str, str] = {}
    app = App(middleware=[Middleware(RequestIdMiddleware), Middleware(TimingMiddleware)])

    @app.get("/")
    async def index() -> Response:
        seen["in_handler"] = request_id_var.get()
        return PlainTextResponse("ok")

    async with client(app) as c:
        r = await c.get("/", headers={"x-request-id": "abc123"})
        assert seen["in_handler"] == "abc123"
        assert r.headers["x-request-id"] == "abc123"
        assert r.headers["server-timing"].startswith("app;dur=")
        assert request_id_var.get() == "-"  # reset after the request


async def test_dispatch_middleware_sees_handler_contextvars() -> None:
    marker: contextvars.ContextVar[str] = contextvars.ContextVar("marker", default="unset")
    observed: list[str] = []

    async def dispatch(request: Request, call_next: CallNext) -> Response:
        marker.set("from-middleware")
        response = await call_next(request)
        observed.append(marker.get())
        response.raw_headers.append((b"x-seen", b"1"))
        return response

    app = App(middleware=[Middleware(DispatchMiddleware, dispatch=dispatch)])

    @app.get("/")
    async def index() -> Response:
        observed.append(marker.get())
        marker.set("from-handler")
        return PlainTextResponse("ok")

    async with client(app) as c:
        r = await c.get("/")
        assert r.text == "ok" and r.headers["x-seen"] == "1"
        # No task boundary: middleware value reaches handler, handler's set reaches middleware.
        assert observed == ["from-middleware", "from-handler"]


async def test_streaming_and_background() -> None:
    log: list[str] = []
    app = App()

    @app.get("/stream")
    async def stream() -> Response:
        async def gen() -> AsyncIterator[str]:
            for i in range(3):
                yield f"chunk{i};"
                await asyncio.sleep(0)

        return StreamingResponse(
            gen(), media_type="text/plain", background=BackgroundTask(log.append, "done")
        )

    async with client(app) as c:
        r = await c.get("/stream")
        assert r.text == "chunk0;chunk1;chunk2;"
        assert "content-length" not in r.headers
    assert log == ["done"]


async def test_lifespan_runs_and_state_is_shared() -> None:
    events: list[str] = []

    @asynccontextmanager
    async def ls(app: App) -> AsyncIterator[None]:
        events.append("up")
        app.state["answer"] = 42
        yield
        events.append("down")

    app = App(lifespan=ls)

    @app.get("/")
    async def index(request: Request) -> Response:
        return JSONResponse({"answer": request.scope["app"].state["answer"]})

    async with lifespan(app), client(app) as c:
        assert (await c.get("/")).json() == {"answer": 42}
        assert events == ["up"]
    assert events == ["up", "down"]


async def test_lifespan_startup_failure_is_reported() -> None:
    @asynccontextmanager
    async def ls(app: App) -> AsyncIterator[None]:
        raise RuntimeError("db down")
        yield  # pragma: no cover

    with pytest.raises(RuntimeError):
        async with lifespan(App(lifespan=ls)):
            pass  # pragma: no cover


async def test_mount_and_nested_router() -> None:
    async def sub_index(request: Request) -> Response:
        scope = request.scope
        return PlainTextResponse(f"sub:{get_route_path(scope)}:{request.path}:{scope['root_path']}")

    sub = Router([Route("/", sub_index), Route("/x", sub_index)])
    app = App(routes=[Mount("/api", sub)])

    async with client(app) as c:
        # ASGI: `path` stays the full target, Mount only extends `root_path`
        assert (await c.get("/api")).text == "sub:/:/api:/api"
        assert (await c.get("/api/x")).text == "sub:/x:/api/x:/api"
        assert (await c.get("/apix")).status_code == 404
        assert (await c.get("/other")).status_code == 404

    async with client(app, root_path="/pfx") as c:  # e.g. `uvicorn --root-path /pfx`
        assert (await c.get("/pfx/api/x")).text == "sub:/x:/pfx/api/x:/pfx/api"


async def test_server_root_path() -> None:
    app = App()

    @app.get("/items/{item_id:int}")
    async def item(item_id: int) -> Response:
        return JSONResponse({"id": item_id})

    async with client(app, root_path="/pfx") as c:
        assert (await c.get("/pfx/items/1")).json() == {"id": 1}


async def test_websocket_echo() -> None:
    app = App()

    @app.websocket("/ws")
    async def ws(sock: WebSocket) -> None:
        await sock.accept()
        try:
            while True:
                await sock.send_text((await sock.receive_text()).upper())
        except WebSocketDisconnect:
            pass

    async with WebSocketTester(app, "/ws") as t:
        await t.send_text("hi")
        assert await t.receive_text() == "HI"

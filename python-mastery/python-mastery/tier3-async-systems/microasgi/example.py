"""Run from this dir: `pip install -e .` then `uvicorn example:app --reload`."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from microasgi import (
    App,
    BackgroundTask,
    HTTPException,
    JSONResponse,
    Middleware,
    PlainTextResponse,
    Request,
    RequestIdMiddleware,
    Response,
    StreamingResponse,
    TimingMiddleware,
    WebSocket,
    WebSocketDisconnect,
    request_id_var,
)


@asynccontextmanager
async def lifespan(app: App) -> AsyncIterator[None]:
    app.state["db"] = {"items": {1: "apple", 2: "pear"}}
    print("startup")
    yield
    print("shutdown")


app = App(
    middleware=[Middleware(RequestIdMiddleware), Middleware(TimingMiddleware)],
    lifespan=lifespan,
    debug=True,
)


@app.get("/")
async def index() -> Response:
    return PlainTextResponse("hello")


@app.get("/items/{item_id:int}")
async def item(request: Request, item_id: int) -> Response:
    db = request.scope["app"].state["db"]
    if item_id not in db["items"]:
        raise HTTPException(404, f"no item {item_id}")
    return JSONResponse({"id": item_id, "name": db["items"][item_id], "rid": request_id_var.get()})


@app.post("/items")
async def create(request: Request) -> Response:
    data = await request.json()
    return JSONResponse(data, status_code=201, background=BackgroundTask(print, "created", data))


@app.get("/events")
async def events() -> Response:
    async def gen() -> AsyncIterator[str]:
        for i in range(5):
            yield f"data: {i}\n\n"
            await asyncio.sleep(0.2)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.websocket("/ws")
async def ws(sock: WebSocket) -> None:
    await sock.accept()
    try:
        while True:
            await sock.send_text(f"echo: {await sock.receive_text()}")
    except WebSocketDisconnect:
        pass

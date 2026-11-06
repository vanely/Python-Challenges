"""FastAPI app. Store opened for the app's lifetime via lifespan.

No `from __future__ import annotations` here: FastAPI evaluates route annotations against
module globals, so a stringified annotation naming anything local to `create_app` would fail.
"""

import json
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from docpipe.models import DocumentOut, SearchHit
from docpipe.store import DocumentNotFound, Store


def get_store(request: Request) -> Store:
    store: Store = request.app.state.store
    return store


StoreDep = Annotated[Store, Depends(get_store)]


def create_app(db_path: Path | str) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.store = Store(db_path)
        try:
            yield
        finally:
            app.state.store.close()

    app = FastAPI(title="docpipe", lifespan=lifespan)

    @app.exception_handler(DocumentNotFound)
    async def _nf(request: Request, exc: DocumentNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.get("/search")
    def search(
        store: StoreDep,
        q: Annotated[str, Query(min_length=1)],
        limit: Annotated[int, Query(ge=1, le=50)] = 10,
    ) -> list[SearchHit]:
        return store.search(q, limit)

    @app.get("/documents")
    def documents(store: StoreDep) -> list[DocumentOut]:
        return [_out(store, d.id) for d in store.list_documents()]

    @app.get("/documents/{doc_id}")
    def document(doc_id: int, store: StoreDep) -> DocumentOut:
        return _out(store, doc_id)

    @app.get("/export")
    def export(store: StoreDep) -> StreamingResponse:
        def lines() -> Iterator[str]:
            for row in store.iter_chunks():
                yield json.dumps(row) + "\n"

        return StreamingResponse(lines(), media_type="application/x-ndjson")

    return app


def _out(store: Store, doc_id: int) -> DocumentOut:
    d = store.get(doc_id)
    return DocumentOut(
        id=d.id,
        path=d.path,
        pages=d.pages,
        chunks=store.chunk_count(d.id),
        ingested_at=d.ingested_at,
    )

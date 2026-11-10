"""uvicorn app.main:app --reload"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.repo import NoteNotFound
from app.routes import router
from app.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # startup: open pools, warm caches
    yield
    # shutdown: close them


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)


@app.exception_handler(NoteNotFound)
async def not_found_handler(request: Request, exc: NoteNotFound) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc), "id": exc.note_id})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

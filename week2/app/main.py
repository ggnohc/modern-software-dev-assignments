from __future__ import annotations

import logging
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .db import init_db
from .logging_config import configure_logging
from .routers import action_items, notes


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run startup / shutdown work. Replaces import-time side effects.

    The two startup steps are:
      1. ``configure_logging(...)`` — install our log format and level
         before any other code emits a log line, so the rest of the
         application's startup output is consistently formatted.
      2. ``init_db()`` — create the SQLite schema if it does not yet exist.

    Both run only when the server actually starts; importing
    ``week2.app.main`` no longer has these side effects.
    """
    settings = get_settings()
    configure_logging(level=settings.log_level)
    logger.info("Application startup: initializing database schema")
    init_db()
    yield
    logger.info("Application shutdown")


def sqlite_error_handler(request: Request, exc: sqlite3.Error) -> JSONResponse:
    """Convert any unhandled ``sqlite3.Error`` into a generic 500 response.

    We deliberately do NOT include the exception message, the SQL, or any
    request body / query params in the response. The exception text could
    contain SQL fragments or schema details (small information-leak risk),
    and the request body could contain user content (privacy / log-injection
    risk). The full traceback is captured server-side via
    ``logger.exception`` so operators have what they need to debug.
    """
    # Pass ``exc`` explicitly: FastAPI's exception-handler dispatch happens
    # outside the original ``except`` block, so ``sys.exc_info()`` (what
    # ``logger.exception`` defaults to) returns ``(None, None, None)`` and
    # the traceback would silently disappear.
    logger.error(
        "Unhandled sqlite3.Error on %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500, content={"detail": "internal database error"}
    )


app = FastAPI(title="Action Item Extractor", lifespan=lifespan)
app.add_exception_handler(sqlite3.Error, sqlite_error_handler)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    html_path = Path(__file__).resolve().parents[1] / "frontend" / "index.html"
    return html_path.read_text(encoding="utf-8")


app.include_router(notes.router)
app.include_router(action_items.router)


static_dir = Path(__file__).resolve().parents[1] / "frontend"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

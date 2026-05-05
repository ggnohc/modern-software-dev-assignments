"""Pydantic request and response models for the API.

These types define the formal contract between the service and its clients.
Routers receive request models (auto-validated by FastAPI) and return
response models (auto-serialized by FastAPI). Storage-layer types
(``sqlite3.Row``, etc.) must not leak into this module — schemas describe
the API surface, not the database.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CreateNoteRequest(BaseModel):
    """Body of POST /notes.

    Whitespace-only content is rejected at parse time via
    ``str_strip_whitespace=True`` combined with ``min_length=1``.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    content: str = Field(..., min_length=1, description="Free-form note text.")


class NoteResponse(BaseModel):
    """Single note as returned by the API.

    Fields mirror the ``notes`` table columns we expose. Extra columns on
    the row (if any) are dropped during serialization, so the API surface
    is decoupled from the schema of the underlying table.
    """

    id: int
    content: str
    created_at: str

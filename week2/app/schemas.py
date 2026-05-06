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


class ExtractRequest(BaseModel):
    """Body of POST /action-items/extract.

    ``text`` is stripped and required to be non-empty. ``save_note`` is a
    typed bool (no more truthy-coercion of arbitrary strings).
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(..., min_length=1, description="Free-form text to extract from.")
    save_note: bool = Field(False, description="If true, persist `text` as a note before extracting.")


class ExtractedItem(BaseModel):
    """One extracted action item, paired with its persisted database id."""

    id: int
    text: str


class ExtractResponse(BaseModel):
    """Response of POST /action-items/extract.

    ``note_id`` is null when the caller did not request to persist the note.
    """

    note_id: int | None = None
    items: list[ExtractedItem]


class ActionItemResponse(BaseModel):
    """Single action item as returned by the API.

    ``done`` is exposed as a real bool. SQLite stores it as 0/1 in an
    ``INTEGER`` column; Pydantic v2 coerces those to ``False``/``True``
    automatically, so the manual ``bool(row["done"])`` cast is no longer
    needed in the router.
    """

    id: int
    note_id: int | None = None
    text: str
    done: bool
    created_at: str


class MarkDoneRequest(BaseModel):
    """Body of POST /action-items/{id}/done.

    The body is optional in practice; when omitted, FastAPI parses an empty
    object and ``done`` defaults to True (the historical behavior).
    """

    done: bool = True


class MarkDoneResponse(BaseModel):
    """Response of POST /action-items/{id}/done.

    Added for symmetry with the other endpoints' typed responses; the prompt
    listed only five new models, but having a model here keeps the OpenAPI
    docs and serialization story consistent.
    """

    id: int
    done: bool

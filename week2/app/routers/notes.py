from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import db
from ..schemas import CreateNoteRequest, NoteResponse


router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("", response_model=NoteResponse)
def create_note(payload: CreateNoteRequest) -> NoteResponse:
    note_id = db.insert_note(payload.content)
    note = db.get_note(note_id)
    return NoteResponse(**dict(note))


@router.get("/{note_id}", response_model=NoteResponse)
def get_single_note(note_id: int) -> NoteResponse:
    row = db.get_note(note_id)
    if row is None:
        raise HTTPException(status_code=404, detail="note not found")
    return NoteResponse(**dict(row))

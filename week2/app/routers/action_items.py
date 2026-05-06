from __future__ import annotations

from typing import Callable, List

from fastapi import APIRouter

from .. import db
from ..schemas import (
    ActionItemResponse,
    ExtractRequest,
    ExtractResponse,
    ExtractedItem,
    MarkDoneRequest,
    MarkDoneResponse,
)
from ..services.extract import extract_action_items, extract_action_items_llm


router = APIRouter(prefix="/action-items", tags=["action-items"])


def _run_extract(
    payload: ExtractRequest,
    extractor: Callable[[str], List[str]],
) -> ExtractResponse:
    """Shared body for the heuristic and LLM extract endpoints.

    Both endpoints accept the same request, persist optionally, run an
    extractor over the text, and return the same response shape. The only
    thing that varies is which extractor function is called.
    """
    note_id: int | None = None
    if payload.save_note:
        note_id = db.insert_note(payload.text)

    items = extractor(payload.text)
    ids = db.insert_action_items(items, note_id=note_id)
    return ExtractResponse(
        note_id=note_id,
        items=[ExtractedItem(id=i, text=t) for i, t in zip(ids, items)],
    )


@router.post("/extract", response_model=ExtractResponse)
def extract(payload: ExtractRequest) -> ExtractResponse:
    return _run_extract(payload, extract_action_items)


@router.post("/extract-llm", response_model=ExtractResponse)
def extract_llm(payload: ExtractRequest) -> ExtractResponse:
    """Like /extract, but classifies via a local LLM (Ollama).

    On any LLM-side failure, ``extract_action_items_llm`` falls back to the
    heuristic extractor and logs a warning — the response shape is unchanged
    so clients don't need to handle that case specially.
    """
    return _run_extract(payload, extract_action_items_llm)


@router.get("", response_model=list[ActionItemResponse])
def list_all(note_id: int | None = None) -> list[ActionItemResponse]:
    rows = db.list_action_items(note_id=note_id)
    return [ActionItemResponse(**dict(r)) for r in rows]


@router.post("/{action_item_id}/done", response_model=MarkDoneResponse)
def mark_done(action_item_id: int, payload: MarkDoneRequest) -> MarkDoneResponse:
    db.mark_action_item_done(action_item_id, payload.done)
    return MarkDoneResponse(id=action_item_id, done=payload.done)

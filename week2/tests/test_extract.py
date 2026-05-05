import pytest
from ollama import ChatResponse, Message

from ..app.services.extract import (
    extract_action_items,
    extract_action_items_llm,
    ActionItemList,
    OLLAMA_MODEL,
)


def test_extract_bullets_and_checkboxes():
    text = """
    Notes from meeting:
    - [ ] Set up database
    * implement API extract endpoint
    1. Write tests
    Some narrative sentence.
    """.strip()

    items = extract_action_items(text)
    assert "Set up database" in items
    assert "implement API extract endpoint" in items
    assert "Write tests" in items


# ---------------------------------------------------------------------------
# Tests for extract_action_items_llm()
#
# Mocking strategy hint:
#   The function calls `chat` (imported at module level in
#   app.services.extract). To avoid hitting a real Ollama daemon in tests,
#   monkeypatch that symbol with a fake that returns an object whose
#   `.message.content` is a JSON string matching the ActionItemList schema:
#
#       class _FakeMsg: ...        # has .content
#       class _FakeResp: ...       # has .message
#       def fake_chat(**kwargs):   # mirrors ollama.chat signature
#           return _FakeResp(...)
#       monkeypatch.setattr("week2.app.services.extract.chat", fake_chat)
#
#   Tip: assert `kwargs["format"]` is the JSON Schema dict produced by
#   ActionItemList.model_json_schema() — that proves you wired structured
#   outputs correctly.
# ---------------------------------------------------------------------------


def _make_fake_response(content: str) -> ChatResponse:
    return ChatResponse(model="fake_model", message=Message(role="assistant", content=content))


def test_llm_extract_bullet_list(monkeypatch):
    """LLM returns a clean list for a bulleted note."""
    # TODO(tests): build a fake `chat` that returns ActionItemList JSON for
    #              a bullet-style input, then assert the parsed result.
    pytest.fail("TODO: implement test_llm_extract_bullet_list")


def test_llm_extract_keyword_prefixes(monkeypatch):
    """LLM returns items for lines starting with todo:/action:/next:."""
    # TODO(tests): exercise inputs like "todo: ship docs" / "action: ..." /
    #              "next: ..." and assert the LLM-driven function picks them up.
    pytest.fail("TODO: implement test_llm_extract_keyword_prefixes")


def test_llm_extract_empty_input_does_not_call_llm(monkeypatch):
    """Empty/whitespace input must short-circuit and never call `chat`."""

    def boom(**kwargs):
        raise AssertionError("chat() should not be called for empty input")

    monkeypatch.setattr("week2.app.services.extract.chat", boom)

    assert extract_action_items_llm("") == []
    assert extract_action_items_llm("   \n  ") == []


def test_llm_extract_no_action_items(monkeypatch):
    """Prose with no actionable content yields an empty list."""
    # TODO(tests): fake `chat` returns ActionItemList(items=[]).
    #              Assert the function returns [].
    pytest.fail("TODO: implement test_llm_extract_no_action_items")


def test_llm_extract_malformed_json(monkeypatch):
    """If the LLM returns malformed JSON, behavior matches the chosen error policy."""
    # TODO(tests): make fake `chat` return an object whose .message.content
    #              is not valid JSON for ActionItemList (e.g. "not json" or
    #              {"foo": 1}). Assert behavior matches your Step 4 decision:
    #                - re-raise: pytest.raises(pydantic.ValidationError)
    #                - fallback: result equals extract_action_items(text)
    pytest.fail("TODO: implement test_llm_extract_malformed_json")


def test_llm_extract_connection_error(monkeypatch):
    """If Ollama is unreachable, behavior matches the chosen error policy."""
    # TODO(tests): make fake `chat` raise ConnectionError (or
    #              ollama.ResponseError). Assert behavior matches your
    #              Step 4 decision (re-raise vs heuristic fallback).
    pytest.fail("TODO: implement test_llm_extract_connection_error")

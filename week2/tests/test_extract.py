import pytest, logging
from pytest import LogCaptureFixture
from unittest.mock import MagicMock
from ollama import ChatResponse, Message

from ..app.config import get_settings
from ..app.services.extract import (
    extract_action_items,
    extract_action_items_llm,
    ActionItemList,
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


# ---------------------------------------------------------------------------
# Mocking mental model (read this once; applies to every LLM test below)
#
# 1) A mock is a puppet, not a brain.
#
#    In production:
#        text -> extract_action_items_llm -> real chat() -> real LLM -> response
#        based on text
#
#    In a unit test (here):
#        text -> extract_action_items_llm -> fake chat (MagicMock) -> the
#        canned ChatResponse you configured via return_value
#
#    The mock IGNORES the input text. Whatever you set as return_value is
#    what gets returned, every call. So the input text and the items you
#    expect back are completely independent.
#
# 2) Use DISTINCT data so the test fails for the right reason.
#
#    The implementation falls back to extract_action_items() on errors. If
#    the input bullets and the fake response items overlap (e.g. both
#    contain "action item 1"), the test passes whether the LLM path ran
#    OR whether it silently fell back to the heuristic. Two scenarios,
#    same green dot — bug invisible.
#
#    Fix: pick fake-response items the heuristic CANNOT produce from the
#    input. Here the input has bullets "action item 1/2" but the fake
#    response is ["banana", "kiwi"]. If the implementation ever broke and
#    fell back to the heuristic, the result would be ["action item 1",
#    "action item 2"] and the assertion would fail. That's the test
#    being sensitive to the actual code path.
#
# 3) Two-thing checklist for every happy-path LLM test:
#      a) assert the return value matches the FAKE response (not the input)
#      b) assert chat was called once with the right kwargs (model, format,
#         options) — proves the wiring, not just the parsing.
#
# 4) Limit of unit tests: you cannot verify "the LLM correctly identifies
#    action items in arbitrary prose" here — that's a property of the real
#    LLM, not your code. That belongs in an integration test or eval, not
#    in this file.
# ---------------------------------------------------------------------------


def test_llm_extract_bullet_list(monkeypatch):
    """LLM returns a clean list for a bulleted note.

    Uses items the heuristic could not produce ("banana", "kiwi") so the
    test is sensitive to whether the LLM code path actually ran versus
    silently falling back to extract_action_items().
    """
    fake_chat = MagicMock(return_value=_make_fake_response('{"items": ["banana", "kiwi"]}'))
    monkeypatch.setattr("week2.app.services.extract.chat", fake_chat)

    result = extract_action_items_llm("* action item 1\n* action item 2")

    assert result == ["banana", "kiwi"]
    fake_chat.assert_called_once()
    kwargs = fake_chat.call_args.kwargs
    assert kwargs["messages"][1]["content"] == "* action item 1\n* action item 2"
    assert kwargs["model"] == get_settings().ollama_model
    assert kwargs["format"] == ActionItemList.model_json_schema()
    assert kwargs["options"] == {"temperature": 0}


def test_llm_extract_keyword_prefixes(monkeypatch):
    """Function correctly forwards keyword-prefixed input to chat() and returns the LLM's items."""
    fake_chat = MagicMock(return_value=_make_fake_response('{"items": ["banana", "kiwi"]}'))
    monkeypatch.setattr("week2.app.services.extract.chat", fake_chat)

    text = "todo: ship docs\naction: fix bug\nnext: investigate API"
    result = extract_action_items_llm(text)
    assert result == ["banana", "kiwi"]
    fake_chat.assert_called_once()
    kwargs = fake_chat.call_args.kwargs
    assert kwargs["messages"][1]["content"] == text


def test_llm_extract_empty_input_does_not_call_llm(monkeypatch):
    """Empty/whitespace input must short-circuit and never call `chat`."""

    def boom(**kwargs):
        raise AssertionError("chat() should not be called for empty input")

    monkeypatch.setattr("week2.app.services.extract.chat", boom)

    assert extract_action_items_llm("") == []
    assert extract_action_items_llm("   \n  ") == []


def test_llm_extract_no_action_items(monkeypatch):
    """Prose with no actionable content yields an empty list via the LLM path.

    Distinct from test_llm_extract_empty_input_does_not_call_llm: here the
    input is non-empty, so the function MUST call chat() and rely on the
    LLM's empty response — not the fast-path short-circuit.
    """
    fake_chat = MagicMock(return_value=_make_fake_response('{"items": []}'))
    monkeypatch.setattr("week2.app.services.extract.chat", fake_chat)

    result = extract_action_items_llm("Just some prose with no tasks at all.")

    assert result == []
    fake_chat.assert_called_once()


def test_llm_extract_malformed_json(monkeypatch, caplog):
    """Malformed LLM response triggers the heuristic fallback and a WARNING log."""
    text = "- task one\n- task two"
    fake_chat = MagicMock(return_value=_make_fake_response('{"foo": 1}'))
    monkeypatch.setattr("week2.app.services.extract.chat", fake_chat)
    with caplog.at_level(logging.WARNING):
        result = extract_action_items_llm(text)
    assert result == extract_action_items(text)
    assert "ValidationError" in caplog.text
    fake_chat.assert_called_once()


def test_llm_extract_connection_error(monkeypatch, caplog):
    """ConnectionError triggers the heuristic fallback and a WARNING log."""
    text = "- task one\n- task two"
    fake_chat = MagicMock(side_effect=ConnectionError("Connection refused"))
    monkeypatch.setattr("week2.app.services.extract.chat", fake_chat)
    with caplog.at_level(logging.WARNING):
        result = extract_action_items_llm(text)
    assert result == extract_action_items(text)
    assert "ConnectionError" in caplog.text
    fake_chat.assert_called_once()

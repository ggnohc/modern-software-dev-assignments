from __future__ import annotations

import logging
import os
import re
from collections.abc import Iterable
from typing import List

from dotenv import load_dotenv
from ollama import ChatResponse, ResponseError, chat
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

load_dotenv()

BULLET_PREFIX_PATTERN = re.compile(r"^\s*([-*•]|\d+\.)\s+")
KEYWORD_PREFIXES = (
    "todo:",
    "action:",
    "next:",
)

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
MAX_INPUT_CHARS = 50_000


class ActionItemList(BaseModel):
    """Structured-output schema for the LLM extractor.

    Wraps a list of action item strings in an object so Ollama's `format=`
    argument receives a top-level JSON Schema object (bare arrays are not
    universally supported by all models).
    """

    items: list[str]


def _is_action_line(line: str) -> bool:
    stripped = line.strip().lower()
    if not stripped:
        return False
    if BULLET_PREFIX_PATTERN.match(stripped):
        return True
    if any(stripped.startswith(prefix) for prefix in KEYWORD_PREFIXES):
        return True
    if "[ ]" in stripped or "[todo]" in stripped:
        return True
    return False


def _dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    """Return ``items`` with case-insensitive duplicates removed, preserving order.

    Empty / whitespace-only entries are dropped. The first surface form
    encountered for a given lowercased value is kept (e.g. for the input
    ``["Write tests", "write tests"]`` the result is ``["Write tests"]``).
    """
    seen: set[str] = set()
    unique: List[str] = []
    for item in items:
        cleaned = item.strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        unique.append(cleaned)
    return unique


def extract_action_items(text: str) -> List[str]:
    lines = text.splitlines()
    extracted: List[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if _is_action_line(line):
            cleaned = BULLET_PREFIX_PATTERN.sub("", line)
            cleaned = cleaned.strip()
            # Trim common checkbox markers
            cleaned = cleaned.removeprefix("[ ]").strip()
            cleaned = cleaned.removeprefix("[todo]").strip()
            extracted.append(cleaned)
    # Fallback: if nothing matched, heuristically split into sentences and pick imperative-like ones
    if not extracted:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        for sentence in sentences:
            s = sentence.strip()
            if not s:
                continue
            if _looks_imperative(s):
                extracted.append(s)
    return _dedupe_preserve_order(extracted)


_LLM_SYSTEM_PROMPT = """\
You extract action items from free-form notes, meeting minutes, and similar text.

An "action item" is a concrete task or next step. Recognize them when they appear as:
  - bulleted or numbered list items (e.g. "- write tests", "1. Update docs")
  - lines prefixed with "todo:", "action:", or "next:"
  - markdown checkboxes ("[ ] ...", "[todo] ...")
  - imperative sentences (e.g. "Investigate the API timeout", "Refactor the parser")

Rules:
  - Return ONLY items that appear in the input text. Do not invent tasks.
  - If there are no action items, return an empty list.
  - Strip bullet, number, and checkbox markers from each item; preserve the
    original wording otherwise.
  - Respond with JSON matching the provided schema.
"""


def extract_action_items_llm(text: str) -> List[str]:
    """Extract action items from free-form text using an LLM via Ollama.

    Drop-in alternative to :func:`extract_action_items` that delegates the
    classification to a local LLM. Uses Ollama's structured-outputs feature
    (https://ollama.com/blog/structured-outputs) with the
    :class:`ActionItemList` Pydantic schema to constrain the response to a
    JSON object containing a list of strings.

    Error policy: on any LLM-side failure (daemon unreachable, model not
    pulled, malformed structured output) this function falls back to the
    heuristic :func:`extract_action_items` rather than raising. The failure
    is logged at WARNING level so it is observable but doesn't break the
    request path.

    Args:
        text: Free-form notes / meeting transcript / etc.

    Returns:
        List of deduplicated action item strings, in the order the LLM
        returned them. Returns an empty list for empty / whitespace input
        without calling the LLM.
    """
    if not text or not text.strip():
        return []

    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS]

    messages = [
        {"role": "system", "content": _LLM_SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]

    try:
        response = chat(
            model=OLLAMA_MODEL,
            messages=messages,
            format=ActionItemList.model_json_schema(),
            options={"temperature": 0},
        )
        # Narrow the union to ChatResponse: chat() can also return a streaming
        # iterator when stream=True, but we never pass stream=True here.
        assert isinstance(response, ChatResponse)
        parsed = ActionItemList.model_validate_json(response.message.content)
    except (ConnectionError, ResponseError, ValidationError) as exc:
        logger.warning(
            "LLM extraction failed (%s); falling back to heuristic extractor",
            type(exc).__name__,
        )
        return extract_action_items(text)

    return _dedupe_preserve_order(parsed.items)


def _looks_imperative(sentence: str) -> bool:
    words = re.findall(r"[A-Za-z']+", sentence)
    if not words:
        return False
    first = words[0]
    # Crude heuristic: treat these as imperative starters
    imperative_starters = {
        "add",
        "create",
        "implement",
        "fix",
        "update",
        "write",
        "check",
        "verify",
        "refactor",
        "document",
        "design",
        "investigate",
    }
    return first.lower() in imperative_starters

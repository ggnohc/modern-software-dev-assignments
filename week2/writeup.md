# Week 2 Write-up
Tip: To preview this markdown file
- On Mac, press `Command (⌘) + Shift + V`
- On Windows/Linux, press `Ctrl + Shift + V`

## INSTRUCTIONS

Fill out all of the `TODO`s in this file.

## SUBMISSION DETAILS

Name: **TODO** \
SUNet ID: **TODO** \
Citations:
- Cursor IDE with Claude as the coding assistant (used in tutor mode for guided implementation).
- Ollama Python SDK (`ollama==0.5.x`) — https://github.com/ollama/ollama-python
- Ollama structured outputs blog — https://ollama.com/blog/structured-outputs
- Pydantic v2 docs — https://docs.pydantic.dev/2.0/

This assignment took me about **TODO** hours to do.


## YOUR RESPONSES
For each exercise, please include what prompts you used to generate the answer, in addition to the location of the generated response. Make sure to clearly add comments in your code documenting which parts are generated.

### Exercise 1: Scaffold a New Feature

Prompt:
```
Help me implement the function extract_action_items_llm(). I want it to be
using Pydantic schema shape. What else do I need to consider?
```

Follow-up prompts to refine the implementation:
```
- "yes, please go ahead with Option B"  (after the assistant explained
  the assert-isinstance pattern for narrowing the ChatResponse | Iterator
  union returned by ollama.chat())
- "just give me the code"  (escape-hatch invocation that produced the
  final implementation of extract_action_items_llm)
```

Generated / Modified Code Snippets:
- `week2/app/services/extract.py`
  - Lines 1–15: cleaned imports (removed unused `json`/`Any`, added `logging`,
    `Iterable`, `ChatResponse`, `ResponseError`, `BaseModel`, `ValidationError`);
    module-level `logger = logging.getLogger(__name__)`.
  - Lines 24–25: `OLLAMA_MODEL` and `MAX_INPUT_CHARS` constants (env-driven model name).
  - Lines 28–36: `ActionItemList` Pydantic schema (wrapper object with `items: list[str]`).
  - Lines 52–70: new shared helper `_dedupe_preserve_order` factored out
    so the heuristic and LLM extractors don't duplicate logic.
  - Line 96: existing `extract_action_items` updated to call the new helper.
  - Lines 99–114: `_LLM_SYSTEM_PROMPT` constant (mirrors the heuristic's
    intuition: bullets, `todo:`/`action:`/`next:`, checkboxes, imperative
    sentences; explicit anti-hallucination and empty-list rules).
  - Lines 117–166: `extract_action_items_llm()` — the LLM-powered extractor.

Design decisions and rationale:

- **Model selection.** Defaulted to `llama3.2:3b` via `os.getenv("OLLAMA_MODEL", "llama3.2:3b")`.
  Env-driven so I don't hardcode a value, and small enough to run on a laptop
  while still producing reasonable structured-output discipline. A `.env`
  override is supported because `load_dotenv()` is already called at module
  import time.

- **Pydantic schema shape — wrapper, not bare list.** `ActionItemList`
  wraps `items: list[str]` in an object instead of being a bare `list[str]`.
  Ollama's `format=` argument expects a top-level JSON Schema object; some
  models reject a bare-array top-level schema. Wrapper is the safer default.

- **Error policy — Option B (fallback to heuristic) with WARNING log.**
  On `ConnectionError`, `ollama.ResponseError`, or `pydantic.ValidationError`
  the function returns `extract_action_items(text)` rather than raising.
  Tradeoff: friendlier UX (the endpoint always returns *something*) at the
  cost of hiding LLM availability problems. The `logger.warning(...)` puts
  observability back so failures are not silent. Logged value is
  `type(exc).__name__` only — the exception's `str()` could contain user
  content, which would be a privacy / log-injection risk.

- **System prompt.** Verbatim:
  ```
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
  ```

- **Defense-in-depth controls.**
  - Empty / whitespace-only input short-circuits to `[]` *before* calling
    the LLM (saves tokens, latency; matches heuristic behavior).
  - `MAX_INPUT_CHARS = 50_000` cap on input — prevents accidental huge pastes
    from blowing the context window.
  - `options={"temperature": 0}` for determinism in any future eval runs.
  - `assert isinstance(response, ChatResponse)` after the call narrows the
    `chat()` return-type union (it can also return a streaming iterator
    when `stream=True`, which we never pass) — silences a pylint false
    positive *and* fails loudly if the SDK contract ever changes.

### Exercise 2: Add Unit Tests

Prompt:
```
Help me with the unit tests for extract_action_items_llm(), but give me
more hints instead of the code.
```

Follow-up prompts during the iterative debugging:
```
- "@_make_fake_chat help me check this implementation"  (to review my
  initial fake response object that mistakenly used OpenAI's choices[].message
  shape instead of Ollama's single message shape)
- "how do i test for extract_action_items_llm only?"  (after the
  ModuleNotFoundError when I patched 'app.services.extract.chat' instead
  of 'week2.app.services.extract.chat')
- "i still don't get it, can you show me the exact code change?"
  (escape hatch for the empty-input test)
- "just show me how to fix this and move on to next test"  (escape hatch
  for the bullet-list test cleanup and the no-action-items test)
- "Please give me some hints"  (for malformed-JSON test)
- "please check it out"  (for review of my keyword-prefixes, malformed-JSON,
  and connection-error tests)
```

Generated / Modified Code Snippets:
- `week2/tests/test_extract.py`
  - Lines 1–10: added imports for `logging`, `unittest.mock.MagicMock`,
    `ollama.{ChatResponse, Message}`, and the new symbols
    (`extract_action_items_llm`, `ActionItemList`, `OLLAMA_MODEL`).
  - Lines 49–50: `_make_fake_response(content: str) -> ChatResponse` factory.
  - Lines 54–96: banner comment block documenting the mocking mental
    model — "a mock is a puppet, not a brain" and the distinct-data
    discipline. Future-proofing for the next person to read this file.
  - Lines 99–117: `test_llm_extract_bullet_list` — happy-path with
    distinct fake data plus call-shape assertions on `model`, `format`,
    `options`, and the user-message content.
  - Lines 119–129: `test_llm_extract_keyword_prefixes` — same pattern,
    keyword-prefixed input.
  - Lines 132–140: `test_llm_extract_empty_input_does_not_call_llm` —
    patches `chat` with a function that *raises* if called; proves the
    fast-path short-circuit works.
  - Lines 143–155: `test_llm_extract_no_action_items` — non-empty input,
    fake response with `{"items": []}`, plus `assert_called_once()` so
    the test can't be fooled by the empty-input fast-path.
  - Lines 158–168: `test_llm_extract_malformed_json` — fake returns
    `'{"foo": 1}'` (valid JSON, wrong schema); asserts the result equals
    `extract_action_items(text)` (the fallback) AND that `caplog.text`
    contains `"ValidationError"` (proves the fallback branch was taken,
    not just that the value coincidentally matched).
  - Lines 171–181: `test_llm_extract_connection_error` — `MagicMock(side_effect=ConnectionError(...))`;
    same belt-and-suspenders assertions as the malformed-JSON test.

Test design decisions:

- **Mocking strategy.** Patch the imported name in the test target's module
  (`week2.app.services.extract.chat`), not the source module (`ollama.chat`).
  The implementation captured a reference at import time, so patching the
  source module would do nothing.

- **`MagicMock` over manual closures.** `MagicMock(return_value=...)` and
  `MagicMock(side_effect=...)` give us free call-counting (`assert_called_once()`)
  and kwargs inspection (`mock.call_args.kwargs`). Less code than a hand-rolled
  closure-with-list pattern.

- **Distinct fake data in happy-path tests.** The implementation falls back
  to the heuristic on errors. If the input bullets and the fake response
  items overlap, both paths produce the same output and the test cannot
  distinguish them — a regression that silently broke the LLM call would
  go unnoticed. Fake-response items `["banana", "kiwi"]` cannot be produced
  by the heuristic from the test's input, so the test fails loudly if the
  fallback fires by accident.

- **`caplog` for fallback proof.** Error-path tests assert
  `"ValidationError" in caplog.text` (or `"ConnectionError"`). Without
  this, equality with the heuristic's output would be ambiguous:
  fallback-took-over vs. coincidental-empty-list become indistinguishable.

- **Sanity-check loop ("see it fail before you trust it").** For every
  test, after green I temporarily broke the implementation (e.g. removed
  an exception type from the `except` tuple, commented out the `try/except`
  block, swapped distinct fake data for overlapping data) and re-ran to
  confirm the test would *fail* in the predicted way. This is the
  Red-Green-Refactor "Red" step, normally skipped, that gives high
  confidence the tests actually catch regressions.

#### Mistakes I made along the way (kept here as a learning artifact)

1. **`{{` and `}}` are not JSON brace escaping outside f-strings.** I
   wrote `'{{"items": ["something"]}}'` thinking the doubled braces
   would emit literal `{` and `}`. They don't — that only works inside
   f-strings. The string was actually `{{"items": ["something"]}}`, which
   is invalid JSON. Pydantic raised `ValidationError` and the
   implementation silently fell back to the heuristic, masking the bug.
   Lesson: when in doubt, paste the literal into `json.loads(...)` and
   watch what happens.

2. **Confused Ollama's response shape with OpenAI's.** My first
   `_make_fake_response` had `response=Response(choices=[{"message": {...}}])`
   — that's the OpenAI ChatCompletion shape. Ollama's `ChatResponse`
   has a single `.message.content`, not `.choices[0].message.content`.
   Lesson: introspect the SDK with
   `python -c "from ollama import ChatResponse; print(ChatResponse.model_fields)"`
   before fabricating fakes.

3. **Wrong patch path.** I started with
   `monkeypatch.setattr("app.services.extract.chat", ...)` and got
   `ModuleNotFoundError: No module named 'app'`. The package path is
   `week2.app.services.extract` because the tests are inside the `week2`
   package. Lesson: the patch path must match the *importer's* module,
   not just what the importer named the symbol.

4. **Replaced `chat` (a function) with a `ChatResponse` instance.**
   I wrote `monkeypatch.setattr(..., _make_fake_response("[]"))`. The
   `()` invokes the helper *now*, so the second arg was a `ChatResponse`
   instance — not a callable. The next call to `chat(...)` raised
   `TypeError: 'ChatResponse' object is not callable`. Lesson:
   `MagicMock(return_value=fake)` keeps the patched value callable.

5. **Test passed for the wrong reason because heuristic fallback masked it.**
   First version of `test_llm_extract_bullet_list` had input
   `"* action item 1\n* action item 2"` and asserted on `["action item 1", "action item 2"]`
   — exactly what the heuristic would produce. So the test passed
   whether the LLM path ran *or* the fallback fired. Fixed by switching
   the fake response to `["banana", "kiwi"]`.

6. **Invented `monkeypatch.get_attr(...)`.** This method doesn't exist
   on `MonkeyPatch`. The correct way to assert "not called" is to make
   the patched callable raise on invocation (so calling it fails the
   test) or to use `MagicMock` and call `mock.assert_not_called()`.

### Exercise 3: Refactor Existing Code for Clarity
Prompt:
```
TODO
```

Generated/Modified Code Snippets:
```
TODO: List all modified code files with the relevant line numbers. (We anticipate there may be multiple scattered changes here – just produce as comprehensive of a list as you can.)
```


### Exercise 4: Use Agentic Mode to Automate a Small Task
Prompt:
```
TODO
```

Generated Code Snippets:
```
TODO: List all modified code files with the relevant line numbers.
```


### Exercise 5: Generate a README from the Codebase
Prompt:
```
TODO
```

Generated Code Snippets:
```
TODO: List all modified code files with the relevant line numbers.
```


## SUBMISSION INSTRUCTIONS
1. Hit a `Command (⌘) + F` (or `Ctrl + F`) to find any remaining `TODO`s in this file. If no results are found, congratulations – you've completed all required fields. 
2. Make sure you have all changes pushed to your remote repository for grading.
3. Submit via Gradescope.

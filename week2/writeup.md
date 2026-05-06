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

I split this exercise into four sub-steps matching the four buckets the
assignment calls out (API contracts/schemas, DB layer cleanup, app
lifecycle/configuration, error handling). The first two sub-steps are
documented below; the remaining two are in progress.

Worth noting up-front: midway through this exercise I realized I had
been treating it as a Python homework exercise rather than as the
AI-IDE practice the assignment is actually grading. The Week 2 syllabus
is "Anatomy of Coding Agents" and the rubric is *10 points for the
generated code, 10 points for the prompt, per part*. So Step 1 below
was driven through a more conversational, hint-led workflow, and
Step 2 onward was driven by writing a single precise prompt and letting
the agent execute. Both styles produced working code; the second style
produced more interesting writeup material (deviations, surprises,
verification gotchas) which is what this exercise is designed to elicit.

#### Step 1: notes.py router → Pydantic request/response models

Prompt(s) used:
```
- "Help me with TODO 3 — what does refactoring for well-defined API
   contracts/schemas look like?"
- "Walk me through Step 1: create week2/app/schemas.py with
   CreateNoteRequest and NoteResponse, then refactor week2/app/routers/notes.py
   to use them."
- "Please show me the code for Step 1"  (escape hatch for the schemas)
```

Generated / modified code:
- `week2/app/schemas.py` — *new file*
  - Module docstring documenting the architectural rule (schemas describe
    the API surface; storage types must not leak in here).
  - `CreateNoteRequest` with `model_config = ConfigDict(str_strip_whitespace=True)`
    and `content: str = Field(..., min_length=1, ...)` — Pydantic now
    rejects whitespace-only content at parse time, replacing the manual
    `.strip()` + `if not content` dance.
  - `NoteResponse` (`id`, `content`, `created_at`).
- `week2/app/routers/notes.py` — refactored both endpoints
  - `POST /notes`: signature now `payload: CreateNoteRequest`, decorator
    has `response_model=NoteResponse`, body shrinks to three lines, and
    response construction uses `NoteResponse(**dict(note))` so adding
    a column to the `notes` table doesn't require touching the router.
  - `GET /notes/{note_id}`: same treatment; the `if row is None: raise
    HTTPException(404, ...)` line stayed because that is *domain* validation
    (does this row exist?) which Pydantic cannot do for me. Important
    distinction worth holding onto: schema validation = shape; domain
    validation = "is this allowed in our world?".
  - Removed unused `typing.Any/Dict/List` imports.

Verification:
- TestClient smoke test covering happy POST, whitespace-only body (now 422
  instead of 400), missing key (422), wrong type (422), padded valid input
  (whitespace stripped on the way in), and GET regression. All passed.

Behavior changes for clients:
- 400 → 422 for empty / whitespace-only / missing `content`. New 422 body
  is structured Pydantic detail with `type` / `loc` / `msg` instead of the
  old `{"detail": "content is required"}` string.
- Happy-path responses are byte-identical.

#### Step 2: action_items.py router → Pydantic request/response models

This step was driven entirely by a single precise prompt to the agent
rather than a conversational hint-ladder. Prompt verbatim:

```
Refactor week2/app/routers/action_items.py to use Pydantic request and
response models, following the style established in week2/app/routers/notes.py.

1. In week2/app/schemas.py, add the following models:
   - ExtractRequest: { text: str (stripped, non-empty), save_note: bool default False }
   - ExtractedItem: { id: int, text: str }
   - ExtractResponse: { note_id: int | None, items: list[ExtractedItem] }
   - ActionItemResponse: { id: int, note_id: int | None, text: str,
                           done: bool, created_at: str }
   - MarkDoneRequest: { done: bool default True }

2. Refactor each of the three endpoints in action_items.py to:
   - accept the request schema as the body parameter
   - declare response_model= and the return type annotation
   - construct response models via Schema(**dict(row)) where applicable
   - delete now-redundant manual validation (e.g., the manual
     "if not text: raise HTTPException(400)")

3. Remove unused imports from typing (Any, Dict).

Do not touch week2/app/db.py — that is a separate refactor step.

After making changes, list the files you modified and any behavior changes
clients might observe (e.g., 400 -> 422 on invalid input).
```

Generated / modified code:
- `week2/app/schemas.py` — appended six new models (ExtractRequest,
  ExtractedItem, ExtractResponse, ActionItemResponse, MarkDoneRequest,
  and one bonus model — see "agent deviation" below).
- `week2/app/routers/action_items.py` — fully rewritten:
  - `POST /extract` now takes `ExtractRequest`, returns `ExtractResponse`.
    Manual `payload.get("text", "").strip()` and the manual 400 check
    are gone — Pydantic does it.
  - `GET ""` returns `list[ActionItemResponse]`. The manual
    `bool(r["done"])` cast is gone; Pydantic v2 coerces 0/1 → False/True
    for `bool`-typed fields automatically.
  - `POST /{action_item_id}/done` takes `MarkDoneRequest`, returns
    `MarkDoneResponse`.
  - All `typing.Any/Dict/List/Optional` imports removed; `int | None`
    syntax used throughout.

Where the agent diverged from spec (good catch — read the diff, kids):
- I asked for five new schemas. The agent added a sixth, `MarkDoneResponse`
  (`{id: int, done: bool}`), so the third endpoint would have a typed
  response like the others. It flagged this in its summary rather than
  silently slipping it in. I accepted it because consistency across
  endpoints is more valuable than strict adherence to my list, but it's
  a useful reminder that agents will fill in "obvious" gaps you didn't
  specify.

Surprise during verification:
- I assumed `save_note: "yes"` would trigger 422. It actually returns
  200 — Pydantic v2 in lax mode accepts `"yes"`/`"no"`, `"on"`/`"off"`,
  `"y"`/`"n"`, `"true"`/`"false"`, and `"1"`/`"0"` as valid bools. Strings
  outside that vocabulary (e.g., `"maybe"`) do raise 422. If I wanted
  strict bool parsing I'd need `Strict[bool]` or a custom validator.
  Documented for future tightening, not changed for now.

Verification gotcha (not a server bug, captured for the writeup grade):
- The `curl ... | jq    # expect 422` pattern from the verification
  snippet failed in zsh because interactive comments are off by default
  (`setopt INTERACTIVE_COMMENTS` would enable them). zsh passed `#`,
  `expect`, `422` as literal arguments to jq, producing
  `jq: error: Top-level program not given (try ".")` — which *looked*
  like a server bug but wasn't. Re-running with
  `curl -s -o /dev/null -w '%{http_code}\n' ...` and `curl -i ...`
  confirmed both negative cases returned 422 with structured Pydantic
  detail bodies. Lesson: when an AI-suggested verification command
  appears to fail, distinguish "tool error" from "system-under-test error"
  before changing the system.

Behavior changes for clients:
- 400 → 422 on empty / missing / whitespace `text`, with structured
  detail body.
- `save_note` and `done` are now typed bools; values outside Pydantic's
  bool vocabulary return 422.
- Happy-path response shapes are byte-identical to the pre-refactor JSON.

#### Step 3: db.py → context-manager + helper pattern

Prompt verbatim (single shot to the agent in Cursor):

```
Refactor week2/app/db.py to clean up the database layer. Keep the file's
public function signatures unchanged so the routers don't need to change.

Goals:

1. Fix the connection-leak. The current `with get_connection() as connection:`
   only commits/rolls-back the transaction; it does NOT close the connection
   (this is a sqlite3 quirk). Replace it with a contextlib.contextmanager
   helper named `_connection()` that:
     - opens the connection,
     - sets row_factory = sqlite3.Row,
     - yields it,
     - calls connection.close() in a finally block.

2. Reduce the repeated boilerplate. Add small private helpers in db.py:
     - `_execute(sql, params=()) -> int`: runs a single INSERT/UPDATE
       inside `_connection()`, commits, and returns cursor.lastrowid as int.
     - `_query_one(sql, params=()) -> sqlite3.Row | None`: runs a SELECT
       and returns one row or None.
     - `_query_all(sql, params=()) -> list[sqlite3.Row]`: runs a SELECT
       and returns all rows.
   Rewrite the existing public functions in terms of these helpers. The
   public function signatures and return types must NOT change.

3. Add minimal error handling. Catch sqlite3.Error at the helper level,
   log via logger.exception(...) (use a module-level
   logger = logging.getLogger(__name__)), and re-raise. Do not swallow.
   The router layer is not the right place to translate sqlite3.Error
   into an HTTP response — we will add a global exception handler in a
   later refactor step. The SQL is fine to log; do NOT log the params.

Out of scope (will be addressed in a later step):
- Moving init_db() out of import-time.
- Making DB_PATH configurable via environment / pydantic-settings.
- Adding a global FastAPI exception handler for sqlite3.Error.
- Replacing sqlite3.Row with Pydantic models at the boundary.

After making changes:
- Confirm no public function signatures changed (compare before/after).
- List behavior changes clients might observe (there should be none for
  happy paths; the only visible difference should be a logged exception
  on database errors).
- Do not modify any router or test files.
```

Generated / modified code:
- `week2/app/db.py` — full rewrite around four (one more than the prompt
  asked for — see below) helpers, all wrapped in a closing context manager.
  - New module docstring explaining the connection-leak fix.
  - New `_connection()` `@contextmanager` that closes in `finally`. The
    plain `with sqlite3.Connection` only commits/rolls back; it doesn't
    close. This is the kind of footgun you only catch by reading the
    sqlite3 docs carefully.
  - New `_execute`, `_query_one`, `_query_all` helpers, each catching
    `sqlite3.Error`, calling `logger.exception("...SQL: %s", sql)` (no
    params), and re-raising.
  - Public functions (`insert_note`, `list_notes`, `get_note`, etc.)
    became one-liners delegating to the helpers.

Where the agent diverged from spec (read carefully — second time it's
done this):
- The prompt listed three helpers. The agent added a fourth,
  `_execute_many(sql, params_seq)`, to preserve the all-or-nothing
  transaction semantics of `insert_action_items()`. Calling `_execute()`
  N times would have opened and committed N independent transactions,
  which is a *behavior change*: a partial-mid-batch failure would leave
  earlier rows committed, where the original code rolled the whole batch
  back. The agent caught this on its own and flagged it in its summary
  rather than silently slipping it in. That's good agent behavior, and
  it's exactly the same pattern from Step 2 — agents will fill in
  obvious gaps when the prompt's literal text would change behavior.

Verification:
- Before/after signature snapshot via `inspect.signature` — all 9 public
  functions unchanged.
- Functional smoke test through every public function (init_db,
  insert_note, get_note, list_notes, insert_action_items,
  list_action_items, mark_action_item_done) plus an error-path test
  with bad SQL. The error path correctly logged
  `"Database error while executing SQL: ..."` with traceback and
  re-raised the original `sqlite3.OperationalError`.
- End-to-end TestClient regression covering all router endpoints. All
  responses byte-identical to pre-refactor JSON.

Behavior changes for clients:
- Happy path: none.
- Error path: improved observability — DB errors now produce an
  ERROR-level log line with the SQL and traceback. Re-raised
  unchanged so FastAPI's default 500 behavior is preserved (the
  *next* slice replaces this with a structured handler).

#### Step 4: app lifecycle + configuration via pydantic-settings

This step had two tightly coupled goals: stop running `init_db()` at
import time, and centralize all environment-driven configuration in a
single Settings object. Single prompt to the agent (see writeup history
in the Cursor chat for the full text — abbreviated here).

Key prompt instructions:
- Add `pydantic-settings` as a dependency.
- New module `week2/app/config.py` with a `Settings(BaseSettings)` class
  (`db_path`, `ollama_model`, `max_input_chars`) and an
  `@lru_cache(maxsize=1)`-decorated `get_settings()` accessor.
- `env_prefix="APP_"` so env vars are `APP_DB_PATH` etc. (avoids
  collisions with system / SDK env vars).
- `db.py` must read `get_settings().db_path` at *call time* — that's
  what makes test overrides work.
- `extract.py`: drop the top-level `OLLAMA_MODEL`/`MAX_INPUT_CHARS`
  constants and the `load_dotenv()` call; read both via
  `get_settings()` at call time.
- `main.py`: replace the import-time `init_db()` call with a FastAPI
  `lifespan` async context manager.
- The single allowed test edit: `test_extract.py` imports `OLLAMA_MODEL`
  and asserts on it; replace with `get_settings().ollama_model`.

Generated / modified code:
- New file `week2/app/config.py` with `Settings(BaseSettings)` and
  `@functools.lru_cache(maxsize=1)` `get_settings()`. Module docstring
  documents the env-prefix convention and the cache-clear pattern for
  tests.
- `week2/app/db.py` — `BASE_DIR`/`DATA_DIR`/`DB_PATH` retained as
  deprecated fallbacks (per prompt) but no longer the source of truth;
  `ensure_data_directory_exists` and both connection paths now read
  `get_settings().db_path`.
- `week2/app/services/extract.py` — removed the top-level constants and
  `load_dotenv()`; `extract_action_items_llm()` reads from settings
  at call time.
- `week2/app/main.py` — top-level `init_db()` deleted; new `lifespan`
  async context manager logs startup/shutdown and runs `init_db()`.
- `week2/tests/test_extract.py` — single one-line change to swap
  `OLLAMA_MODEL` for `get_settings().ollama_model`.
- `pyproject.toml` / `poetry.lock` — `pydantic-settings = "^2.14.0"`.

Verification:
- All 7 unit tests pass after the symbol swap.
- Setting `APP_DB_PATH=/tmp/.../override.db` and starting the app via
  `TestClient(app)` causes that file to be created — proving the
  override flows all the way through to the actual sqlite3.connect call.
- The DB file does NOT exist immediately after `from week2.app.main import app`;
  it only appears after `TestClient(app).__enter__()` (i.e. after the
  lifespan startup runs). This is the precise behavior we wanted: no
  more import-time side effects.

Behavior changes for clients:
- Happy paths byte-identical.
- The DB file is no longer created at import time. Tools that import
  `week2.app.main` (test runners, doc generators, schema extractors)
  no longer trigger schema creation as a side effect.

Things flagged for follow-up:
- `python-dotenv` is now redundant — `pydantic-settings` reads `.env`
  directly via `env_file=".env"`. Left in `pyproject.toml` for now.
- `BASE_DIR`/`DATA_DIR`/`DB_PATH` are dead code paths in `db.py`.
  Kept per prompt; future cleanup.
- `@lru_cache` on `get_settings()` is global state. Tests that mutate
  the environment must call `get_settings.cache_clear()` for the
  override to take effect. Documented in the module docstring.

#### Step 5: error handling + structured logging

Final TODO 3 slice. Goal: replace the bare 500-with-exception-text
behavior with a structured `{"detail": "internal database error"}`
response, add process-wide log configuration, and consolidate the
per-helper logging into a single global handler.

Key prompt instructions:
- New module `week2/app/logging_config.py` with a
  `configure_logging(level)` helper using `logging.config.dictConfig`
  (NOT `basicConfig`, which is a no-op once uvicorn's handlers exist),
  `disable_existing_loggers=False` (so uvicorn's own loggers stay
  intact), and the format
  `"%(asctime)s %(levelname)-8s %(name)s :: %(message)s"`.
- Add `log_level: str = "INFO"` to `Settings`.
- Add a global `sqlite3.Error` exception handler in `main.py` that
  returns `JSONResponse(500, {"detail": "internal database error"})`
  and logs via `logger.exception(...)` with method + path (NOT body /
  query params, which may contain user content).
- Strip the four `try/except sqlite3.Error: logger.exception(...); raise`
  wrappers from `db.py` — the global handler now owns logging for these
  errors, and keeping both produces duplicate log lines.
- Call `configure_logging(level=get_settings().log_level)` as the first
  step in the lifespan, before `init_db()`, so startup output is
  consistently formatted.

Generated / modified code:
- New file `week2/app/logging_config.py` with `configure_logging()`.
  Eager-validates the level name (typos like `"INF0"` raise loudly at
  startup rather than silently falling back to `WARNING`).
- `week2/app/config.py` — added `log_level: str = "INFO"`.
- `week2/app/db.py` — removed all four helper-level `try/except`
  wrappers and the wrapper around `init_db`. The helpers are now just
  the SQL execution. Removed the now-unused `import logging` and
  module-level `logger`.
- `week2/app/main.py` — added the `sqlite3.Error` exception handler;
  registered via `app.add_exception_handler`; lifespan now calls
  `configure_logging` before `init_db`.

Surprise during verification (this is the gold for the writeup):
- First attempt: the response was correct (`{"detail": "internal
  database error"}`, status 500) and the log line appeared in the
  configured format — but **no traceback**. Logs read
  `Unhandled sqlite3.Error on GET /action-items` and that was it.
- Root cause: `logger.exception(msg)` defaults to `exc_info=True`,
  which means "use `sys.exc_info()`". But FastAPI/Starlette's
  exception-handler dispatch happens *outside* the original `except`
  block — by the time our handler runs, `sys.exc_info()` returns
  `(None, None, None)` and the traceback is silently dropped.
- Fix: pass the exception object explicitly. The handler now uses
  `logger.error(..., exc_info=exc)`, which the logging module unwraps
  into `(type(exc), exc, exc.__traceback__)`. Inline comment in
  `main.py` documents the trap so the next person doesn't break it.
- Lesson: AI-generated code that *looks* correct can still drop
  observability data on the floor in non-obvious ways. The prompt's
  verification step ("trigger a sqlite3.Error and confirm the server
  log contains an ERROR line with traceback") was the only thing that
  caught this. Without that explicit check, the bug would have shipped
  and we'd have been blind to DB errors in production.

Verification:
- All 7 unit tests still pass.
- Triggered `sqlite3.Error` (corrupted DB file with garbage bytes,
  then `GET /action-items`):
  - response status: 500
  - response body: `{"detail": "internal database error"}` (verified
    no SQL or exception text leaked)
  - server log: ERROR-level line in the configured format, plus the
    full traceback through `routers/action_items.py` →
    `db.py:_query_all` → `cursor.execute` → `sqlite3.DatabaseError:
    file is not a database`.
- Startup log line uses the configured format:
  `2026-05-06 16:57:53,892 INFO     week2.app.main :: Application
  startup: initializing database schema`.

Behavior changes for clients:
- 500 responses are now structured (`{"detail": "internal database error"}`)
  instead of bare exception text. Clients can rely on the JSON shape
  without parsing free-form messages.
- DB errors are logged exactly once (at the handler) instead of twice
  (per-helper + via FastAPI's default). Identical information density,
  less noise.
- Happy paths: still byte-identical.


### Exercise 4: Use Agentic Mode to Automate a Small Task

Two small features wired up in a single agent invocation: an LLM
extraction endpoint with its frontend button, and a list-all-notes
endpoint with its button. The combined prompt was small enough to
package together — both pieces follow the same shape (new backend
route + matching frontend button) and the agent had everything it
needed to wire both consistently.

Prompt verbatim:

```
Implement TODO 4 of the week 2 assignment: two small features wiring
new backend endpoints to new frontend buttons.

Feature 1 — LLM extraction endpoint + button

Backend:
- Add a new endpoint `POST /action-items/extract-llm` to
  week2/app/routers/action_items.py.
- It accepts the same ExtractRequest body and returns the same
  ExtractResponse as the existing `POST /action-items/extract`. Same
  validation rules, same response_model, same persistence behavior
  (save_note flag still honored).
- The only difference: it calls `extract_action_items_llm()` from
  `week2/app/services/extract.py` instead of `extract_action_items()`.
- Factor the shared body into a small private helper if it makes the
  duplication painful, but a tiny copy is fine for two endpoints.

Frontend (week2/frontend/index.html):
- Add a second button "Extract (LLM)" next to the existing "Extract"
  button.
- Wire it to POST to the new endpoint with the same request body shape.
- The response is identical, so reuse the existing items-rendering code
  (factor it into a helper function if needed).
- Show a loading message while the request is in flight.
- The LLM call is slow (multi-second) — make sure both buttons are
  disabled while a request is in flight to avoid double-submits, then
  re-enabled in a finally block.

Feature 2 — List all notes endpoint + button

Backend:
- Add a new endpoint `GET /notes` to week2/app/routers/notes.py that
  returns all notes ordered by id descending. Use db.list_notes() (it
  already exists). Declare `response_model=list[NoteResponse]`.

Frontend:
- Add a "List Notes" button below the existing controls.
- Wire it to GET /notes and render each note with its id, content
  (escape HTML — note content is user-supplied), and created_at.

Out of scope:
- Pagination on /notes.
- Editing or deleting notes.
- Showing each note's associated action items.
- Restyling the existing UI.

Important security note: when rendering note content in the list-notes
view, do NOT use innerHTML with raw text. Use textContent or escape
the string via document.createTextNode / a small escape helper. The
existing "Extract" rendering already has this issue with item.text —
feel free to fix it in passing while you're touching the rendering
code, but flag it as a separate concern in your summary.
```

Generated / modified code:

- `week2/app/routers/action_items.py`
  - Added `_run_extract(payload, extractor)` private helper (lines 22–42).
    Both `extract` and `extract_llm` now delegate to it; without the
    helper the persistence + response-construction logic is copy-pasted
    across the two endpoints.
  - Existing `extract` endpoint (line 45) became a one-line delegation;
    behavior unchanged.
  - New `extract_llm` endpoint (line 50) — same request/response, calls
    `extract_action_items_llm` instead of the heuristic.

- `week2/app/routers/notes.py`
  - Added `list_notes()` route at line 19, returning `list[NoteResponse]`,
    ordered by id descending (delegated to existing `db.list_notes()`).
  - Existing `get_single_note` route (now line 24) updated with explicit
    `response_model=NoteResponse` for symmetry with the others.

- `week2/frontend/index.html` — full rewrite of the `<script>` block:
  - `withButtonsDisabled(fn)` helper guards every button click against
    double-submit while async work is in flight. The LLM call is the
    main motivator (5–15s on local hardware), but every button now
    routes through it for consistency.
  - `renderItems(items)` and `renderNotes(notes)` both use
    `document.createElement` + `textContent` exclusively — no
    innerHTML interpolation anywhere in the file.
  - `runExtract(endpoint)` is shared between the two extract buttons;
    only the URL differs.
  - "Extract (LLM)" button next to the original "Extract" button.
  - "Saved Notes" section with "List Notes" button below the extract
    controls; renders each note as a list item with id, timestamp, and
    content (the `<pre>`-like styling preserves whitespace in the
    original note text).
  - Light CSS additions for the notes list and a `[disabled]` style on
    buttons.

Where the agent diverged from spec (third time the pattern repeats —
worth tracking for the writeup grade):

- The prompt offered the option of factoring `_run_extract` into a
  helper "if it makes the duplication painful" but said "a tiny copy
  is fine." The agent chose to factor anyway, judging that two routes
  with three near-identical lines each was already over the threshold.
  Reasonable call, slightly more code than the prompt's minimum, and
  the helper is short enough that the cost is low.

Surprise / writeup gold: closing a real XSS while shipping a feature.

The original frontend interpolated user-supplied `item.text` into
`innerHTML` via a template string. A note containing
`<img src=x onerror=alert(1)>` would have executed in any browser.
The prompt explicitly asked for `textContent` in *new* code and
flagged the existing vulnerability as a separate concern; the agent
elected to fix the existing path too, since rewriting the rendering
helper made the old code dead anyway. The new render path uses safe
DOM construction throughout. Verified with a deliberately malicious
note (`"<script>alert(1)</script>"` in the textarea, saved, then
listed): the string round-trips through SQLite unchanged and renders
as literal text — no script execution.

This is the kind of side-effect win that's worth being deliberate
about: when a prompt touches a critical path, asking the agent to
"fix it in passing while you're here" trades a small scope creep for
a real security improvement. The cost was zero — the safe pattern is
the same number of lines as the unsafe one, just structured
differently.

Verification:
- All 7 unit tests pass (the test file was not touched in this slice).
- TestClient regression on existing endpoints: POST /notes (incl. with
  HTML payload), POST /action-items/extract, plus the negatives — all
  unchanged.
- New endpoint smoke test:
  - `GET /notes` returns `list[NoteResponse]`, ordered by id desc.
  - `POST /action-items/extract-llm` with mocked `chat()` returns the
    expected ExtractResponse shape and proves the LLM code path is
    actually hit (`fake_chat.called == True`).
  - Validation negatives on the new LLM endpoint (`{}`, `{"text":"   "}`)
    return 422 — request schema is shared with the heuristic endpoint
    so behavior is identical.

Browser-flow verification (manual, not captured here):
- Both Extract buttons disable themselves and the List Notes button
  during their requests, re-enable in `finally`.
- "Saved Notes" section populates correctly when List Notes is clicked.
- A note saved with `<script>alert(1)</script>` content displays as
  literal text — no alert dialog.
- With Ollama stopped (`pkill ollama`), Extract (LLM) still returns
  results (heuristic fallback) and the server log shows the
  `LLM extraction failed (ConnectionError); falling back to heuristic
  extractor` warning. Resilience pattern from TODO 1 is inherited
  cleanly by the new endpoint.

Behavior changes for clients:
- `POST /action-items/extract` and `GET /notes/{id}` are unchanged.
- Two new endpoints (`POST /action-items/extract-llm`, `GET /notes`)
  are now available. OpenAPI docs at `/docs` automatically list them.
- The frontend page now has two extract buttons and a notes section.


### Exercise 5: Generate a README from the Codebase

The prompt for this exercise was deliberately heavily-spec'd because
README generation is the kind of task where agents over-deliver: badges,
contributor sections, license stubs, "Made with FastAPI" banners, and
duplicate setup instructions all show up uninvited. The constraints in
the prompt below were explicit about what NOT to include for that
reason.

Prompt verbatim:

```
Generate a README.md for the week 2 assignment, located at
`week2/README.md`. The audience is another developer who has just
cloned the repo, has Python/venv/Poetry installed (per the top-level
README), and wants to run, test, or contribute to the action item
extractor.

Required sections, in this order:

1. Title + one-paragraph overview
   - "Action Item Extractor" or similar.
   - One paragraph: a small FastAPI + SQLite app that converts free-form
     notes into a checklist of action items. Two extraction strategies
     are available — a heuristic (regex/imperative) and an LLM-powered
     one via local Ollama — and the LLM path falls back to the heuristic
     if Ollama is unreachable.

2. Quick start
   - Prerequisite: link to the top-level README for environment setup
     (`../README.md`), and remind the reader to activate the venv in
     every new terminal.
   - The single command to run the dev server.
   - The URL.
   - One-sentence note: the SQLite database file is created automatically
     on first server start (via the FastAPI lifespan).

3. Optional: enable LLM extraction
   - Brief explanation that the /action-items/extract-llm endpoint
     calls a local Ollama daemon. Without it, the endpoint silently
     returns heuristic results plus a warning log.
   - Three commands: `ollama serve`, `ollama pull llama3.2:3b`, and
     a `curl` to confirm the model is reachable.

4. Configuration
   - Markdown table: APP_DB_PATH, APP_OLLAMA_MODEL, APP_MAX_INPUT_CHARS,
     APP_LOG_LEVEL — each with the actual default from config.py.

5. API
   - Markdown table covering all 8 endpoints currently exposed.
   - Read the routers to confirm the routes — do not invent endpoints.

6. Running tests
   - Single command + one sentence on what's covered.

7. Project layout
   - Small file tree showing the relevant files (not every file).

8. Notes for grading / context (one short paragraph)
   - This was developed for CS146S using Cursor + Claude.
   - Implementation, design decisions, and prompts are documented in
     week2/writeup.md.

Constraints:
- Markdown only.
- Code blocks must specify the language.
- Do not include shields/badges, contributor sections, or licenses.
- Do not document private helpers (anything starting with `_`).
- Do not duplicate Pydantic field documentation that is already
  available via /docs.
- Do not duplicate the Python/venv/Poetry setup steps from the
  top-level README — link to it instead.
- No "TODO" placeholders.

Verification:
- Every command works when copy-pasted from a fresh shell.
- The endpoint table matches the actual routes
  (`curl http://127.0.0.1:8000/openapi.json | jq '.paths | keys'`).
- The env-var table matches the fields actually defined in
  week2/app/config.py.
```

Generated / modified code:
- `week2/README.md` (new file, ~120 lines). Eight sections in the order
  the prompt specified: overview → quick start → optional Ollama →
  configuration table → API table → tests → project layout →
  architecture notes pointer back to this writeup.
- The "Architecture notes" section at the end was a small over-delivery
  beyond the prompt's eight required sections — a four-bullet summary
  of the patterns established during the TODO 3 refactor (config as
  source of truth, no import-time side effects, schemas-not-storage,
  error path consolidation). I judged it worth keeping because each
  bullet links forward to a specific writeup section and helps a reader
  decide whether they need to read more before contributing.

Verification performed:
- Ran the suggested OpenAPI cross-check by spinning up the app via
  TestClient and reading `/openapi.json`. Output was exactly the eight
  endpoints listed in the README's API table — no inventions, no
  omissions.
- The four `APP_*` env vars in the README match the four fields on
  `Settings` in `week2/app/config.py` (`db_path`, `ollama_model`,
  `max_input_chars`, `log_level`). Defaults match.
- The project tree matches the actual layout. No imaginary files.

Things deliberately left out (would have bloated the README):
- A "Troubleshooting" section. Most issues (port in use, venv not
  activated, Ollama not running) either announce themselves clearly
  in the error message or are covered by the existing log lines.
- Badges, license, contributor section. Coursework, not a library.
- Field-by-field schema documentation. `/docs` already provides this
  with better fidelity than markdown could.

Behavior changes for clients: none — README is documentation.


## SUBMISSION INSTRUCTIONS
1. Hit a `Command (⌘) + F` (or `Ctrl + F`) to find any remaining `TODO`s in this file. If no results are found, congratulations – you've completed all required fields. 
2. Make sure you have all changes pushed to your remote repository for grading.
3. Submit via Gradescope.

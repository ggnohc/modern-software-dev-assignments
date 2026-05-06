# Action Item Extractor

A small FastAPI + SQLite app that converts free-form notes into a checklist of
action items. Two extraction strategies are available — a heuristic
(regex / imperative-sentence detection) and an LLM-powered one that talks to
a local Ollama daemon. The LLM path falls back to the heuristic if Ollama is
unreachable, so the API remains usable even without a running model.

This project was built for the Week 2 assignment of
[CS146S: The Modern Software Developer](https://themodernsoftware.dev) at
Stanford. Implementation notes, design decisions, and the AI prompts used to
generate / refactor the code live in [`writeup.md`](writeup.md).

## Quick start

Environment setup (Python 3.12 + Poetry + venv) is documented once at the
[top-level repo README](../README.md). Make sure the `.venv` is activated in
every new terminal before running any of the commands below.

```bash
poetry run uvicorn week2.app.main:app --reload
```

Then open http://127.0.0.1:8000/.

The SQLite database file is created automatically on the server's first
startup (via the FastAPI `lifespan` handler) at the path configured by
`APP_DB_PATH` (default: `week2/data/app.db`). Importing the app no longer has
this side effect — only running it does.

## Optional: enable LLM extraction

The `POST /action-items/extract-llm` endpoint calls a local Ollama daemon.
Without it, the endpoint silently returns heuristic results plus a `WARNING`
log line — i.e. requests still succeed, they just don't use the LLM.

```bash
ollama serve            # start the daemon (skip if already running)
ollama pull llama3.2:3b # one-time, ~2 GB
curl -s http://127.0.0.1:11434/api/tags | jq '.models[].name'
```

The model is configurable via `APP_OLLAMA_MODEL`; see [Configuration](#configuration).

## Configuration

All configuration is read from environment variables (or a `.env` file at the
repo root) via `pydantic-settings`. Variables are prefixed with `APP_` to
avoid colliding with system or SDK-specific variables.

| Variable             | Default              | Description                                                                            |
| -------------------- | -------------------- | -------------------------------------------------------------------------------------- |
| `APP_DB_PATH`        | `week2/data/app.db`  | Path to the SQLite database file. Parent directory is created automatically.           |
| `APP_OLLAMA_MODEL`   | `llama3.2:3b`        | Ollama model name used by the LLM extractor.                                           |
| `APP_MAX_INPUT_CHARS`| `50000`              | Hard cap on input length passed to the LLM. Longer inputs are truncated server-side.   |
| `APP_LOG_LEVEL`      | `INFO`               | Root logger level. Accepts any standard name (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Validated at startup; a typo fails loudly. |

## API

The full schema with request/response models is auto-generated and available
at `http://127.0.0.1:8000/docs` (Swagger UI) and `/redoc`.

| Method | Path                                  | Description                                                                                       |
| ------ | ------------------------------------- | ------------------------------------------------------------------------------------------------- |
| GET    | `/`                                   | The single-page HTML frontend.                                                                    |
| POST   | `/notes`                              | Create a note. Whitespace-only content is rejected (422).                                         |
| GET    | `/notes`                              | List all notes, newest first.                                                                     |
| GET    | `/notes/{note_id}`                    | Fetch a single note. Returns 404 if it does not exist.                                            |
| POST   | `/action-items/extract`               | Extract action items via the heuristic extractor. `save_note: true` persists the input first.    |
| POST   | `/action-items/extract-llm`           | Same shape, but classifies via the local LLM. Falls back to the heuristic on any LLM failure.    |
| GET    | `/action-items?note_id={id}`          | List action items. The optional `note_id` query param filters to one note's items.               |
| POST   | `/action-items/{action_item_id}/done` | Mark an action item done or undone. Body `{"done": bool}`; defaults to `true` if body is empty.  |

## Running tests

```bash
poetry run pytest week2/tests/
```

Seven tests covering: the heuristic extractor; the LLM extractor's happy
path on bullet lists and keyword-prefixed lines; the empty-input fast path;
non-actionable input; and both error paths (malformed JSON from the LLM,
connection failure to Ollama). The LLM is mocked in every test; no Ollama
daemon is needed to run the suite.

## Project layout

```text
week2/
├── app/
│   ├── main.py             FastAPI app, lifespan handler, global error handler
│   ├── config.py           pydantic-settings Settings class + cached accessor
│   ├── db.py               SQLite layer (connection helper + execute/query helpers)
│   ├── logging_config.py   dictConfig wrapper for process-wide log format
│   ├── schemas.py          Pydantic request/response models
│   ├── routers/            HTTP route handlers (notes, action_items)
│   └── services/extract.py heuristic + LLM action item extractors
├── tests/test_extract.py
├── frontend/index.html     Single-page UI consumed by GET /
├── README.md               (this file)
└── writeup.md              Assignment write-up: prompts, decisions, AI gotchas
```

## Architecture notes

A few intentional patterns worth knowing if you intend to extend the project:

- **Single source of truth for config.** Modules read `get_settings().db_path`
  at call time, not at import time, so tests can override `APP_DB_PATH` and
  call `get_settings.cache_clear()` without monkey-patching module attributes.
- **No import-time side effects.** Schema creation runs in the FastAPI
  `lifespan` handler. Importing `week2.app.main` from a doc generator or
  test runner does not create the database file.
- **Schemas are the API surface, not the storage layer.** Routers feed
  `sqlite3.Row` objects through `Schema(**dict(row))`. Adding a column to a
  table does not change the API contract unless the schema is updated too.
- **Error path consolidation.** `sqlite3.Error` propagates from `db.py`
  helpers up to a single global FastAPI handler, which logs the failure
  with `exc_info=exc` (passing the exception explicitly because Starlette
  dispatches handlers outside the original `except` block) and returns
  `{"detail": "internal database error"}` with status 500.

For the longer-form rationale behind each of these — and the prompts that
produced the code — see [`writeup.md`](writeup.md).

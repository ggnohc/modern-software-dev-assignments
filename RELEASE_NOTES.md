# Release notes

## Week 1 — Prompting techniques (2026-04-28)

Completed the Week 1 exercises under `week1/` for CS146S-style prompting practice (local Ollama, `mistral-nemo:12b` / `llama3.1:8b` per assignment scripts).

### Highlights

- **K-shot prompting** (`week1/k_shot_prompting.py`): tuned few-shot system prompt for constrained string output.
- **Chain-of-thought** (`week1/chain_of_thought.py`): system prompt requiring explicit modular-arithmetic reasoning and final `Answer:` line.
- **Tool calling** (`week1/tool_calling.py`): system prompt instructing JSON tool calls matching the in-repo executor schema.
- **Self-consistency** (`week1/self_consistency_prompting.py`): system prompt structured for stable majority voting under high temperature.
- **RAG** (`week1/rag.py`): wired `YOUR_CONTEXT_PROVIDER` to supply `data/api_docs.txt` so generation is grounded in retrieved context.
- **Reflexion** (`week1/reflexion.py`): added reflexion system prompt and user-side context builder (prior code + test failures) for a single repair pass.

### Tooling

- **Poetry** (`poetry.toml`): document in-project virtualenv preference (`in-project = true`); `.venv` remains gitignored.

### Lessons learned (for future review)

These are the main mistakes encountered while doing Week 1, what caused them, and how they were fixed—written so you can skim this file months later and remember the *why*.

#### K-shot (`k_shot_prompting.py`)

- **Mistake:** Few-shot examples with **incorrect input→output pairs** (e.g. wrong hand-reversed string). The model learns the *pattern of errors*, not just “reverse letters.”
- **Mistake:** Examples that did not match the **hard case** (compound / multi-token-ish strings). Short English words are easy; the grader string was not.
- **Mistake:** Teaching a **step-by-step letter procedure** while the **user prompt** forbade extra text—only a bare reversed token was allowed—so “show your work” and “output only the word” fought each other.
- **Fix:** Verify every few-shot label **by hand** (count letters, re-reverse). Prefer examples whose **shape** matches the test input. When the rubric allows, include the **strongest possible demonstration** of the exact mapping you need (k-shot is “behavior cloning from examples”).

#### Chain-of-thought (`chain_of_thought.py`)

- **Mistake:** LaTeX-style backslashes in a normal Python string (`\pmod`, `\gcd`) triggered **`SyntaxWarning: invalid escape sequence`**.
- **Fix:** Use a **raw string** (`r"""..."""`) or escape backslashes (`\\pmod`).
- **Mistake:** Under `temperature=0.3`, answers were **stochastic**—sometimes wrong on run 1 (`Answer: 3`, `89`) then right on run 2.
- **Fix:** Require **explicit** theorem use, **show the division** for exponent reduction, and add a **sanity check** (e.g. split mod 4 / mod 25 or recompute in small chunks) so wrong paths are less likely to “sound done.”

#### Tool calling (`tool_calling.py`)

- **Mistake:** Documenting **`add` / `greet`** as callable “tools” even though only **`output_every_func_return_type`** exists in `TOOL_REGISTRY` → `Unknown tool: add`.
- **Mistake:** Letting the model emit **generic tool JSON** (`tool_invocation`, `tool_name`, arrays of args) instead of the grader’s **flat contract**.
- **Fix:** Only describe tools that are **actually executable** in this homework. Pin the **exact JSON shape** the runner parses: top-level **`"tool"`** (string) and **`"args"`** (object). Prefer `args: {}` and let the harness default `file_path` to `__file__`.

#### Self-consistency (`self_consistency_prompting.py`)

- **Mistake:** Treating self-consistency as “magic”—without raising per-run accuracy, majority vote still drifts at **`temperature=1.0`**.
- **Observation:** One run returned **`45`** (location of the second stop) instead of **`25`** (distance *between* stops)—classic **wrong target quantity** under noise.
- **Fix:** Write the system prompt like a **grading rubric**: define variables, compute segment endpoints, subtract, optional sanity check (segments sum to total trip).

#### RAG (`rag.py`)

- **Mistake:** `YOUR_CONTEXT_PROVIDER` returned **`[]`**, so the model saw **“(no context provided)”** and had to hallucinate API details.
- **Fix:** Return the **actual doc chunk(s)** that contain base URL, auth header, and path—here, **`[corpus[0]]`** for the single loaded file.

#### Reflexion (`reflexion.py`)

- **Mistake:** Putting `{prev_code}` / `{failures}` inside **`YOUR_REFLEXION_PROMPT`** without formatting—Python sent **literal braces**, so the system prompt did not substitute values (the user message still carried the truth, which is why runs could succeed anyway).
- **Fix:** Keep the reflexion **system** prompt **static** (rules + output format). Put **all changing facts** (previous code, failure list) in **`your_build_reflexion_context`** using an **f-string** (or `.format`).
- **Nuance:** `any(not c.isalnum() for c in password)` is a **broad** “special character” proxy vs the file’s explicit `SPECIALS` set—fine for bundled tests, brittle if the suite grows.

### References

- Assignment overview: `week1/assignment.md`
- Course context: root `README.md`

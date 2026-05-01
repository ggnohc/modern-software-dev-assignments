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

### References

- Assignment overview: `week1/assignment.md`
- Course context: root `README.md`

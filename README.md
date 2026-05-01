# Assignments for CS146S: The Modern Software Developer

This is the home of the assignments for [CS146S: The Modern Software Developer](https://themodernsoftware.dev), taught at Stanford University fall 2025.

## Repo Setup
These steps work with Python 3.12.

1. Install Python 3.12
   - macOS: `brew install python@3.12`
   - Linux: use your distro's package manager (e.g. `sudo apt install python3.12 python3.12-venv`)
   - Windows: download from [python.org](https://www.python.org/downloads/)
   - Verify: `python3.12 --version`

2. Create and activate a virtual environment (Python 3.12)
   From the repository root:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate          # macOS/Linux
   # .venv\Scripts\activate           # Windows (PowerShell: .venv\Scripts\Activate.ps1)
   ```
   To deactivate later, run `deactivate`.

3. Install Poetry (inside the activated venv)
   ```bash
   pip install --upgrade pip
   pip install poetry
   ```

4. Install project dependencies with Poetry (inside the activated venv)
   From the repository root:
   ```bash
   poetry install --no-interaction
   ```
   Poetry is configured (via `poetry.toml`) to use the in-project `.venv`, so it will install into the venv you just activated.

> **Note:** The `.venv` must be activated in every new terminal before running any `poetry`, `pytest`, `uvicorn`, or other project commands. If you see `command not found` or `ModuleNotFoundError`, the most common cause is a non-activated venv — re-run `source .venv/bin/activate` from the repo root.
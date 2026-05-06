"""Application configuration loaded from environment / .env via pydantic-settings.

Single source of truth for runtime config. Other modules must call
``get_settings()`` rather than reading ``os.environ`` directly so that:

  - tests can override values by clearing the cache and overriding env
    (or by monkey-patching ``get_settings``),
  - the ``.env`` file is read exactly once per process,
  - configuration appears in OpenAPI / docs generation deterministically.

All env vars are prefixed with ``APP_`` to avoid collisions with system or
SDK-specific variables (e.g. plain ``OLLAMA_MODEL`` could be set by other
tooling). Use ``APP_DB_PATH``, ``APP_OLLAMA_MODEL``, ``APP_MAX_INPUT_CHARS``.
"""

from __future__ import annotations

import functools
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


_DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "app.db"


class Settings(BaseSettings):
    """Runtime configuration.

    Field defaults match the previous hardcoded values so behavior is
    unchanged for callers that don't set any env vars.
    """

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_path: Path = _DEFAULT_DB_PATH
    ollama_model: str = "llama3.2:3b"
    max_input_chars: int = 50_000


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide :class:`Settings` singleton.

    Cached for performance and to ensure ``.env`` is read once. Tests that
    need to override any field should call ``get_settings.cache_clear()``
    after mutating the environment, or monkeypatch this function directly.
    """
    return Settings()

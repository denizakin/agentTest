"""Utility helpers for loading project configuration.

This module is the single source of truth for environment-driven
configuration such as API credentials and database connection details.

Usage:
- Call ``load_env_file()`` once at startup to load ``resources/.env``.
- Use ``get_env`` for simple lookups.
- Use the convenience helpers like ``get_okx_api_config`` and
  ``get_database_url`` for normalized access.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - executed only when python-dotenv missing
    load_dotenv = None  # type: ignore[assignment]


def load_env_file(env_path: Optional[Path] = None) -> None:
    """
    Load environment variables from an .env file if python-dotenv is available.

    Parameters:
        env_path: Optional path to the .env file. Defaults to resources/.env.
    """
    if load_dotenv is None:
        return

    env_file = env_path or "resources/.env"
    if Path(env_file).exists():
        load_dotenv(env_file)


def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    """Fetch an environment variable with an optional default."""
    return os.getenv(name, default)


# ----- OKX API helpers -----

def get_okx_api_config() -> Dict[str, Optional[str]]:
    """Return OKX API-related configuration gathered from environment.

    Keys:
    - OKX_API_KEY
    - OKX_SECRET_KEY
    - OKX_PASSPHRASE
    - OKX_FLAG ("0" real, "1" demo)
    """
    return {
        "OKX_API_KEY": get_env("OKX_API_KEY"),
        "OKX_SECRET_KEY": get_env("OKX_SECRET_KEY"),
        "OKX_PASSPHRASE": get_env("OKX_PASSPHRASE"),
        "OKX_FLAG": get_env("OKX_FLAG", "0"),
    }


# ----- Database helpers -----

def get_database_url() -> Optional[str]:
    """Return a database URL for PostgreSQL/TimescaleDB.

    Prefers ``DATABASE_URL`` if present; otherwise constructs a DSN from:
    - DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
    """
    db_url = get_env("DATABASE_URL")
    if db_url:
        return db_url

    host = get_env("DB_HOST")
    port = get_env("DB_PORT") or "5432"
    name = get_env("DB_NAME")
    user = get_env("DB_USER")
    password = get_env("DB_PASSWORD")

    if not (host and name and user and password):
        return None

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"

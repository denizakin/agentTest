"""Utility helpers for loading project configuration."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

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

    env_file = env_path or Path(__file__).resolve().parents[2] / "resources" / ".env"
    if env_file.exists():
        load_dotenv(env_file)


def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    """Fetch an environment variable with an optional default."""
    return os.getenv(name, default)

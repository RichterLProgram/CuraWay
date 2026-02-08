from __future__ import annotations

import os

from pathlib import Path

from openai import OpenAI


DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _read_key_from_file(path_str: str | None) -> str | None:
    if not path_str:
        return None
    path = Path(path_str)
    if not path.exists():
        return None
    content = path.read_text(encoding="utf-8").strip()
    return content or None


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        api_key = _read_key_from_file(os.getenv("OPENAI_API_KEY_FILE"))
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set OPENAI_API_KEY or OPENAI_API_KEY_FILE."
        )
    return OpenAI(api_key=api_key)

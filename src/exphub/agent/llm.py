"""LLM provider abstraction for CrystalPilot agent.

Supports three backends via the LLM_PROVIDER env var:
  google  (default) — Google Gemini
  openrouter        — OpenRouter (OpenAI-compatible)
  ollama / local    — Local Ollama
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from pydantic import SecretStr

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy imports — missing packages won't crash at import time
# ---------------------------------------------------------------------------
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except Exception:
    ChatGoogleGenerativeAI = None  # type: ignore[assignment,misc]

try:
    from langchain_openai import ChatOpenAI as ChatOpenAI_openai
except Exception:
    ChatOpenAI_openai = None  # type: ignore[assignment,misc]

try:
    from langchain_ollama import ChatOllama
except Exception:
    ChatOllama = None  # type: ignore[assignment,misc]

# ---------------------------------------------------------------------------
# Env helpers
# ---------------------------------------------------------------------------
# .env lives at repo root (4 levels up from this file)
ENV_PATH = Path(__file__).resolve().parents[3] / ".env"


def _load_env_once() -> None:
    load_dotenv(dotenv_path=ENV_PATH if ENV_PATH.exists() else None, override=False)


def _require_key(name: str, friendly: str) -> str:
    _load_env_once()
    val = os.getenv(name)
    if not val:
        raise ValueError(f"{name} not found. {friendly}")
    return val


# ---------------------------------------------------------------------------
# Provider resolution
# ---------------------------------------------------------------------------
def get_configured_chat_model() -> BaseChatModel:
    """Return a LangChain chat model based on LLM_PROVIDER env var."""
    _load_env_once()
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider == "openrouter":
        if ChatOpenAI_openai is None:
            raise ImportError("langchain-openai is required for OpenRouter support")
        api_key = _require_key("OPENROUTER_API_KEY", "Set OPENROUTER_API_KEY in .env")
        model = os.getenv("OPENROUTER_MODEL", "gpt-4o-mini")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        return ChatOpenAI_openai(
            model=model,
            api_key=SecretStr(api_key),
            base_url=base_url,
            temperature=0.2,
        )

    if provider in ("local", "ollama"):
        if ChatOllama is None:
            raise ImportError("langchain-ollama is required for Ollama support")
        model = os.getenv("OLLAMA_MODEL_NAME", "gpt-oss:120b")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return ChatOllama(model=model, base_url=base_url, temperature=0.2)

    # Default: Google Gemini
    if ChatGoogleGenerativeAI is None:
        raise ImportError("langchain-google-genai is required for Gemini support")
    api_key = _require_key("GOOGLE_API_KEY", "Set GOOGLE_API_KEY in .env")
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=api_key,
        temperature=0.2,
    )

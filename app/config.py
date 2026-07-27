from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = "咳辨"
    api_base_url: str = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    model_name: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_mode: str = os.getenv("OPENAI_API_MODE", "chat_completions").strip().lower()
    mock_mode: bool = os.getenv("MOCK_MODE", "true").lower() in {"1", "true", "yes", "on"}
    request_timeout: float = float(os.getenv("LLM_TIMEOUT", "30"))

    @property
    def llm_enabled(self) -> bool:
        return bool(self.api_key) and not self.mock_mode

    @property
    def uses_responses_api(self) -> bool:
        return self.api_mode in {"responses", "response"}


@lru_cache
def get_settings() -> Settings:
    return Settings()

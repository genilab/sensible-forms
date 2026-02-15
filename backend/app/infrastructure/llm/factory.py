"""LLM client factory.

Chooses the best available provider at runtime.

Rules (example-friendly):
- If a Gemini API key is configured and the SDK is installed, use Gemini.
- Otherwise, fall back to a deterministic mock client so the app can run.
"""

from __future__ import annotations

from functools import lru_cache
import logging

from app.infrastructure.config.settings import settings
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.llm.mock import MockLLMClient


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    if settings.GEMINI_API_KEY:
        try:
            from app.infrastructure.llm.gemini import GeminiClient

            return GeminiClient()
        except Exception as e:
            # Keep example runnable even if the Gemini SDK isn't installed or init fails.
            logger.warning("Falling back to MockLLMClient (Gemini init failed): %s", e)
            return MockLLMClient()

    logger.info("Using MockLLMClient (no GEMINI_API_KEY/GOOGLE_API_KEY found)")

    return MockLLMClient()

"""LLM client factory.

Chooses the best available provider at runtime.

Rules (example-friendly):
- Prefer an OpenAI-compatible gateway (e.g. OwlChat/OpenUI) when configured.
- Otherwise, fall back to Gemini when configured.
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
    provider = (settings.LLM_PROVIDER or "auto").strip().lower()

    if provider in {"mock", "fake"}:
        logger.info("Using MockLLMClient (LLM_PROVIDER=%s)", provider)
        return MockLLMClient()

    openai_key_present = bool(settings.OPENAI_API_KEY)
    gemini_key_present = bool(settings.GEMINI_API_KEY)

    use_openai = provider in {"openai", "openui", "owlchat"} or (
        provider == "auto" and openai_key_present
    )
    use_gemini = provider in {"google", "genai", "gemini"} or (
        provider == "auto" and (not openai_key_present) and gemini_key_present
    )

    if use_openai:
        if not openai_key_present:
            raise RuntimeError("OPENAI_API_KEY is not set but LLM_PROVIDER=openai was requested.")

        try:
            from app.infrastructure.llm.openai_compat import OpenAICompatibleClient

            logger.info("Using OpenAICompatibleClient (model=%s)", settings.OPENAI_MODEL)
            return OpenAICompatibleClient()
        except Exception as e:
            if provider == "auto":
                logger.warning("OpenAI client init failed: %s", e)

                # Preserve desired fallback order: OpenAI -> Gemini -> Mock
                if gemini_key_present:
                    try:
                        from app.infrastructure.llm.gemini import GeminiClient

                        logger.info("Falling back to GeminiClient (model=%s)", settings.DEFAULT_MODEL)
                        return GeminiClient()
                    except Exception as gemini_error:
                        logger.warning("Gemini init also failed: %s", gemini_error)

                logger.warning("Falling back to MockLLMClient (no usable LLM provider)")
                return MockLLMClient()
            raise

    if use_gemini:
        if not gemini_key_present:
            raise RuntimeError("GEMINI_API_KEY is not set but LLM_PROVIDER=gemini was requested.")

        try:
            from app.infrastructure.llm.gemini import GeminiClient

            logger.info("Using GeminiClient (model=%s)", settings.DEFAULT_MODEL)
            return GeminiClient()
        except Exception as e:
            if provider == "auto":
                # Keep example runnable even if the Gemini SDK isn't installed or init fails.
                logger.warning("Falling back to MockLLMClient (Gemini init failed): %s", e)
                return MockLLMClient()
            raise

    if provider not in {
        "auto",
        "mock",
        "fake",
        "openai",
        "openui",
        "owlchat",
        "google",
        "genai",
        "gemini",
    }:
        raise RuntimeError(
            f"Unknown LLM_PROVIDER value: {settings.LLM_PROVIDER!r}. "
            "Valid options are: auto; mock (alias: fake); "
            "openai-compatible (values: openai, openui, owlchat); "
            "gemini (aliases: google, genai)."
        )

    logger.info("Using MockLLMClient (no OPENAI_API_KEY or GEMINI_API_KEY found)")
    return MockLLMClient()

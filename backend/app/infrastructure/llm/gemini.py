"""
Gemini LLM Client Implementation.

Responsible for:
- Communicating with the Gemini API
- Formatting requests
- Handling responses
- Managing provider-specific behavior

Implements the LLM client interface specific to the Gemini provider. This allows the application to interact with Gemini as an LLM provider while adhering to a common interface used across different providers (in client.py).
"""

# Example Code:
from __future__ import annotations

from typing import Any, Optional

from app.infrastructure.llm.client import LLMClient
from app.infrastructure.config.settings import settings
from app.infrastructure.llm.langchain_messages import to_langchain_messages


class GeminiClient(LLMClient):
    def __init__(self, *, api_key: Optional[str] = None, model: Optional[str] = None):
        resolved_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        if not resolved_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your environment or a .env file (see infrastructure/config/settings.py)."
            )

        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as e:
            raise RuntimeError(
                "Gemini client requires LangChain's 'langchain-google-genai' package. "
                "Install it in your backend environment with: pip install langchain-google-genai"
            ) from e

        self._model_name = model or settings.DEFAULT_MODEL
        # Instantiate once; per-call params are applied via `.bind()`.
        self._llm = ChatGoogleGenerativeAI(
            google_api_key=resolved_key,
            model=self._model_name,
        )

    def invoke(
        self,
        messages,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
        config: dict | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            lc_messages = to_langchain_messages(messages)

            effective_max_output = (
                max_output_tokens if max_output_tokens is not None else max_tokens
            )

            bind_kwargs: dict[str, Any] = {**kwargs, "temperature": temperature}
            if effective_max_output is not None:
                bind_kwargs["max_output_tokens"] = effective_max_output

            result = self._llm.bind(**bind_kwargs).invoke(lc_messages, config=config)
            content = getattr(result, "content", None)
            return content if isinstance(content, str) else str(result)

        except Exception as e:
            raise RuntimeError(f"Gemini generation failed: {str(e)}")
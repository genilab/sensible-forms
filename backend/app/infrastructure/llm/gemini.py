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


class GeminiClient(LLMClient):
    def __init__(self, *, api_key: Optional[str] = None, model: Optional[str] = None):
        resolved_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        if not resolved_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your environment or a .env file (see infrastructure/config/settings.py)."
            )

        try:
            from google import genai
        except ImportError as e:
            raise RuntimeError(
                "Gemini client requires the 'google-genai' package. Install it in your backend environment."
            ) from e

        self._client = genai.Client(api_key=resolved_key)
        self._model_name = model or settings.DEFAULT_MODEL

    def invoke(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 512,
        **kwargs: Any,
    ) -> str:
        try:
            config: dict[str, Any] = {"temperature": temperature}
            if max_tokens is not None:
                config["max_output_tokens"] = max_tokens

            # `kwargs` can include provider-specific config fields.
            response = self._client.models.generate_content(
                model=self._model_name,
                contents=prompt,
                config={**config, **kwargs},
            )

            # The SDK returns a structured response; `.text` is the common convenience accessor.
            return response.text

        except Exception as e:
            # You could raise a custom domain exception here
            raise RuntimeError(f"Gemini generation failed: {str(e)}")
"""
LLM Client Abstraction

Defines a provider-agnostic interface for interacting with
large language models.

This file ensures:
- The rest of the application does NOT depend on a specific LLM vendor
- We can swap providers (Gemini, OpenAI, Anthropic, etc.)
  without rewriting business logic
- Consistent error handling and response normalization

This layer should contain ZERO domain logic.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class LLMClient(ABC):
    """Provider-agnostic LLM interface.

    The rest of the app should depend on this interface only.

    Notes:
    - `messages` may be a simple prompt string, or a message list (provider-specific).
    - Token parameter names differ by provider; prefer calling `invoke_llm()`.
    """

    def invoke_llm(
        self,
        messages: Any,
        *,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
        config: dict | None = None,
        **kwargs: Any,
    ) -> str:
        """Provider-agnostic invocation wrapper.

        This keeps call sites stable when switching between providers:
        - OpenAI-compatible chat endpoints (typically use `max_tokens`)
        - Gemini / Google GenAI (typically use `max_output_tokens`)

        Implementations decide how to map `max_output_tokens`.
        """

        call_kwargs: dict[str, Any] = {**kwargs}
        if temperature is not None:
            call_kwargs["temperature"] = temperature
        if max_output_tokens is not None:
            call_kwargs["max_output_tokens"] = max_output_tokens

        return self.invoke(messages, config=config, **call_kwargs)

    @abstractmethod
    def invoke(
        self,
        messages: Any,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
        config: dict | None = None,
        **kwargs: Any,
    ) -> str:
        """Invoke the underlying provider and return generated text."""
        raise NotImplementedError
"""OpenAI-compatible LLM client implementation.

This client talks to an OpenAI-compatible Chat Completions endpoint using LangChain.

It intentionally adheres to the project's minimal, provider-agnostic interface.

Configuration is read from `app.infrastructure.config.settings`:
- OPENAI_API_KEY
- OPENAI_BASE_URL: treated like the OpenAI SDK `base_url`
- OPENAI_MODEL
"""

from __future__ import annotations

from typing import Any, Optional

from app.infrastructure.config.settings import settings
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.llm.langchain_messages import to_langchain_messages


class OpenAICompatibleClient(LLMClient):
    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: float = 60.0,  # Magic Number: generous default timeout for OpenAI-compatible calls, which can sometimes be slow (e.g. with large context or tool calls)
    ):
        resolved_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        if not resolved_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to your environment or .env at the repository root."
            )

        resolved_base_url = (base_url if base_url is not None else settings.OPENAI_BASE_URL).strip()
        if not resolved_base_url:
            raise RuntimeError("OPENAI_BASE_URL is empty.")

        try:
            from langchain_openai import ChatOpenAI
        except ImportError as e:
            raise RuntimeError(
                "OpenAI-compatible client requires LangChain's 'langchain-openai' package. Install it with: pip install langchain-openai"
            ) from e 
        
        self._model = model or settings.OPENAI_MODEL
        # ChatOpenAI follows OpenAI semantics: base_url + /chat/completions.
        # This is compatible with OpenUI/OwlChat when base_url is set to the gateway's OpenAI route.
        self._llm = ChatOpenAI(
            api_key=resolved_key,
            base_url=resolved_base_url,
            model=self._model,
            timeout=timeout_seconds,
        )

    def invoke(
        self,
        messages,
        tools: list[Any] | None = None,
        temperature: float = 0.7,   # Magic Number: default temp for general chatbot responses <- Needs to be a core variable
        max_tokens: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
        config: dict | None = None,
        **kwargs: Any,
    ) -> Any:
        try:
            lc_messages = to_langchain_messages(messages)

            effective_max_tokens = max_tokens if max_tokens is not None else max_output_tokens

            bind_kwargs: dict[str, Any] = {**kwargs, "temperature": temperature}
            if effective_max_tokens is not None:
                bind_kwargs["max_tokens"] = effective_max_tokens

            llm = self._llm
            if tools:
                llm = llm.bind_tools(tools)

            result = llm.bind(**bind_kwargs).invoke(lc_messages, config=config)

            if tools:
                return result

            content = getattr(result, "content", None)
            return content if isinstance(content, str) else str(result)

        except Exception as e:
            raise RuntimeError(f"OpenAI-compatible generation failed: {str(e)}")

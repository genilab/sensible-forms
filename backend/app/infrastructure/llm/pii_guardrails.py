"""Global PII input redaction for LLM calls.

This module wraps an existing `LLMClient` and applies LangChain's built-in
PII guardrails *to inputs only* (redaction/anonymization) before any model call.

Why here?
- Keeps guardrails provider-agnostic (works for OpenAI-compatible, Gemini, Mock).
- Centralizes policy in one place (wire once in the LLM factory).

Notes:
- This redacts content sent to the model.
- It does not retroactively remove PII already stored in LangGraph state.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from app.infrastructure.llm.client import LLMClient
from app.infrastructure.llm.langchain_messages import to_langchain_messages


class PiiInputRedactor:
    """Redact PII from inputs before they are sent to a model.

    Uses LangChain's built-in `PIIMiddleware` with `apply_to_input=True`.

    Note: PIIMiddleware redacts the *last* HumanMessage in the message list.
    That matches this repo's prompt-building pattern (system + one user message).
    """

    def __init__(
        self,
        *,
        pii_types: Optional[Iterable[str]] = None,
        strategy: str = "redact",
    ):
        try:
            from langchain.agents.middleware import PIIMiddleware
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "PII guardrails require LangChain's PIIMiddleware. "
                "Upgrade/install LangChain v1 middleware support (package: 'langchain')."
            ) from e

        resolved_types = list(pii_types) if pii_types is not None else [
            "email",
            "credit_card",
            "ip",
            "mac_address",
            "url",
        ]

        self._middleware = [
            PIIMiddleware(
                pii_type,
                strategy=strategy,  # type: ignore[arg-type]
                apply_to_input=True,
                apply_to_output=False,
                apply_to_tool_results=False,
            )
            for pii_type in resolved_types
        ]

    def redact_messages(self, messages: Any) -> Any:
        lc_messages = to_langchain_messages(messages)
        state: dict[str, Any] = {"messages": lc_messages}

        for mw in self._middleware:
            update = mw.before_model(state, runtime=None)  # runtime isn't used internally
            if update and "messages" in update:
                state["messages"] = update["messages"]

        return state["messages"]

    def redact_text(self, text: str) -> str:
        redacted_messages = self.redact_messages(text)
        if isinstance(redacted_messages, list) and redacted_messages:
            content = getattr(redacted_messages[-1], "content", None)
            if isinstance(content, str):
                return content
        return str(text)


class PiiRedactingLLMClient(LLMClient):
    """An `LLMClient` decorator that redacts PII in user inputs."""

    def __init__(
        self,
        inner: LLMClient,
        *,
        pii_types: Optional[Iterable[str]] = None,
        strategy: str = "redact",
    ):
        self._inner = inner

        self._redactor = PiiInputRedactor(pii_types=pii_types, strategy=strategy)

    def invoke(
        self,
        messages: Any,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
        config: dict | None = None,
        **kwargs: Any,
    ) -> str:
        redacted = self._redactor.redact_messages(messages)
        return self._inner.invoke(
            redacted,
            temperature=temperature,
            max_tokens=max_tokens,
            max_output_tokens=max_output_tokens,
            config=config,
            **kwargs,
        )

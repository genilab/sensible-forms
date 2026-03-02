from __future__ import annotations

from typing import Any, Optional

import pytest

from app.infrastructure.llm.client import LLMClient
from app.infrastructure.llm.pii_guardrails import PiiRedactingLLMClient


class CapturingLLMClient(LLMClient):
    def __init__(self):
        self.last_messages: Any = None

    def invoke(
        self,
        messages: Any,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
        config: dict | None = None,
        **kwargs: Any,
    ) -> str:
        self.last_messages = messages
        return "ok"


def _flatten_contents(messages: Any) -> str:
    if isinstance(messages, str):
        return messages

    if isinstance(messages, list):
        parts: list[str] = []
        for item in messages:
            if isinstance(item, dict):
                parts.append(str(item.get("content") or ""))
            else:
                content = getattr(item, "content", None)
                parts.append(str(content) if content is not None else str(item))
        return "\n".join(parts)

    return str(messages)


def test_pii_redaction_on_input_messages():
    inner = CapturingLLMClient()
    guarded = PiiRedactingLLMClient(inner)

    guarded.invoke(
        [
            {
                "role": "user",
                "content": "My email is john.doe@example.com and my card is 5105-1051-0510-5100",
            }
        ]
    )

    sent = _flatten_contents(inner.last_messages)
    assert "john.doe@example.com" not in sent
    assert "5105-1051-0510-5100" not in sent
    assert "REDACTED" in sent


@pytest.mark.parametrize(
    "prompt",
    [
        "Email: jane@example.com",
        "Card: 5105-1051-0510-5100",
    ],
)
def test_pii_redaction_on_input_string(prompt: str):
    inner = CapturingLLMClient()
    guarded = PiiRedactingLLMClient(inner)

    guarded.invoke(prompt)

    sent = _flatten_contents(inner.last_messages)
    assert "example.com" not in sent
    assert "5105-1051-0510-5100" not in sent
    assert "REDACTED" in sent

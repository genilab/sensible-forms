import pytest

from app.infrastructure.llm.client import LLMClient


class CapturingClient(LLMClient):
    def __init__(self):
        self.last_call = None

    def invoke(
        self,
        messages,
        tools=None,
        temperature: float = 0.7,
        max_tokens=None,
        max_output_tokens=None,
        config: dict | None = None,
        **kwargs,
    ):
        self.last_call = {
            "messages": messages,
            "tools": tools,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "max_output_tokens": max_output_tokens,
            "config": config,
            "kwargs": kwargs,
        }
        return "ok"


def test_invoke_llm_forwards_config_and_kwargs():
    client = CapturingClient()

    result = client.invoke_llm(
        "hello",
        config={"trace_id": "t1"},
        max_tokens=123,
        extra="value",
    )

    assert result == "ok"
    assert client.last_call["messages"] == "hello"
    assert client.last_call["config"] == {"trace_id": "t1"}
    assert client.last_call["max_tokens"] == 123
    assert client.last_call["kwargs"]["extra"] == "value"


def test_invoke_llm_sets_temperature_and_max_output_tokens_when_provided():
    client = CapturingClient()

    client.invoke_llm(
        "hi",
        temperature=0.2,
        max_output_tokens=50,
    )

    assert client.last_call["temperature"] == 0.2
    assert client.last_call["max_output_tokens"] == 50


def test_invoke_llm_does_not_override_defaults_when_none():
    client = CapturingClient()

    # Both kwargs are None, so wrapper should not pass them;
    # we should see the defaults from `invoke`.
    client.invoke_llm("hi")

    assert client.last_call["temperature"] == 0.7
    assert client.last_call["max_output_tokens"] is None


def test_invoke_llm_can_forward_max_tokens_and_max_output_tokens_together():
    client = CapturingClient()

    client.invoke_llm(
        "hi",
        temperature=0.3,
        max_output_tokens=10,
        max_tokens=7,
    )

    assert client.last_call["temperature"] == 0.3
    assert client.last_call["max_output_tokens"] == 10
    assert client.last_call["max_tokens"] == 7


def test_base_invoke_raises_not_implemented_error():
    # Can't instantiate LLMClient directly (abstract), but we can still
    # exercise the base method body to cover the explicit raise.
    dummy = object()
    with pytest.raises(NotImplementedError):
        LLMClient.invoke(dummy, "hi")

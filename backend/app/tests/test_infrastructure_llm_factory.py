import sys
from types import ModuleType

import pytest

from app.infrastructure.config.settings import settings
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.llm.factory import get_llm_client
from app.infrastructure.llm.mock import MockLLMClient


class _BaseFakeClient(LLMClient):
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
        return "ok"


class _CapturingClient(LLMClient):
    def __init__(self):
        self.last = None

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
        self.last = {
            "messages": messages,
            "tools": tools,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "max_output_tokens": max_output_tokens,
            "config": config,
            "kwargs": kwargs,
        }
        return "ok"


def _install_fake_module(monkeypatch: pytest.MonkeyPatch, module_name: str, **attrs) -> None:
    mod = ModuleType(module_name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    monkeypatch.setitem(sys.modules, module_name, mod)


# Factory tests share an LRU-cached getter; clear it between tests for isolation.
@pytest.fixture(autouse=True)
def _reset_llm_factory_cache():
    # `get_llm_client` is LRU-cached; isolate tests.
    get_llm_client.cache_clear()
    yield
    get_llm_client.cache_clear()


# LLM factory: mock provider returns MockLLMClient.
def test_provider_mock_returns_mock(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")

    client = get_llm_client()
    assert isinstance(client, MockLLMClient)


# LLM factory: openai provider requires OPENAI_API_KEY.
def test_openai_missing_key_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not set"):
        get_llm_client()


# LLM factory: openai provider uses the OpenAI-compatible client implementation when available.
def test_openai_success_uses_openai_compat(monkeypatch: pytest.MonkeyPatch):
    class FakeOpenAICompatibleClient(_BaseFakeClient):
        pass

    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")

    _install_fake_module(
        monkeypatch,
        "app.infrastructure.llm.openai_compat",
        OpenAICompatibleClient=FakeOpenAICompatibleClient,
    )

    client = get_llm_client()
    assert isinstance(client, FakeOpenAICompatibleClient)


# LLM factory: auto provider falls back to Gemini when OpenAI client init fails.
def test_auto_openai_init_failure_falls_back_to_gemini(monkeypatch: pytest.MonkeyPatch):
    class FailingOpenAIClient(_BaseFakeClient):
        def __init__(self):
            raise RuntimeError("boom")

    class FakeGeminiClient(_BaseFakeClient):
        pass

    monkeypatch.setattr(settings, "LLM_PROVIDER", "auto")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini")

    _install_fake_module(
        monkeypatch,
        "app.infrastructure.llm.openai_compat",
        OpenAICompatibleClient=FailingOpenAIClient,
    )
    _install_fake_module(
        monkeypatch,
        "app.infrastructure.llm.gemini",
        GeminiClient=FakeGeminiClient,
    )

    client = get_llm_client()
    assert isinstance(client, FakeGeminiClient)


# LLM factory: auto provider falls back to Mock when both OpenAI and Gemini fail.
def test_auto_openai_and_gemini_fail_falls_back_to_mock(monkeypatch: pytest.MonkeyPatch):
    class FailingOpenAIClient(_BaseFakeClient):
        def __init__(self):
            raise RuntimeError("boom")

    class FailingGeminiClient(_BaseFakeClient):
        def __init__(self):
            raise RuntimeError("also boom")

    monkeypatch.setattr(settings, "LLM_PROVIDER", "auto")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini")

    _install_fake_module(
        monkeypatch,
        "app.infrastructure.llm.openai_compat",
        OpenAICompatibleClient=FailingOpenAIClient,
    )
    _install_fake_module(
        monkeypatch,
        "app.infrastructure.llm.gemini",
        GeminiClient=FailingGeminiClient,
    )

    client = get_llm_client()
    assert isinstance(client, MockLLMClient)


# LLM factory: gemini provider requires GEMINI_API_KEY.
def test_gemini_missing_key_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not set"):
        get_llm_client()


# LLM factory: gemini provider uses GeminiClient when available.
def test_gemini_success_uses_gemini_client(monkeypatch: pytest.MonkeyPatch):
    class FakeGeminiClient(_BaseFakeClient):
        pass

    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini")

    _install_fake_module(monkeypatch, "app.infrastructure.llm.gemini", GeminiClient=FakeGeminiClient)

    client = get_llm_client()
    assert isinstance(client, FakeGeminiClient)


# LLM factory: auto provider falls back to Mock when Gemini init fails and OpenAI key is absent.
def test_auto_gemini_init_failure_falls_back_to_mock(monkeypatch: pytest.MonkeyPatch):
    class FailingGeminiClient(_BaseFakeClient):
        def __init__(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(settings, "LLM_PROVIDER", "auto")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini")

    _install_fake_module(monkeypatch, "app.infrastructure.llm.gemini", GeminiClient=FailingGeminiClient)

    client = get_llm_client()
    assert isinstance(client, MockLLMClient)


# LLM factory: rejects unknown provider values.
def test_unknown_provider_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "definitely-not-real")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    with pytest.raises(RuntimeError, match="Unknown LLM_PROVIDER"):
        get_llm_client()


# LLMClient.invoke_llm (factory path): forwards optional params and kwargs through the wrapper.
def test_client_invoke_llm_forwards_kwargs_and_optional_params():
    client = _CapturingClient()

    result = client.invoke_llm(
        "hello",
        config={"trace": "1"},
        temperature=0.2,
        max_output_tokens=50,
        max_tokens=7,
        extra="value",
    )

    assert result == "ok"
    assert client.last["messages"] == "hello"
    assert client.last["config"] == {"trace": "1"}
    assert client.last["temperature"] == 0.2
    assert client.last["max_output_tokens"] == 50
    assert client.last["max_tokens"] == 7
    assert client.last["kwargs"]["extra"] == "value"


# LLMClient.invoke: base method body raises NotImplementedError (explicit contract).
def test_client_base_invoke_raises_not_implemented_error():
    with pytest.raises(NotImplementedError):
        LLMClient.invoke(object(), "hi")

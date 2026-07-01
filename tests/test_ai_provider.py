from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from mcaoe.ai.provider import (
    get_api_key,
    ensure_env_template,
    SUPPORTED_PROVIDERS,
    create_provider,
    LLMProvider,
    GeminiProvider,
    OpenAIProvider,
)


def test_env_template_creation(tmp_path: Path) -> None:
    tpl = ensure_env_template(tmp_path)
    assert tpl.exists()
    content = tpl.read_text()
    for p in SUPPORTED_PROVIDERS:
        assert p.upper() in content


def test_get_api_key_none_by_default() -> None:
    for p in SUPPORTED_PROVIDERS:
        assert get_api_key(p) is None


def test_get_api_key_reads_env_var() -> None:
    with patch.dict("os.environ", {"MCAOE_GEMINI_API_KEY": "test-key-123"}, clear=True):
        key = get_api_key("gemini")
        assert key == "test-key-123"


def test_get_api_key_falls_back_to_short_env_var() -> None:
    with patch.dict("os.environ", {"GEMINI_API_KEY": "short-key"}, clear=True):
        key = get_api_key("gemini")
        assert key == "short-key"


def test_create_provider_default_is_gemini() -> None:
    provider = create_provider()
    assert isinstance(provider, GeminiProvider)


def test_create_provider_openai() -> None:
    provider = create_provider("gpt")
    assert isinstance(provider, OpenAIProvider)


def test_create_provider_unknown_falls_back_to_gemini() -> None:
    provider = create_provider("nonexistent")
    assert isinstance(provider, GeminiProvider)


def test_gemini_provider_name() -> None:
    provider = GeminiProvider()
    assert provider.name() == "gemini"


def test_gemini_generate_without_sdk_returns_unavailable() -> None:
    provider = GeminiProvider(api_key="test")
    with patch.object(provider, "_model", None):
        result = provider.generate("test prompt")
    assert "unavailable" in result.lower()


def test_openai_provider_name() -> None:
    provider = OpenAIProvider()
    assert provider.name() == "openai"


def test_openai_generate_without_sdk_returns_unavailable() -> None:
    provider = OpenAIProvider(api_key="test")
    with patch.object(provider, "_client", None):
        result = provider.generate("test prompt")
    assert "unavailable" in result.lower()


def test_llm_provider_is_abstract() -> None:
    import inspect
    assert inspect.isabstract(LLMProvider)

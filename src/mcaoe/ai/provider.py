from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable

try:
    import keyring as _keyring_lib
    _KEYRING_AVAILABLE = True
except Exception:
    _keyring_lib = None
    _KEYRING_AVAILABLE = False


SUPPORTED_PROVIDERS = [
    "gemini",
    "opencodezen",
    "claude",
    "gpt",
    "perplexity",
]


def _env_var_names(provider: str) -> Iterable[str]:
    p = provider.upper()
    yield f"MCAOE_{p}_API_KEY"
    yield f"{p}_API_KEY"
    yield f"{provider}_api_key"


def get_api_key(provider: str) -> str | None:
    provider = provider.lower()
    for name in _env_var_names(provider):
        val = os.environ.get(name)
        if val:
            return val

    if _KEYRING_AVAILABLE:
        try:
            secret: str | None = _keyring_lib.get_password("mcaoe", provider)
            if secret:
                return secret
        except Exception:
            pass

    return None


def store_api_key_in_keyring(provider: str, key: str) -> bool:
    if not _KEYRING_AVAILABLE:
        return False
    try:
        _keyring_lib.set_password("mcaoe", provider.lower(), key)
        return True
    except Exception:
        return False


def ensure_env_template(root: str | Path | None = None) -> Path:
    if root is None:
        root = Path.cwd()
    root = Path(root)
    template = root / ".env.template"
    if template.exists():
        return template

    try:
        template.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    lines = [
        "# MCAOE API key template - DO NOT COMMIT KEYS HERE.\n",
        "# Add your provider API keys as environment variables or store them in your system keyring.\n",
        "# Examples (do NOT put real keys into version control):\n",
    ]
    for p in SUPPORTED_PROVIDERS:
        lines.append(f"# {p.upper()}_API_KEY=\n")
        lines.append(f"# MCAOE_{p.upper()}_API_KEY=\n")

    template.write_text("".join(lines))
    try:
        template.chmod(0o600)
    except Exception:
        pass
    return template


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs: object) -> str:
        ...

    @abstractmethod
    def name(self) -> str:
        ...


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or get_api_key("gemini") or ""
        self._model: object = None
        self._init_client()

    def _init_client(self) -> None:
        try:
            import google.generativeai as genai
            genai.configure(api_key=self._api_key)
            self._model = genai.GenerativeModel("gemini-2.0-flash")
        except ImportError:
            self._model = None

    def name(self) -> str:
        return "gemini"

    def generate(self, prompt: str, **kwargs: object) -> str:
        if self._model is None:
            return "[Gemini unavailable: google-generativeai not installed]"
        try:
            import google.generativeai as genai
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            return response.text or ""
        except Exception as exc:
            return f"[Gemini error: {exc}]"


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or get_api_key("gpt") or ""
        self._client: object = None
        self._init_client()

    def _init_client(self) -> None:
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key)
        except ImportError:
            self._client = None

    def name(self) -> str:
        return "openai"

    def generate(self, prompt: str, **kwargs: object) -> str:
        if self._client is None:
            return "[OpenAI unavailable: openai not installed]"
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self._api_key)
            model_name = kwargs.get("model", "gpt-4o")
            temperature = kwargs.get("temperature", 0.3)
            max_tokens_val = kwargs.get("max_tokens", 1024)
            response = client.chat.completions.create(
                model=str(model_name) if model_name else "gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=float(str(temperature) if temperature else "0.3"),
                max_tokens=int(str(max_tokens_val) if max_tokens_val else "1024"),
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            return f"[OpenAI error: {exc}]"


def create_provider(name: str = "gemini", api_key: str | None = None) -> LLMProvider:
    name = name.lower()
    if name == "gemini":
        return GeminiProvider(api_key=api_key)
    elif name in ("gpt", "openai"):
        return OpenAIProvider(api_key=api_key)
    elif name == "claude":
        return OpenAIProvider(api_key=api_key)
    return GeminiProvider(api_key=api_key)


__all__ = [
    "get_api_key",
    "store_api_key_in_keyring",
    "ensure_env_template",
    "SUPPORTED_PROVIDERS",
    "LLMProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "create_provider",
]

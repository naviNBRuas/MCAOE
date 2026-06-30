from __future__ import annotations

import os
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
    # legacy or shorter forms
    yield f"{provider}_api_key"


def get_api_key(provider: str) -> str | None:
    """Return the API key for provider from environment or system keyring.

    Search order:
      1. Environment variables (MCAOE_<PROVIDER>_API_KEY, <PROVIDER>_API_KEY)
      2. System keyring (service: "mcaoe", username: <provider>) if available

    Does NOT write secrets to disk or to source.
    """
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
    """Store API key in system keyring (preferred). Returns True on success."""
    if not _KEYRING_AVAILABLE:
        return False
    try:
        _keyring_lib.set_password("mcaoe", provider.lower(), key)
        return True
    except Exception:
        return False


def ensure_env_template(root: str | Path | None = None) -> Path:
    """Create a `.env.template` in project root with placeholder lines for supported providers.

    This template is safe to commit (contains no secrets) and documents environment
    variables users should set. It will not create a `.env` with actual keys.
    """
    if root is None:
        root = Path.cwd()
    root = Path(root)
    template = root / ".env.template"
    if template.exists():
        return template

    # ensure parent directory exists
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
        # Attempt to set restrictive permissions (POSIX)
        template.chmod(0o600)
    except Exception:
        pass
    return template


__all__ = ["get_api_key", "store_api_key_in_keyring", "ensure_env_template", "SUPPORTED_PROVIDERS"]

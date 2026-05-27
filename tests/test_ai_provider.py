from __future__ import annotations

from pathlib import Path

from mcaoe.ai.provider import get_api_key, ensure_env_template, SUPPORTED_PROVIDERS


def test_env_template_creation(tmp_path: Path) -> None:
    tpl = ensure_env_template(tmp_path)
    assert tpl.exists()
    content = tpl.read_text()
    # ensure placeholders for providers are present
    for p in SUPPORTED_PROVIDERS:
        assert p.upper() in content


def test_get_api_key_none_by_default() -> None:
    for p in SUPPORTED_PROVIDERS:
        assert get_api_key(p) is None

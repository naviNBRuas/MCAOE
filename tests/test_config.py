from pathlib import Path

from mcaoe.config import AppSettings


def test_app_settings_defaults() -> None:
    settings = AppSettings()
    assert settings.session_name == "default"
    assert settings.database_path == Path(".mcaoe/mcaoe.sqlite3")
    assert settings.log_level == "INFO"
    assert settings.ui_enabled is True
    assert settings.ai_enabled is False
    assert settings.capability == "web_security"
    assert settings.docker_image == "blackarchlinux/blackarch"


def test_app_settings_custom_values() -> None:
    settings = AppSettings(
        session_name="test-session",
        database_path=Path("/tmp/test.db"),
        log_level="DEBUG",
        ui_enabled=False,
        ai_enabled=True,
        capability="infrastructure",
        docker_image="custom/image",
    )
    assert settings.session_name == "test-session"
    assert settings.database_path == Path("/tmp/test.db")
    assert settings.log_level == "DEBUG"
    assert settings.ui_enabled is False
    assert settings.ai_enabled is True
    assert settings.capability == "infrastructure"
    assert settings.docker_image == "custom/image"


def test_app_settings_from_yaml_with_data(tmp_path: Path) -> None:
    from unittest.mock import MagicMock, patch

    fake_yaml = MagicMock()
    fake_yaml.safe_load.return_value = {"session_name": "yaml-test", "capability": "infrastructure"}

    yaml_path = tmp_path / "config.yml"
    yaml_path.write_text("session_name: yaml-test\ncapability: infrastructure\n")

    with patch("mcaoe.config._yaml", fake_yaml), patch("mcaoe.config._YAML_AVAILABLE", True):
        loaded = AppSettings.from_yaml(yaml_path)
        assert loaded.session_name == "yaml-test"
        assert loaded.capability == "infrastructure"


def test_app_settings_from_yaml_nonexistent(tmp_path: Path) -> None:
    loaded = AppSettings.from_yaml(tmp_path / "nonexistent.yml")
    assert loaded.session_name == "default"


def test_app_settings_to_yaml_creates_parent_dir(tmp_path: Path) -> None:
    nested = tmp_path / "sub" / "dir" / "config.yml"
    settings = AppSettings(session_name="nested")
    result = settings.to_yaml(nested)
    assert result.exists()


def test_app_settings_merge_env_overrides_session_name() -> None:
    import os
    settings = AppSettings(session_name="original")
    os.environ["MCAOE_SESSION_NAME"] = "env-override"
    try:
        settings.merge_env()
        assert settings.session_name == "env-override"
    finally:
        del os.environ["MCAOE_SESSION_NAME"]


def test_app_settings_merge_env_boolean_parsing() -> None:
    import os
    settings = AppSettings(ai_enabled=False)
    os.environ["MCAOE_AI_ENABLED"] = "true"
    try:
        settings.merge_env()
        assert settings.ai_enabled is True
    finally:
        del os.environ["MCAOE_AI_ENABLED"]

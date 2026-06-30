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

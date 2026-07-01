from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

try:
    import yaml as _yaml
    _YAML_AVAILABLE = True
except Exception:
    _YAML_AVAILABLE = False
    _yaml = None


@dataclass(slots=True)
class AppSettings:
    session_name: str = "default"
    database_path: Path = Path(".mcaoe/mcaoe.sqlite3")
    log_level: str = "INFO"
    ui_enabled: bool = True
    ai_enabled: bool = False
    capability: str = "web_security"
    docker_image: str = "blackarchlinux/blackarch"
    config_path: Path = Path(".mcaoe/config.yml")

    @classmethod
    def from_yaml(cls, path: str | Path | None = None) -> AppSettings:
        if not _YAML_AVAILABLE:
            return cls()
        resolved = Path(path) if path else Path(".mcaoe/config.yml")
        if not resolved.exists():
            return cls()
        try:
            raw = _yaml.safe_load(resolved.read_text())
            if not isinstance(raw, dict):
                return cls()
            valid_keys = {f.name for f in fields(cls)}
            filtered = {k: v for k, v in raw.items() if k in valid_keys}
            if "database_path" in filtered:
                filtered["database_path"] = Path(str(filtered["database_path"]))
            if "config_path" in filtered:
                filtered["config_path"] = Path(str(filtered["config_path"]))
            return cls(**filtered)
        except Exception:
            return cls()

    def to_yaml(self, path: str | Path | None = None) -> Path:
        resolved = Path(path) if path else self.config_path
        resolved.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {
            "session_name": self.session_name,
            "database_path": str(self.database_path),
            "log_level": self.log_level,
            "ui_enabled": self.ui_enabled,
            "ai_enabled": self.ai_enabled,
            "capability": self.capability,
            "docker_image": self.docker_image,
        }
        if _YAML_AVAILABLE:
            resolved.write_text(_yaml.safe_dump(data, default_flow_style=False))
        else:
            resolved.write_text("# MCAOE configuration\n")
        return resolved

    def merge_env(self) -> AppSettings:
        import os
        mapping: dict[str, str] = {
            "MCAOE_SESSION_NAME": "session_name",
            "MCAOE_DATABASE_PATH": "database_path",
            "MCAOE_LOG_LEVEL": "log_level",
            "MCAOE_UI_ENABLED": "ui_enabled",
            "MCAOE_AI_ENABLED": "ai_enabled",
            "MCAOE_CAPABILITY": "capability",
            "MCAOE_DOCKER_IMAGE": "docker_image",
        }
        for env_var, attr in mapping.items():
            val = os.environ.get(env_var)
            if val is not None:
                if attr in ("ui_enabled", "ai_enabled"):
                    setattr(self, attr, val.lower() in ("true", "1", "yes"))
                else:
                    setattr(self, attr, val)
        return self

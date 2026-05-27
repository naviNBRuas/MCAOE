from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppSettings:
    session_name: str = "default"
    database_path: Path = Path(".mcaoe/mcaoe.sqlite3")
    log_level: str = "INFO"
    ui_enabled: bool = True
    ai_enabled: bool = False
    capability: str = "web_security"
    docker_image: str = "blackarchlinux/blackarch"

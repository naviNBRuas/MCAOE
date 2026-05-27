from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from mcaoe.models.domain import Evidence, Technology


@dataclass(slots=True)
class WhatWebTechnology:
    name: str
    version: str | None = None
    confidence: float = 0.7
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WhatWebParseResult:
    technologies: list[WhatWebTechnology]
    evidence: list[Evidence]

    def summary(self) -> dict[str, int]:
        return {
            "technologies": len(self.technologies),
            "evidence": len(self.evidence),
        }


def parse_whatweb_output(output_text: str) -> WhatWebParseResult:
    output_text = output_text.strip()
    if not output_text:
        return WhatWebParseResult(technologies=[], evidence=[])

    parsed_json = _try_parse_json(output_text)
    if parsed_json is not None:
        return _parse_json_payload(parsed_json)

    return _parse_plaintext_output(output_text)


def _try_parse_json(output_text: str) -> Any | None:
    try:
        return json.loads(output_text)
    except json.JSONDecodeError:
        return None


def _parse_json_payload(payload: Any) -> WhatWebParseResult:
    technologies: list[WhatWebTechnology] = []
    evidence: list[Evidence] = [Evidence(source="whatweb", summary="Parsed WhatWeb JSON output", payload={"type": type(payload).__name__})]

    items = payload if isinstance(payload, list) else [payload]
    for item in items:
        if not isinstance(item, dict):
            continue

        target = str(item.get("target") or item.get("url") or item.get("host") or "unknown")
        plugins = item.get("plugins") or item.get("technologies") or item.get("matches") or {}
        if isinstance(plugins, dict):
            plugin_items = plugins.items()
        elif isinstance(plugins, list):
            plugin_items = ((str(entry), {}) for entry in plugins)
        else:
            plugin_items = []

        for name, details in plugin_items:
            version = None
            attributes: dict[str, Any] = {}
            if isinstance(details, dict):
                version = details.get("version") or details.get("string")
                attributes = dict(details)
            elif details not in (None, ""):
                version = str(details)
            technologies.append(WhatWebTechnology(name=str(name), version=version, attributes=attributes))

        evidence.append(
            Evidence(
                source="whatweb",
                summary=f"WhatWeb result for {target}",
                payload=item,
            )
        )

    return WhatWebParseResult(technologies=technologies, evidence=evidence)


def _parse_plaintext_output(output_text: str) -> WhatWebParseResult:
    technologies: list[WhatWebTechnology] = []
    evidence: list[Evidence] = []

    for line in output_text.splitlines():
        line = line.strip()
        if not line:
            continue
        evidence.append(Evidence(source="whatweb", summary="Parsed WhatWeb line", payload={"line": line}))
        for token in re.findall(r"\[([^\]]+)\]", line):
            if not token or token.isdigit():
                continue
            normalized = token.strip()
            if not normalized:
                continue
            if any(char.isalpha() for char in normalized) and "status" not in normalized.lower() and not normalized.lower().startswith("http"):
                technologies.append(WhatWebTechnology(name=normalized))

    return WhatWebParseResult(technologies=technologies, evidence=evidence)


def as_domain_technologies(result: WhatWebParseResult) -> list[Technology]:
    technologies: list[Technology] = []
    for item in result.technologies:
        technologies.append(Technology(name=item.name, confidence=item.confidence))
    return technologies
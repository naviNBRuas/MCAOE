from __future__ import annotations

import re
from dataclasses import dataclass, field

from mcaoe.models.domain import Evidence, Finding, Technology, Unknown


@dataclass(slots=True)
class NiktoParseResult:
    findings: list[Finding]
    evidence: list[Evidence]
    technologies: list[Technology] = field(default_factory=list)
    unknowns: list[Unknown] = field(default_factory=list)

    def summary(self) -> dict[str, int]:
        return {
            "findings": len(self.findings),
            "evidence": len(self.evidence),
            "technologies": len(self.technologies),
            "unknowns": len(self.unknowns),
        }


def parse_nikto_output(output_text: str) -> NiktoParseResult:
    output_text = output_text.strip()
    if not output_text:
        return NiktoParseResult(findings=[], evidence=[])

    findings: list[Finding] = []
    evidence: list[Evidence] = [Evidence(source="nikto", summary="Parsed Nikto output")]
    technologies: list[Technology] = []
    unknowns: list[Unknown] = []
    seen_titles: set[str] = set()

    for line in output_text.splitlines():
        line = line.strip()
        if not line:
            continue

        evidence.append(Evidence(source="nikto", summary="Parsed Nikto line", payload={"line": line}))
        normalized = line.lstrip("+").strip()

        server_match = re.search(r"(?:Server|X-Powered-By):\s*([^\n\r]+)", normalized, re.IGNORECASE)
        if server_match:
            technology_name = _normalize_technology_name(server_match.group(1))
            if technology_name:
                technologies.append(Technology(name=technology_name, confidence=0.7))

        if _looks_like_finding(normalized):
            title = _finding_title(normalized)
            if title.lower() not in seen_titles:
                seen_titles.add(title.lower())
                findings.append(
                    Finding(
                        title=title,
                        description=normalized,
                        severity=_severity_for_line(normalized),
                    )
                )

        if "missing" in normalized.lower() and "header" in normalized.lower():
            unknowns.append(
                Unknown(
                    label=normalized[:80],
                    details=normalized,
                    priority=2,
                )
            )

    return NiktoParseResult(
        findings=findings,
        evidence=evidence,
        technologies=_unique_technologies(technologies),
        unknowns=unknowns,
    )


def _looks_like_finding(line: str) -> bool:
    lowered = line.lower()
    return any(
        token in lowered
        for token in (
            "x-frame-options",
            "x-content-type-options",
            "directory indexing",
            "admin",
            "sql",
            "php",
            "cgi",
            "outdated",
            "vulnerab",
            "missing",
            "allowed methods",
        )
    )


def _finding_title(line: str) -> str:
    if "directory indexing" in line.lower():
        return "Directory indexing enabled"
    if "x-frame-options" in line.lower():
        return "Missing X-Frame-Options header"
    if "x-content-type-options" in line.lower():
        return "Missing X-Content-Type-Options header"
    if "allowed methods" in line.lower():
        return "Potentially risky HTTP methods exposed"
    return line[:120].rstrip(".")


def _severity_for_line(line: str) -> str:
    lowered = line.lower()
    if any(token in lowered for token in ("sql", "vulnerab", "outdated")):
        return "high"
    if any(token in lowered for token in ("directory indexing", "cgi", "admin")):
        return "medium"
    return "low"


def _normalize_technology_name(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None

    lowered = value.lower()
    if "nginx" in lowered:
        return "nginx"
    if "apache" in lowered:
        return "apache httpd"
    if "microsoft-iis" in lowered or "iis" in lowered:
        return "iis"
    if "php" in lowered:
        return "php"
    if "openssl" in lowered or "tls" in lowered:
        return "tls"
    return value.split("/")[0].strip().lower()


def _unique_technologies(values: list[Technology]) -> list[Technology]:
    unique: dict[str, Technology] = {}
    for item in values:
        key = item.name.lower()
        if key not in unique:
            unique[key] = item
    return list(unique.values())
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from mcaoe.models.domain import Evidence, Finding, Unknown


@dataclass(slots=True)
class FfufResult:
    url: str
    status: int | None = None
    length: int | None = None
    words: int | None = None
    lines: int | None = None
    redirect_location: str | None = None
    input_value: str | None = None
    content_type: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FfufParseResult:
    results: list[FfufResult]
    findings: list[Finding]
    evidence: list[Evidence]
    unknowns: list[Unknown] = field(default_factory=list)

    def summary(self) -> dict[str, int]:
        return {
            "results": len(self.results),
            "findings": len(self.findings),
            "evidence": len(self.evidence),
            "unknowns": len(self.unknowns),
        }


def parse_ffuf_output(output_text: str) -> FfufParseResult:
    output_text = output_text.strip()
    if not output_text:
        return FfufParseResult(results=[], findings=[], evidence=[])

    payload = _try_parse_json(output_text)
    if payload is not None:
        return _parse_json_payload(payload)

    return _parse_plaintext_output(output_text)


def _try_parse_json(output_text: str) -> Any | None:
    try:
        return json.loads(output_text)
    except json.JSONDecodeError:
        return None


def _parse_json_payload(payload: Any) -> FfufParseResult:
    evidence: list[Evidence] = [Evidence(source="ffuf", summary="Parsed FFUF JSON output", payload={"type": type(payload).__name__})]
    results: list[FfufResult] = []
    findings: list[Finding] = []
    unknowns: list[Unknown] = []

    items: list[Any]
    if isinstance(payload, dict):
        items = payload.get("results") or payload.get("matches") or []
        if not isinstance(items, list):
            items = []
    elif isinstance(payload, list):
        items = payload
    else:
        items = []

    for item in items:
        if not isinstance(item, dict):
            continue

        result = _result_from_mapping(item)
        results.append(result)
        evidence.append(Evidence(source="ffuf", summary=f"FFUF result for {result.url}", payload=item))
        _classify_result(result, findings, unknowns)

    return FfufParseResult(results=results, findings=findings, evidence=evidence, unknowns=unknowns)


def _parse_plaintext_output(output_text: str) -> FfufParseResult:
    evidence: list[Evidence] = []
    results: list[FfufResult] = []
    findings: list[Finding] = []
    unknowns: list[Unknown] = []

    for line in output_text.splitlines():
        line = line.strip()
        if not line:
            continue
        evidence.append(Evidence(source="ffuf", summary="Parsed FFUF line", payload={"line": line}))
        result = _result_from_text_line(line)
        if result is None:
            continue
        results.append(result)
        _classify_result(result, findings, unknowns)

    return FfufParseResult(results=results, findings=findings, evidence=evidence, unknowns=unknowns)


def _result_from_mapping(item: dict[str, Any]) -> FfufResult:
    raw_url = item.get("url") or item.get("redirectlocation") or item.get("path") or "unknown"
    status = _int_or_none(item.get("status"))
    return FfufResult(
        url=str(raw_url),
        status=status,
        length=_int_or_none(item.get("length")),
        words=_int_or_none(item.get("words")),
        lines=_int_or_none(item.get("lines")),
        redirect_location=item.get("redirectlocation") or item.get("redirect_location"),
        input_value=_stringify(item.get("input")),
        content_type=_stringify(item.get("content-type") or item.get("content_type")),
        raw=dict(item),
    )


def _result_from_text_line(line: str) -> FfufResult | None:
    if not line.startswith("/") and "http" not in line.lower():
        return None

    parts = line.split()
    url = parts[0]
    status = _extract_bracketed_int(line, r"\[(\d{3})\]")
    length = _extract_bracketed_int(line, r"\[(\d+)\s+words?\]")
    words = _extract_bracketed_int(line, r"\[(\d+)\s+words?\]")
    lines = _extract_bracketed_int(line, r"\[(\d+)\s+lines?\]")
    return FfufResult(url=url, status=status, length=length, words=words, lines=lines, raw={"line": line})


def _classify_result(result: FfufResult, findings: list[Finding], unknowns: list[Unknown]) -> None:
    status = result.status
    if status in {200, 204, 206}:
        findings.append(
            Finding(
                title="Interesting content discovered",
                description=_describe_result(result),
                severity="informational",
            )
        )
    elif status in {401, 403}:
        findings.append(
            Finding(
                title="Restricted content discovered",
                description=_describe_result(result),
                severity="low",
            )
        )
    elif status in {301, 302, 307, 308}:
        unknowns.append(
            Unknown(
                label=f"Redirect discovered: {result.url}",
                details=_describe_result(result),
                priority=3,
            )
        )


def _describe_result(result: FfufResult) -> str:
    extras = []
    if result.length is not None:
        extras.append(f"length={result.length}")
    if result.words is not None:
        extras.append(f"words={result.words}")
    if result.lines is not None:
        extras.append(f"lines={result.lines}")
    if result.redirect_location:
        extras.append(f"redirect={result.redirect_location}")
    return f"{result.url} ({', '.join(extras) if extras else 'no metadata'})"


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _stringify(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _extract_bracketed_int(text: str, pattern: str) -> int | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if match is None:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None
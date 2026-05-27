#!/usr/bin/env python3
"""Dry-run smoke harness that exercises core flows across all CapabilityName values.

This script avoids executing external commands (no run/execution) and focuses on
plan-time logic, assistant summaries, reports, readiness checks, and policy decisions.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from mcaoe.ai.assistant import AnalystAssistant
from mcaoe.core.events import Event, EventType, EventBus
from mcaoe.execution.orchestrator import AnalystOrchestrator
from mcaoe.models.domain import CapabilityName, Session
from mcaoe.plugins.registry import PluginRegistry
from mcaoe.policy import SafetyPolicy
from mcaoe.graph.engine import KnowledgeGraphEngine
from mcaoe.recommendations.engine import RecommendationEngine
from mcaoe.database.store import SQLiteStore
from mcaoe.reports import build_session_report, render_session_report_markdown
from mcaoe.ui.readiness import render_readiness_scorecard


def run_capability_smoke() -> dict[str, dict]:
    results: dict[str, dict] = {}

    registry = PluginRegistry.with_defaults()
    bus = EventBus()
    policy = SafetyPolicy()
    graph = KnowledgeGraphEngine()
    recommendations = RecommendationEngine()

    for cap in CapabilityName:
        with tempfile.TemporaryDirectory(prefix="mcaoe-smoke-") as td:
            db_path = Path(td) / "mcaoe.sqlite3"
            store = SQLiteStore(db_path)
            orchestrator = AnalystOrchestrator(
                bus=bus,
                registry=registry,
                policy=policy,
                graph=graph,
                recommendations=recommendations,
                store=store,
            )

            assistant = AnalystAssistant()
            session = Session(name=f"smoke-{cap.value}", capability=cap)
            # seed a target so capability-specific plugin selection can work
            session.workflow.target = "https://example.com"
            session.targets.append("https://example.com")

            # Plan a single task for this capability (plan-only)
            try:
                # choose a plugin recommended for capability if present
                try:
                    from mcaoe.workflows import build_mvp_capability_profiles

                    profiles = {p.name: p for p in build_mvp_capability_profiles()}
                    profile = profiles.get(cap)
                    plugin_name = None
                    if profile and profile.recommended_plugins:
                        for name in profile.recommended_plugins:
                            if name in registry.plugins:
                                plugin_name = name
                                break
                except Exception:
                    plugin_name = None

                if not plugin_name:
                    plugin_name = next(iter(registry.plugins)) if registry.plugins else None

                plan = None
                if plugin_name:
                    plan = orchestrator.plan_tool_run(session, plugin_name, session.workflow.target)
                plan_status = bool(plan)
            except Exception as exc:  # plan errors should be captured
                plan_status = False
                plan = None
                print(f"[{cap.value}] plan error: {exc}")

            # Assistant summaries (no external calls)
            summary = assistant.summarize(session)
            card = assistant.session_card(session)

            # Build report (no executions)
            events = [Event(type=EventType.target_added, payload={"target": session.workflow.target})]
            report = build_session_report(session, events)
            md = render_session_report_markdown(report)

            readiness = render_readiness_scorecard(session)

            results[cap.value] = {
                "planable": plan_status,
                "assistant_summary_lines": summary.splitlines()[:5],
                "session_card": card,
                "report_markdown_head": md.splitlines()[:6],
                "readiness_lines": readiness[:6],
            }

    return results


if __name__ == "__main__":
    out = run_capability_smoke()
    for cap, data in out.items():
        print(f"== {cap} ==")
        print(f"planable: {data['planable']}")
        print("assistant:")
        for line in data["assistant_summary_lines"]:
            print("  ", line)
        print("readiness:")
        for line in data["readiness_lines"]:
            print("  ", line)
        print()
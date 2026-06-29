from __future__ import annotations

import asyncio
import argparse
from pathlib import Path

from mcaoe.ai import AnalystAssistant
from mcaoe.core.events import EventBus
from mcaoe.core.workflow import WorkflowEngine
from mcaoe.database.store import SQLiteStore
from mcaoe.execution.orchestrator import AnalystOrchestrator
from mcaoe.execution.provider import LocalExecutionProvider
from mcaoe.logging import configure_logging
from mcaoe.config import AppSettings
from mcaoe.graph.engine import KnowledgeGraphEngine
from mcaoe.models.domain import CapabilityName, Session
from mcaoe.observability import EventJournal, SessionReplay
from mcaoe.reports import build_session_report, render_session_report_json, render_session_report_markdown
from mcaoe.plugins.registry import PluginRegistry
from mcaoe.policy import SafetyPolicy
from mcaoe.recommendations.engine import RecommendationEngine
from mcaoe.workflows import build_mvp_capability_profiles
from mcaoe.runtime.docker import DockerExecutionProvider, DockerRuntimeManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mcaoe", description="MCAOE analyst workbench")
    parser.add_argument("--session-name", default="default", help="Session label to use in the local store")
    parser.add_argument("--database", default=".mcaoe/mcaoe.sqlite3", help="SQLite database path")
    parser.add_argument("--log-level", default="INFO", help="Structured log level")
    parser.add_argument("--capability", default="web_security", choices=[name.value for name in CapabilityName])
    parser.add_argument("--target", help="Target host, domain, or URL to work against")
    parser.add_argument(
        "--plugin",
        choices=["nmap", "whatweb", "nikto", "ffuf", "gobuster", "sslscan", "subfinder", "amass"],
        help="Plugin to plan or execute",
    )
    parser.add_argument("--execute", action="store_true", help="Execute the planned plugin task")
    parser.add_argument("--approve", action="store_true", help="Explicitly approve task execution")
    parser.add_argument("--list-profiles", action="store_true", help="Print available capability profiles and exit")
    parser.add_argument("--list-plugins", action="store_true", help="Print available plugins and exit")
    parser.add_argument("--no-ui", action="store_true", help="Run a headless summary instead of launching the UI")
    parser.add_argument("--dry-run", action="store_true", help="Print the scaffold summary and exit")
    parser.add_argument("--runtime", choices=["local", "docker"], default="local", help="Execution backend to use")
    parser.add_argument("--export-report", help="Write a session report to the given file path and exit")
    parser.add_argument("--report-format", choices=["markdown", "json"], default="markdown", help="Session report output format")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    configure_logging(args.log_level)

    settings = AppSettings(
        session_name=args.session_name,
        database_path=Path(args.database),
        log_level=args.log_level,
        ui_enabled=not args.no_ui,
        capability=args.capability,
    )

    capability = CapabilityName(settings.capability)
    session = Session(name=settings.session_name, capability=capability)
    if args.target:
        session.workflow.target = args.target
        if args.target not in session.targets:
            session.targets.append(args.target)
    bus = EventBus()
    journal = EventJournal()
    bus.subscribe_all(journal.append)
    workflow = WorkflowEngine(bus=bus)
    recommendation_engine = RecommendationEngine()
    recommendations = recommendation_engine.generate(session)
    session.recommendations = recommendations
    graph = KnowledgeGraphEngine()
    store = SQLiteStore(settings.database_path)
    assistant = AnalystAssistant()
    registry = PluginRegistry.with_defaults()
    policy = SafetyPolicy()
    runtime = DockerRuntimeManager()
    provider = LocalExecutionProvider() if args.runtime == "local" else DockerExecutionProvider(runtime)
    orchestrator = AnalystOrchestrator(
        bus=bus,
        registry=registry,
        policy=policy,
        graph=graph,
        recommendations=recommendation_engine,
        store=store,
        provider=provider,
    )
    store.save_session(session)

    if args.list_profiles:
        for profile in build_mvp_capability_profiles():
            print(f"{profile.name.value}: {profile.description}")
            print(f"  plugins: {', '.join(profile.recommended_plugins)}")
            print(f"  default stage: {profile.default_workflow_stage.value}")
        return

    if args.list_plugins:
        for plugin_name in sorted(registry.plugins):
            plugin = registry.plugins[plugin_name]
            metadata = getattr(plugin, "metadata", None)
            description = getattr(metadata, "description", "") if metadata is not None else ""
            print(f"{plugin_name}: {description}")
        return

    if args.dry_run:
        print("MCAOE scaffold ready")
        print(f"workflow_stage={workflow.state.stage.value}")
        print(f"recommendations={len(recommendations)}")
        print(f"graph_nodes={graph.summary()['nodes']}")
        print(f"plugins={','.join(sorted(registry.plugins))}")
        print(f"policy_requires_approval={policy.require_explicit_approval}")
        print(f"session_summary={orchestrator.summarize(session)}")
        print(f"events={len(journal.events)}")
        print(f"runtime_status={runtime.status().message}")
        replay = SessionReplay.from_session(session, journal.events)
        print(replay.summary())
        print("session_card=")
        for key, value in assistant.session_card(session).items():
            print(f"  {key}: {value}")
        for hint in assistant.next_steps(session):
            print(f"hint={hint}")
        print(assistant.summarize(session))
        return

    if args.export_report:
        report = build_session_report(session, journal.events)
        output_path = Path(args.export_report)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if args.report_format == "json":
            output_path.write_text(render_session_report_json(report), encoding="utf-8")
        else:
            output_path.write_text(render_session_report_markdown(report), encoding="utf-8")
        print(f"report_written={output_path}")
        print(f"coverage_score={report.coverage.coverage_score}")
        print(f"next_steps={len(report.next_steps)}")
        return

    if args.no_ui:
        if args.target:
            asyncio.run(orchestrator.record_target(session, args.target))
        if args.plugin and args.target:
            task = orchestrator.plan_tool_run(session, args.plugin, args.target)
            print(f"planned={task.command} {' '.join(task.arguments)}")
            if args.execute:
                if not args.approve:
                    raise SystemExit("Refusing to execute without --approve")
                result = asyncio.run(orchestrator.execute_planned_task(session, task, approved_by_user=True))
                print(f"exit_code={result['exit_code']}")
                if result["stdout"]:
                    print(result["stdout"])
                if result.get("stats"):
                    print(f"parsed_stats={result['stats']}")
                if result["stderr"]:
                    print(result["stderr"])
        print(f"workflow_stage={session.workflow.stage.value}")
        print(f"events={len(journal.events)}")
        print(f"runtime_status={runtime.status().message}")
        print("session_card=")
        for key, value in assistant.session_card(session).items():
            print(f"  {key}: {value}")
        print(assistant.summarize(session))
        return

    if settings.ui_enabled:
        from mcaoe.ui.app import MCAOEApp

        app = MCAOEApp(
            session=session,
            assistant=assistant,
            registry=registry,
            journal=journal,
            runtime=runtime,
            orchestrator=orchestrator,
        )
        app.run()
        return

    print(assistant.summarize(session))


if __name__ == "__main__":
    main()

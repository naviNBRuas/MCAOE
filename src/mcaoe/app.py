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


def _print_completion(shell: str) -> None:
    if shell == "bash":
        print(
            """_mcaoe_completion() {
    local cur opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    opts="--session-name --database --log-level --capability --target --plugin --execute --approve --list-profiles --list-plugins --no-ui --dry-run --runtime --export-report --export-session --import-session --report-format --list-sessions --delete-session --load-session --session-count --config --completion --help"
    COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
    return 0
}
complete -F _mcaoe_completion mcaoe"""
        )
    elif shell == "zsh":
        print(
            """#compdef mcaoe
_mcaoe() {
    local -a opts
    opts=(
        '--session-name:Session label'
        '--database:Database path'
        '--log-level:Log level'
        '--capability:Capability profile'
        '--target:Target host'
        '--plugin:Plugin name'
        '--execute:Execute task'
        '--approve:Approve execution'
        '--list-profiles:List profiles'
        '--list-plugins:List plugins'
        '--no-ui:Headless mode'
        '--dry-run:Print summary'
        '--runtime:Execution backend'
        '--export-report:Export report path'
        '--export-session:Export session ID'
        '--import-session:Import session file'
        '--report-format:Report format'
        '--list-sessions:List sessions'
        '--delete-session:Delete session'
        '--load-session:Load session'
        '--session-count:Session count'
        '--config:Config file path'
        '--completion:Shell type'
    )
    _arguments $opts
}
_mcaoe"""
        )
    elif shell == "fish":
        print(
            """complete -c mcaoe -l session-name -d 'Session label'
complete -c mcaoe -l database -d 'Database path'
complete -c mcaoe -l log-level -d 'Log level'
complete -c mcaoe -l capability -d 'Capability profile'
complete -c mcaoe -l target -d 'Target host'
complete -c mcaoe -l plugin -d 'Plugin name'
complete -c mcaoe -l execute -d 'Execute task'
complete -c mcaoe -l approve -d 'Approve execution'
complete -c mcaoe -l list-profiles -d 'List profiles'
complete -c mcaoe -l list-plugins -d 'List plugins'
complete -c mcaoe -l no-ui -d 'Headless mode'
complete -c mcaoe -l dry-run -d 'Print summary'
complete -c mcaoe -l runtime -d 'Execution backend'
complete -c mcaoe -l export-report -d 'Export report path'
complete -c mcaoe -l export-session -d 'Export session'
complete -c mcaoe -l import-session -d 'Import session'
complete -c mcaoe -l report-format -d 'Report format'
complete -c mcaoe -l list-sessions -d 'List sessions'
complete -c mcaoe -l delete-session -d 'Delete session'
complete -c mcaoe -l load-session -d 'Load session'
complete -c mcaoe -l session-count -d 'Session count'
complete -c mcaoe -l config -d 'Config file'
complete -c mcaoe -l completion -d 'Shell type'"""
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcaoe",
        description="MCAOE analyst workbench",
        epilog="Shell completion: eval \"$(mcaoe --completion bash)\"",
    )
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
    parser.add_argument("--export-session", help="Export a session to a JSON file by session ID and exit")
    parser.add_argument("--import-session", help="Import a session from a JSON file and exit")
    parser.add_argument("--report-format", choices=["markdown", "json"], default="markdown", help="Session report output format")
    parser.add_argument("--list-sessions", action="store_true", help="List all saved sessions and exit")
    parser.add_argument("--delete-session", help="Delete a session by its ID")
    parser.add_argument("--load-session", help="Load an existing session by its ID instead of creating a new one")
    parser.add_argument("--session-count", action="store_true", help="Print the number of saved sessions and exit")
    parser.add_argument("--config", help="Path to YAML config file (.mcaoe/config.yml by default)")
    parser.add_argument(
        "--completion",
        choices=["bash", "zsh", "fish"],
        help="Print shell completion script and exit",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.completion:
        _print_completion(args.completion)
        return

    configure_logging(args.log_level)

    config_path = Path(args.config) if args.config else Path(".mcaoe/config.yml")
    settings = AppSettings.from_yaml(config_path)
    settings.session_name = args.session_name
    settings.database_path = Path(args.database)
    settings.log_level = args.log_level
    settings.ui_enabled = not args.no_ui
    settings.capability = args.capability
    settings.merge_env()
    settings.to_yaml(config_path)

    store = SQLiteStore(settings.database_path)

    if args.list_sessions:
        sessions = store.list_sessions()
        if not sessions:
            print("No saved sessions found.")
        else:
            for sid, name, cap, target in sessions:
                target_str = target or "no target"
                print(f"{sid}  {name}  [{cap}]  {target_str}")
        return

    if args.session_count:
        print(f"sessions={store.session_count()}")
        return

    if args.delete_session:
        if store.delete_session(args.delete_session):
            print(f"deleted={args.delete_session}")
        else:
            print(f"not_found={args.delete_session}")
        return

    if args.export_session:
        payload = store.export_session_json(args.export_session)
        if payload is None:
            print(f"not_found={args.export_session}")
        else:
            out = Path(f"session_{args.export_session}.json")
            out.write_text(payload, encoding="utf-8")
            print(f"exported={out}")
        return

    if args.import_session:
        src = Path(args.import_session)
        if not src.exists():
            print(f"not_found={src}")
        else:
            session = store.import_session_json(src.read_text(encoding="utf-8"))
            if session is not None:
                print(f"imported={session.id}  {session.name}")
            else:
                print("import_failed")
        return

    capability = CapabilityName(settings.capability)
    if args.load_session:
        loaded = store.load_session(args.load_session)
        if loaded is None:
            raise SystemExit(f"Session {args.load_session!r} not found in database.")
        session = loaded
    else:
        session = Session(name=settings.session_name, capability=capability)

    if args.target:
        session.add_target(args.target)
        session.workflow.target = args.target
    bus = EventBus()
    journal = EventJournal()
    bus.subscribe_all(journal.append)
    workflow = WorkflowEngine(bus=bus)
    recommendation_engine = RecommendationEngine()
    recommendations = recommendation_engine.generate(session)
    session.recommendations = recommendations
    graph = KnowledgeGraphEngine()
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

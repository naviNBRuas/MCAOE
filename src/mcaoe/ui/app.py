from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, RichLog, Static

from mcaoe.ai.assistant import AnalystAssistant
from mcaoe.execution.orchestrator import AnalystOrchestrator
from mcaoe.models.domain import Session
from mcaoe.observability import EventJournal, SessionReplay
from mcaoe.plugins.registry import PluginRegistry
from mcaoe.runtime.docker import DockerRuntimeManager
from mcaoe.ui.readiness import render_readiness_scorecard


class MCAOEApp(App):
    CSS = """
    Screen {
        layout: vertical;
        background: $surface;
    }

    #banner {
        border: round $accent;
        padding: 1;
        margin: 0 0 1 0;
        height: auto;
    }

    #main {
        height: 1fr;
    }

    #left, #center, #right, #bottom {
        border: round $accent;
        padding: 1;
        margin: 0 1 1 0;
    }

    #left {
        width: 1fr;
    }

    #center {
        width: 1fr;
    }

    #right {
        width: 1.25fr;
    }

    #bottom {
        height: 11;
    }

    .section-title {
        text-style: bold;
        color: $accent;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("a", "toggle_ai", "AI Hint"),
        Binding("p", "preview_task", "Preview Task"),
        Binding("enter", "execute_task", "Execute Task"),
    ]

    def __init__(
        self,
        session: Session,
        assistant: AnalystAssistant,
        registry: PluginRegistry,
        journal: EventJournal | None = None,
        runtime: DockerRuntimeManager | None = None,
        orchestrator: AnalystOrchestrator | None = None,
    ) -> None:
        super().__init__()
        self.session = session
        self.assistant = assistant
        self.registry = registry
        self.journal = journal
        self.runtime = runtime or DockerRuntimeManager()
        self.orchestrator = orchestrator
        self.planned_plugin: str | None = None
        self.planned_target: str | None = None
        self.planned_command: str | None = None
        self.planned_arguments: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="banner")
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield Static("AI Assistant / Recommendations", classes="section-title")
                yield RichLog(id="activity")
            with Vertical(id="center"):
                yield Static("Workflow / Graph / Unknowns", classes="section-title")
                yield RichLog(id="graph")
            with Vertical(id="right"):
                yield Static("Target Intelligence / Evidence", classes="section-title")
                yield RichLog(id="details")
        with Vertical(id="bottom"):
            yield Static("Execution / Event Trace", classes="section-title")
            yield RichLog(id="terminal")
        yield Footer()

    def on_mount(self) -> None:
        self.render_dashboard()

    def action_refresh(self) -> None:
        self.render_dashboard()
        self.query_one("#terminal", RichLog).write("Dashboard refreshed.")

    def action_toggle_ai(self) -> None:
        self.query_one("#activity", RichLog).write("AI assistant remains advisory-only by design.")

    def action_preview_task(self) -> None:
        target = self.session.workflow.target or (self.session.targets[0] if self.session.targets else None)
        if not target:
            self.query_one("#terminal", RichLog).write("No target is configured yet. Add one before previewing a task.")
            return

        plugin_name = self._select_preview_plugin()
        if plugin_name is None:
            self.query_one("#terminal", RichLog).write("No suitable plugin found for the current capability profile.")
            return

        if self.orchestrator is None:
            self.query_one("#terminal", RichLog).write("Task preview requires an orchestrator instance.")
            return

        task = self.orchestrator.plan_tool_run(self.session, plugin_name, target)
        self.planned_plugin = plugin_name
        self.planned_target = target
        self.planned_command = task.command
        self.planned_arguments = list(task.arguments)
        self.render_dashboard()

    async def action_execute_task(self) -> None:
        if self.orchestrator is None:
            self.query_one("#terminal", RichLog).write("Task execution requires an orchestrator instance.")
            return
        if self.planned_command is None or self.planned_plugin is None or self.planned_target is None:
            self.query_one("#terminal", RichLog).write("Preview a task first, then press Enter to execute it with approval.")
            return

        task = self.orchestrator.plan_tool_run(self.session, self.planned_plugin, self.planned_target)
        self.query_one("#terminal", RichLog).write(f"Executing approved task: {task.command} {' '.join(task.arguments)}")
        result = await self.orchestrator.execute_planned_task(self.session, task, approved_by_user=True)
        self.query_one("#terminal", RichLog).write(f"Exit code: {result['exit_code']}")
        if result["stdout"]:
            self.query_one("#terminal", RichLog).write(result["stdout"])
        if result.get("stats"):
            self.query_one("#terminal", RichLog).write(f"Parsed stats: {result['stats']}")
        if result["stderr"]:
            self.query_one("#terminal", RichLog).write(result["stderr"])
        self.planned_plugin = None
        self.planned_target = None
        self.planned_command = None
        self.planned_arguments = []
        self.render_dashboard()

    def _select_preview_plugin(self) -> str | None:
        recommended = []
        for profile in self.registry.plugins.values():
            metadata = getattr(profile, "metadata", None)
            if metadata is None:
                continue
            name = getattr(metadata, "name", None)
            if name:
                recommended.append(str(name))

        capability_plugins = self._capability_recommended_plugins()
        for plugin_name in capability_plugins:
            if plugin_name in self.registry.plugins:
                return plugin_name

        if recommended:
            return recommended[0]
        return None

    def _capability_recommended_plugins(self) -> list[str]:
        from mcaoe.workflows import build_mvp_capability_profiles

        profiles = {profile.name: profile for profile in build_mvp_capability_profiles()}
        profile = profiles.get(self.session.capability)
        if profile is None:
            return []
        return list(profile.recommended_plugins)

    def _write_task_preview(self, command: str, arguments: list[str]) -> None:
        terminal = self.query_one("#terminal", RichLog)
        terminal.write("Planned task preview:")
        terminal.write(f"- command: {command}")
        terminal.write(f"- arguments: {' '.join(arguments)}")
        terminal.write("Press Enter to execute with explicit approval.")



    def render_dashboard(self) -> None:
        self._set_banner()
        self._set_activity()
        self._set_workflow()
        self._set_details()
        self._set_execution()

    def _set_banner(self) -> None:
        summary = self.assistant.session_card(self.session)
        counts = summary["counts"]
        banner = self.query_one("#banner", Static)
        banner.update(
            f"[b]MCAOE[/b]  |  session={summary['session']}  |  capability={summary['capability']}  |  stage={summary['workflow_stage']}  |  "
            f"target={summary['target'] or 'unset'}  |  coverage={summary['coverage_score']}/100  |  targets={counts['targets']} hosts={counts['hosts']} services={counts['services']} tech={counts['technologies']} findings={counts['findings']} unknowns={counts['unknowns']}"
        )

    def _set_activity(self) -> None:
        activity = self.query_one("#activity", RichLog)
        activity.clear()
        activity.write(self.assistant.summarize(self.session))
        for highlight in self.assistant.highlights(self.session):
            activity.write(highlight)

    def _set_workflow(self) -> None:
        workflow = self.query_one("#graph", RichLog)
        workflow.clear()
        workflow.write(f"Capability: {self.session.capability.value}")
        workflow.write(f"Workflow stage: {self.session.workflow.stage.value}")
        workflow.write(f"Workflow notes: {len(self.session.workflow.notes)}")
        workflow.write(f"Unknowns tracked: {len(self.session.unknowns)}")
        workflow.write("")
        for line in render_readiness_scorecard(self.session):
            workflow.write(line)
        if self.session.unknowns:
            for unknown in self.session.unknowns[:5]:
                workflow.write(f"? {unknown.label} [priority {unknown.priority}]")
        if self.session.technologies:
            workflow.write("Technologies: " + ", ".join(technology.name for technology in self.session.technologies[:5]))

    def _set_details(self) -> None:
        details = self.query_one("#details", RichLog)
        details.clear()
        details.write(f"Plugins loaded: {', '.join(sorted(self.registry.plugins)) or 'none'}")
        details.write(self.runtime.status().message)
        recommendations = self.session.recommendations or []
        if recommendations:
            details.write("Recommendations:")
            for recommendation in recommendations[:5]:
                details.write(f"- {recommendation.title} ({recommendation.workflow_relevance or 'general'})")
        if self.session.evidence:
            details.write("Evidence:")
            for evidence in self.session.evidence[:5]:
                details.write(f"- {evidence.source}: {evidence.summary}")

    def _set_execution(self) -> None:
        terminal = self.query_one("#terminal", RichLog)
        terminal.clear()
        terminal.write("Execution output will appear here after approved tasks run.")
        if self.planned_command is not None:
            terminal.write("Planned task preview:")
            terminal.write(f"- command: {self.planned_command}")
            terminal.write(f"- arguments: {' '.join(self.planned_arguments)}")
            terminal.write("- action: press Enter to execute with explicit approval")
        if self.journal is not None and self.journal.events:
            terminal.write("Recent events:")
            recent = self.journal.as_dicts()[-5:]
            for event in recent:
                terminal.write(f"- {event['type']}: {event['payload']}")
            replay = SessionReplay.from_session(self.session, self.journal.events)
            terminal.write(replay.summary())
        else:
            terminal.write("No events recorded yet.")

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Label,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
    Tree,
)

from mcaoe.ai.assistant import AnalystAssistant
from mcaoe.execution.orchestrator import AnalystOrchestrator
from mcaoe.models.domain import Session
from mcaoe.observability import EventJournal
from mcaoe.plugins.registry import PluginRegistry
from mcaoe.runtime.docker import DockerRuntimeManager


APP_CSS = """
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

#activity-panel {
    border: round $accent;
    padding: 1;
    margin: 0 1 1 0;
    height: 1fr;
}

#execution-panel {
    border: round $accent;
    padding: 1;
    margin: 0 1 1 0;
    height: 8;
}

#docker-status {
    width: auto;
    min-width: 15;
    text-align: center;
}

.section-title {
    text-style: bold;
    color: $accent;
}

.host-table {
    height: 1fr;
}

.service-table {
    height: 1fr;
}

.finding-table {
    height: 1fr;
}

.knowledge-tree {
    height: 1fr;
}
"""


class TaskApprovalModal(ModalScreen[bool]):
    def __init__(self, command: str, arguments: list[str], target: str) -> None:
        super().__init__()
        self._command = command
        self._arguments = arguments
        self._target = target

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Approve Task Execution", classes="section-title"),
            Static(f"Target: {self._target}"),
            Static(f"Command: {self._command}"),
            Static(f"Arguments: {' '.join(self._arguments)}"),
            Horizontal(
                Button("Approve", variant="primary", id="approve"),
                Button("Cancel", variant="default", id="cancel"),
            ),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "approve":
            self.dismiss(True)
        else:
            self.dismiss(False)


class MCAOEApp(App[None]):
    CSS = APP_CSS

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("a", "toggle_ai", "AI Summary"),
        Binding("p", "preview_task", "Preview Task"),
        Binding("enter", "execute_task", "Execute Task"),
        Binding("d", "toggle_docker_logs", "Docker Logs"),
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
        yield Horizontal(Static(id="banner"), Static(id="docker-status"))
        with TabbedContent(id="main-tabs"):
            with TabPane("Inventory", id="tab-inventory"):
                with Horizontal():
                    DataTable(id="host-table", classes="host-table")
                    DataTable(id="service-table", classes="service-table")
            with TabPane("Findings", id="tab-findings"):
                DataTable(id="finding-table", classes="finding-table")
            with TabPane("Knowledge Graph", id="tab-graph"):
                Tree("Graph", id="knowledge-tree", classes="knowledge-tree")
            with TabPane("Activity", id="tab-activity"):
                RichLog(id="activity-log", highlight=True)
        with Vertical(id="execution-panel"):
            yield RichLog(id="terminal", max_lines=20)
        yield Footer()

    def on_mount(self) -> None:
        self._init_tables()
        self._init_tree()
        self.render_dashboard()

    def _init_tables(self) -> None:
        host_table = self.query_one("#host-table", DataTable)
        host_table.add_columns("Address", "Hostname", "Services", "Findings")
        for host in self.session.hosts:
            host_table.add_row(
                host.address,
                host.hostname or "unknown",
                str(len([s for s in self.session.services if str(s.host_id) == str(host.id)])),
                str(0),
            )

        service_table = self.query_one("#service-table", DataTable)
        service_table.add_columns("Port", "Protocol", "Name", "Version", "Host")
        for service in self.session.services:
            service_table.add_row(
                str(service.port),
                service.protocol,
                service.name,
                service.version or "?",
                str(service.host_id)[:8],
            )

        finding_table = self.query_one("#finding-table", DataTable)
        finding_table.add_columns("Title", "Severity", "Evidence")
        for finding in self.session.findings:
            finding_table.add_row(
                finding.title,
                finding.severity,
                str(len(finding.evidence_ids)),
            )

    def _init_tree(self) -> None:
        tree = self.query_one("#knowledge-tree", Tree)
        tree.root.expand()
        hosts_node = tree.root.add("Hosts")
        services_node = tree.root.add("Services")
        tech_node = tree.root.add("Technologies")
        findings_node = tree.root.add("Findings")
        unknowns_node = tree.root.add("Unknowns")

        seen_hosts: set[str] = set()
        for host in self.session.hosts:
            host_str = str(host.id)
            if host_str not in seen_hosts:
                hosts_node.add_leaf(f"{host.address} ({host_str[:8]})")
                seen_hosts.add(host_str)

        for service in self.session.services:
            label = f"{service.name}:{service.port}/{service.protocol}"
            if service.version:
                label += f" ({service.version})"
            services_node.add_leaf(label)

        for tech in self.session.technologies:
            tech_node.add_leaf(f"{tech.name} ({tech.confidence:.0%})")

        for finding in self.session.findings:
            findings_node.add_leaf(f"[{finding.severity}] {finding.title}")

        for unknown in self.session.unknowns:
            unknowns_node.add_leaf(f"{unknown.label} (p{unknown.priority})")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table_id = event.data_table.id
        if table_id == "host-table":
            self._update_activity(f"Selected host row: {event.row_key.value}")
        elif table_id == "service-table":
            self._update_activity(f"Selected service row: {event.row_key.value}")
        elif table_id == "finding-table":
            self._update_activity(f"Selected finding row: {event.row_key.value}")

    def action_refresh(self) -> None:
        self.render_dashboard()
        self._update_terminal("Dashboard refreshed.")

    def action_toggle_ai(self) -> None:
        summary = self.assistant.summarize(self.session)
        self._update_activity(summary)

    def action_preview_task(self) -> None:
        target = self.session.workflow.target or (self.session.targets[0] if self.session.targets else None)
        if not target:
            self._update_terminal("No target is configured yet. Add one before previewing a task.")
            return

        plugin_name = self._select_preview_plugin()
        if plugin_name is None:
            self._update_terminal("No suitable plugin found for the current capability profile.")
            return

        if self.orchestrator is None:
            self._update_terminal("Task preview requires an orchestrator instance.")
            return

        task = self.orchestrator.plan_tool_run(self.session, plugin_name, target)
        self.planned_plugin = plugin_name
        self.planned_target = target
        self.planned_command = task.command
        self.planned_arguments = list(task.arguments)
        self._update_terminal(f"Planned: {task.command} {' '.join(task.arguments)}")
        self._update_terminal("Press Enter to execute with approval.")

    async def action_execute_task(self) -> None:
        if self.orchestrator is None:
            self._update_terminal("Task execution requires an orchestrator instance.")
            return
        if self.planned_command is None or self.planned_plugin is None or self.planned_target is None:
            self._update_terminal("Preview a task first, then press Enter to execute it with approval.")
            return

        approved = await self.push_screen_wait(
            TaskApprovalModal(
                command=self.planned_command,
                arguments=self.planned_arguments,
                target=self.planned_target,
            )
        )
        if not approved:
            self._update_terminal("Task execution cancelled by user.")
            return

        task = self.orchestrator.plan_tool_run(self.session, self.planned_plugin, self.planned_target)
        self._update_terminal(f"Executing approved task: {task.command} {' '.join(task.arguments)}")
        result = await self.orchestrator.execute_planned_task(self.session, task, approved_by_user=True)
        self._update_terminal(f"Exit code: {result['exit_code']}")
        if result.get("stdout"):
            self._update_terminal(result["stdout"])
        if result.get("stats"):
            self._update_terminal(f"Parsed stats: {result['stats']}")
        if result.get("stderr"):
            self._update_terminal(result["stderr"])
        self.planned_plugin = None
        self.planned_target = None
        self.planned_command = None
        self.planned_arguments = []
        self.render_dashboard()

    def action_toggle_docker_logs(self) -> None:
        self._update_terminal(f"Docker: {self.runtime.status().message}")

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

    def render_dashboard(self) -> None:
        self._set_banner()
        self._set_docker_status()

    def _set_banner(self) -> None:
        summary: dict[str, object] = self.assistant.session_card(self.session)
        counts_raw = summary.get("counts", {})
        counts: dict[str, object] = counts_raw if isinstance(counts_raw, dict) else {}
        banner = self.query_one("#banner", Static)
        banner.update(
            f"[b]MCAOE[/b]  |  session={summary.get('session', '')}  |  capability={summary.get('capability', '')}  |  stage={summary.get('workflow_stage', '')}  |  "
            f"target={summary.get('target') or 'unset'}  |  coverage={summary.get('coverage_score', '?')}/100  |  "
            f"targets={counts.get('targets', 0)} hosts={counts.get('hosts', 0)} services={counts.get('services', 0)} "
            f"tech={counts.get('technologies', 0)} findings={counts.get('findings', 0)} unknowns={counts.get('unknowns', 0)}"
        )

    def _set_docker_status(self) -> None:
        status = self.runtime.status()
        docker_widget = self.query_one("#docker-status", Static)
        if status.healthy:
            docker_widget.update("[green]Docker: OK[/green]")
        else:
            docker_widget.update("[red]Docker: OFFLINE[/red]")

    def _update_activity(self, message: str) -> None:
        try:
            activity = self.query_one("#activity-log", RichLog)
            activity.write(message)
        except Exception:
            pass

    def _update_terminal(self, message: str) -> None:
        try:
            terminal = self.query_one("#terminal", RichLog)
            terminal.write(message)
        except Exception:
            pass

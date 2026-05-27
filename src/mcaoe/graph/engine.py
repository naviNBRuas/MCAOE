from __future__ import annotations

from dataclasses import dataclass, field

try:  # pragma: no cover - preferred path when dependency is installed
    import networkx as nx
except Exception:  # pragma: no cover - fallback used in minimal environments
    class _SimpleMultiDiGraph:
        def __init__(self) -> None:
            self.nodes: dict[object, dict[str, object]] = {}
            self.edges: list[tuple[object, object, dict[str, object]]] = []

        def add_node(self, node_id: object, **attrs: object) -> None:
            self.nodes[node_id] = dict(attrs)

        def add_edge(self, source: object, target: object, **attrs: object) -> None:
            self.edges.append((source, target, dict(attrs)))

        def number_of_nodes(self) -> int:
            return len(self.nodes)

        def number_of_edges(self) -> int:
            return len(self.edges)

    class nx:  # type: ignore[no-redef]
        MultiDiGraph = _SimpleMultiDiGraph

from mcaoe.models.domain import Evidence, Finding, Host, Service, Technology, Unknown


@dataclass(slots=True)
class KnowledgeGraphEngine:
    graph: nx.MultiDiGraph = field(default_factory=nx.MultiDiGraph)

    def add_host(self, host: Host) -> None:
        self.graph.add_node(host.id, kind="host", label=host.address, payload=host.model_dump())

    def add_service(self, service: Service) -> None:
        self.graph.add_node(
            service.id,
            kind="service",
            label=f"{service.name}:{service.port}/{service.protocol}",
            payload=service.model_dump(),
        )
        self.graph.add_edge(service.host_id, service.id, relation="hosts")

    def add_technology(self, technology: Technology) -> None:
        self.graph.add_node(
            technology.id,
            kind="technology",
            label=technology.name,
            payload=technology.model_dump(),
        )

    def add_evidence(self, evidence: Evidence) -> None:
        self.graph.add_node(
            evidence.id,
            kind="evidence",
            label=evidence.source,
            payload=evidence.model_dump(),
        )

    def add_finding(self, finding: Finding) -> None:
        self.graph.add_node(
            finding.id,
            kind="finding",
            label=finding.title,
            payload=finding.model_dump(),
        )

    def add_unknown(self, unknown: Unknown) -> None:
        self.graph.add_node(
            unknown.id,
            kind="unknown",
            label=unknown.label,
            payload=unknown.model_dump(),
        )

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {"nodes": self.graph.number_of_nodes(), "edges": self.graph.number_of_edges()}
        return counts

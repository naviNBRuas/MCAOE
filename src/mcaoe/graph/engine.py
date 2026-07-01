from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    import networkx as _nx
    _NETWORKX_AVAILABLE = True
except Exception:
    _NETWORKX_AVAILABLE = False

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

if _NETWORKX_AVAILABLE:
    _GraphClass: Any = _nx.MultiDiGraph
else:
    _GraphClass = _SimpleMultiDiGraph

from mcaoe.models.domain import Evidence, Finding, Host, Service, Technology, Unknown


@dataclass(slots=True)
class KnowledgeGraphEngine:
    graph: Any = field(default_factory=lambda: _GraphClass())

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

    def link_technology_to_host(self, technology: Technology, host: Host) -> None:
        self.graph.add_edge(host.id, technology.id, relation="runs")

    def link_finding_to_host(self, finding: Finding, host: Host) -> None:
        self.graph.add_edge(finding.id, host.id, relation="affects")

    def link_evidence_to_entity(self, evidence: Evidence, entity_id: str) -> None:
        self.graph.add_edge(evidence.id, entity_id, relation="references")

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {"nodes": self.graph.number_of_nodes(), "edges": self.graph.number_of_edges()}
        return counts

    def nodes_by_kind(self, kind: str) -> list[dict[str, object]]:
        nodes: list[dict[str, object]] = []
        for node_id, attrs in (self.graph.nodes.items() if hasattr(self.graph.nodes, "items") else []):
            if attrs.get("kind") == kind:
                nodes.append({"id": node_id, **attrs})
        return nodes

    def neighbors(self, node_id: str) -> list[dict[str, object]]:
        neighbors: list[dict[str, object]] = []
        for source, target, edge_attrs in graph_edges(self.graph):
            if source == node_id:
                node_data = self.graph.nodes.get(target, {})
                neighbors.append({"id": target, "relation": edge_attrs.get("relation", "connected"), **node_data})
            elif target == node_id:
                node_data = self.graph.nodes.get(source, {})
                neighbors.append({"id": source, "relation": edge_attrs.get("relation", "connected"), **node_data})
        return neighbors

    def paths_between(self, source_id: str, target_id: str, max_depth: int = 5) -> list[list[str]]:
        found: list[list[str]] = []
        _dfs_paths(self.graph, source_id, target_id, [], found, max_depth)
        return found


def graph_edges(graph: Any) -> list[tuple[str, str, dict[str, object]]]:
    edges: list[tuple[str, str, dict[str, object]]] = []
    if hasattr(graph, "edges") and callable(getattr(graph.edges, "data", None)):
        for source, target, data in graph.edges(data=True):
            edges.append((str(source), str(target), dict(data)))
    return edges


def _dfs_paths(
    graph: Any,
    current: str,
    target: str,
    path: list[str],
    found: list[list[str]],
    max_depth: int,
) -> None:
    if len(path) > max_depth:
        return
    path = [*path, current]
    if current == target:
        found.append(path)
        return
    if hasattr(graph, "edges"):
        for source, dest, _ in graph.edges(data=True):
            if str(source) == current and str(dest) not in path:
                _dfs_paths(graph, str(dest), target, path, found, max_depth)

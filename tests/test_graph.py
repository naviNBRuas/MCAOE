from uuid import uuid4

from mcaoe.graph.engine import KnowledgeGraphEngine, graph_edges, _dfs_paths
from mcaoe.models.domain import Evidence, Finding, Host, Service, Technology, Unknown


def _make_graph() -> tuple[KnowledgeGraphEngine, Host, Service, Technology, Finding]:
    eng = KnowledgeGraphEngine()
    host = Host(id=uuid4(), address="10.0.0.1")
    eng.add_host(host)
    svc = Service(id=uuid4(), host_id=host.id, name="http", port=80)
    eng.add_service(svc)
    tech = Technology(id=uuid4(), name="nginx")
    eng.add_technology(tech)
    eng.link_technology_to_host(tech, host)
    finding = Finding(id=uuid4(), title="Open port 80", description="Port 80 is open", severity="low")
    eng.add_finding(finding)
    eng.link_finding_to_host(finding, host)
    return eng, host, svc, tech, finding


def test_summary_counts_nodes_and_edges() -> None:
    eng, *_ = _make_graph()
    summary = eng.summary()
    assert summary["nodes"] >= 4
    assert summary["edges"] >= 2


def test_nodes_by_kind_returns_correct_type() -> None:
    eng, *_ = _make_graph()
    hosts = eng.nodes_by_kind("host")
    assert len(hosts) == 1
    assert hosts[0]["kind"] == "host"
    assert hosts[0]["label"] == "10.0.0.1"


def test_nodes_by_kind_services() -> None:
    eng, *_ = _make_graph()
    services = eng.nodes_by_kind("service")
    assert len(services) == 1
    assert "http:80/tcp" in str(services[0]["label"])


def test_nodes_by_kind_empty_for_missing_type() -> None:
    eng, *_ = _make_graph()
    assert eng.nodes_by_kind("nonexistent") == []


def test_neighbors_returns_connected_nodes() -> None:
    eng, host, *_ = _make_graph()
    neighbors = eng.neighbors(str(host.id))
    assert len(neighbors) >= 2
    relations = {n["relation"] for n in neighbors}
    assert "hosts" in relations
    assert "runs" in relations


def test_neighbors_empty_for_unknown_node() -> None:
    eng, *_ = _make_graph()
    assert eng.neighbors("nonexistent") == []


def test_paths_between_finds_direct_edge() -> None:
    eng, host, svc, *_ = _make_graph()
    paths = eng.paths_between(str(host.id), str(svc.id), max_depth=3)
    assert len(paths) >= 1


def test_add_evidence_and_link() -> None:
    eng = KnowledgeGraphEngine()
    host = Host(id=uuid4(), address="10.0.0.1")
    eng.add_host(host)
    evidence = Evidence(id=uuid4(), source="nmap scan", summary="port 22 open")
    eng.add_evidence(evidence)
    eng.link_evidence_to_entity(evidence, str(host.id))
    neighbors = eng.neighbors(str(host.id))
    assert len(neighbors) >= 1


def test_add_unknown() -> None:
    eng = KnowledgeGraphEngine()
    unknown = Unknown(id=uuid4(), label="TLS version", priority=2)
    eng.add_unknown(unknown)
    unknowns = eng.nodes_by_kind("unknown")
    assert len(unknowns) == 1
    assert unknowns[0]["label"] == "TLS version"


def test_graph_edges_empty_on_empty_graph() -> None:
    eng = KnowledgeGraphEngine()
    assert graph_edges(eng.graph) == []


def test_dfs_paths_max_depth_respected() -> None:
    eng = KnowledgeGraphEngine()
    h1 = Host(id=uuid4(), address="10.0.0.1")
    h2 = Host(id=uuid4(), address="10.0.0.2")
    eng.add_host(h1)
    eng.add_host(h2)
    eng.graph.add_edge(str(h1.id), str(h2.id), relation="connected")

    found: list[list[str]] = []
    _dfs_paths(eng.graph, str(h1.id), str(h2.id), [], found, max_depth=1)
    assert len(found) >= 1

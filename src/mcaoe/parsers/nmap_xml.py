from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, cast
from xml.etree import ElementTree as ET

from mcaoe.models.domain import Evidence, Host, Service, Technology


@dataclass(slots=True)
class NmapParseResult:
    hosts: list[Host]
    services: list[Service]
    evidence: list[Evidence]
    technologies: list[Technology] = field(default_factory=list)

    def summary(self) -> dict[str, int]:
        return {
            "hosts": len(self.hosts),
            "services": len(self.services),
            "evidence": len(self.evidence),
            "technologies": len(self.technologies),
        }


def parse_nmap_xml(xml_text: str) -> NmapParseResult:
    root = ET.fromstring(xml_text)
    hosts: list[Host] = []
    services: list[Service] = []
    evidence: list[Evidence] = [Evidence(source="nmap", summary="Parsed Nmap XML output")]
    technologies: list[Technology] = []
    technology_index: dict[str, Technology] = {}

    for host_node in root.findall(".//host"):
        status_node = host_node.find("status")
        if status_node is not None and status_node.get("state") != "up":
            continue
        address_node = host_node.find("address")
        if address_node is None or not address_node.get("addr"):
            continue

        hostname_node = host_node.find("hostnames/hostname")
        host = Host(address=address_node.get("addr", ""), hostname=hostname_node.get("name") if hostname_node is not None else None)
        hosts.append(host)
        evidence.append(
            Evidence(
                source="nmap",
                summary=f"Host discovered: {host.address}",
                payload={"address": host.address, "hostname": host.hostname},
            )
        )

        host_open_ports = 0

        for port_node in host_node.findall("ports/port"):
            state_node = port_node.find("state")
            if state_node is None or state_node.get("state") != "open":
                continue

            host_open_ports += 1
            port_id = int(port_node.get("portid", "0"))
            protocol = port_node.get("protocol", "tcp")
            service_node = port_node.find("service")
            service_name = service_node.get("name", "unknown") if service_node is not None else "unknown"
            product = service_node.get("product") if service_node is not None else None
            version = service_node.get("version") if service_node is not None else None
            services.append(
                Service(
                    host_id=host.id,
                    name=service_name,
                    port=port_id,
                    protocol=cast(Literal["tcp", "udp"], protocol if protocol in {"tcp", "udp"} else "tcp"),
                    product=product,
                    version=version,
                )
            )
            evidence.append(
                Evidence(
                    source="nmap",
                    summary=f"Open service discovered: {service_name} on {host.address}:{port_id}",
                    payload={
                        "address": host.address,
                        "port": port_id,
                        "protocol": protocol,
                        "service": service_name,
                        "product": product,
                        "version": version,
                    },
                )
            )

            for technology_name in _infer_technology_names(service_name, product):
                if technology_name in technology_index:
                    technology = technology_index[technology_name]
                else:
                    technology = Technology(name=technology_name, confidence=0.65)
                    technology_index[technology_name] = technology
                    technologies.append(technology)
                if evidence[-1].id not in technology.evidence_ids:
                    technology.evidence_ids.append(evidence[-1].id)

        evidence.append(
            Evidence(
                source="nmap",
                summary=f"Host scan summary for {host.address}",
                payload={
                    "address": host.address,
                    "hostname": host.hostname,
                    "open_ports": host_open_ports,
                },
            )
        )

    return NmapParseResult(hosts=hosts, services=services, evidence=evidence, technologies=technologies)


def _infer_technology_names(service_name: str, product: str | None) -> list[str]:
    values = {service_name.lower()}
    if product:
        values.add(product.lower())

    technologies: list[str] = []
    for value in values:
        if any(token in value for token in ("http", "https", "ssl/http", "web")):
            technologies.append("web service")
        if "nginx" in value:
            technologies.append("nginx")
        if "apache" in value:
            technologies.append("apache httpd")
        if "ssh" in value:
            technologies.append("ssh")
        if "openssl" in value or "tls" in value:
            technologies.append("tls")
        if "microsoft" in value or "iis" in value:
            technologies.append("iis")
    return sorted(dict.fromkeys(technologies))

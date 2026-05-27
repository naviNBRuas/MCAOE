from __future__ import annotations

from mcaoe.plugins.base import PluginMetadata
from mcaoe.plugins.templates import StaticCommandPlugin


def build_sslscan_plugin() -> StaticCommandPlugin:
    return StaticCommandPlugin(
        metadata=PluginMetadata(
            name="sslscan",
            description="TLS configuration and certificate inspection.",
            capability_tags=["infrastructure", "web_security", "tls"],
            risk_level="low",
        ),
        command="sslscan",
        argument_factory=lambda _session, target: [target],
    )


def build_subfinder_plugin() -> StaticCommandPlugin:
    return StaticCommandPlugin(
        metadata=PluginMetadata(
            name="subfinder",
            description="Passive subdomain discovery.",
            capability_tags=["osint", "recon", "infrastructure"],
            risk_level="low",
        ),
        command="subfinder",
        argument_factory=lambda _session, target: ["-d", target],
    )


def build_amass_plugin() -> StaticCommandPlugin:
    return StaticCommandPlugin(
        metadata=PluginMetadata(
            name="amass",
            description="Attack surface mapping and enumeration.",
            capability_tags=["osint", "recon", "infrastructure"],
            risk_level="medium",
        ),
        command="amass",
        argument_factory=lambda _session, target: ["enum", "-passive", "-d", target],
    )

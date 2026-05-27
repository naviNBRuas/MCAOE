from __future__ import annotations

from mcaoe.plugins.base import PluginMetadata
from mcaoe.plugins.templates import StaticCommandPlugin


def build_whatweb_plugin() -> StaticCommandPlugin:
    return StaticCommandPlugin(
        metadata=PluginMetadata(
            name="whatweb",
            description="Web fingerprinting and technology identification.",
            capability_tags=["web_security", "enumeration", "fingerprinting"],
            risk_level="low",
        ),
        command="whatweb",
        argument_factory=lambda _session, target: ["--color=never", "--log-json=-", target],
    )


def build_nikto_plugin() -> StaticCommandPlugin:
    return StaticCommandPlugin(
        metadata=PluginMetadata(
            name="nikto",
            description="Web server misconfiguration and vulnerability checks.",
            capability_tags=["web_security", "enumeration", "validation"],
            risk_level="medium",
        ),
        command="nikto",
        argument_factory=lambda _session, target: ["-h", target],
    )


def build_ffuf_plugin() -> StaticCommandPlugin:
    return StaticCommandPlugin(
        metadata=PluginMetadata(
            name="ffuf",
            description="Fast web content discovery and fuzzing.",
            capability_tags=["web_security", "content_discovery"],
            risk_level="medium",
        ),
        command="ffuf",
        argument_factory=lambda _session, target: ["-u", f"{target}/FUZZ", "-w", "/usr/share/wordlists/dirb/common.txt", "-of", "json", "-o", "/dev/stdout"],
    )


def build_gobuster_plugin() -> StaticCommandPlugin:
    return StaticCommandPlugin(
        metadata=PluginMetadata(
            name="gobuster",
            description="Directory and DNS brute-force style content discovery.",
            capability_tags=["web_security", "content_discovery"],
            risk_level="medium",
        ),
        command="gobuster",
        argument_factory=lambda _session, target: ["dir", "-u", target, "-w", "/usr/share/wordlists/dirb/common.txt"],
    )

from __future__ import annotations

from dataclasses import dataclass, field

from mcaoe.plugins.http_tools import build_ffuf_plugin, build_nikto_plugin, build_whatweb_plugin, build_gobuster_plugin
from mcaoe.plugins.network_tools import build_amass_plugin, build_sslscan_plugin, build_subfinder_plugin
from mcaoe.plugins.nmap import NmapPlugin


@dataclass(slots=True)
class PluginRegistry:
    plugins: dict[str, object] = field(default_factory=dict)

    def register(self, plugin: object) -> None:
        name = getattr(getattr(plugin, "metadata", None), "name", None)
        if not name:
            raise ValueError("Plugin metadata.name is required")
        self.plugins[name] = plugin

    def get(self, name: str) -> object:
        return self.plugins[name]

    @classmethod
    def with_defaults(cls) -> "PluginRegistry":
        registry = cls()
        registry.register(NmapPlugin())
        registry.register(build_whatweb_plugin())
        registry.register(build_nikto_plugin())
        registry.register(build_ffuf_plugin())
        registry.register(build_gobuster_plugin())
        registry.register(build_sslscan_plugin())
        registry.register(build_subfinder_plugin())
        registry.register(build_amass_plugin())
        return registry

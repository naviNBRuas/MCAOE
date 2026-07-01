from mcaoe.plugins.registry import PluginRegistry


def test_registry_with_defaults_contains_known_plugins() -> None:
    registry = PluginRegistry.with_defaults()
    assert "nmap" in registry.plugins
    assert "whatweb" in registry.plugins
    assert "nikto" in registry.plugins
    assert "ffuf" in registry.plugins
    assert "gobuster" in registry.plugins
    assert "sslscan" in registry.plugins
    assert "subfinder" in registry.plugins
    assert "amass" in registry.plugins


def test_registry_register_validates_metadata() -> None:
    registry = PluginRegistry()

    class BadPlugin:
        pass

    try:
        registry.register(BadPlugin())
        assert False, "Should have raised ValueError"
    except ValueError as exc:
        assert "metadata.name" in str(exc)


def test_registry_get_returns_plugin() -> None:
    registry = PluginRegistry.with_defaults()
    nmap = registry.get("nmap")
    assert nmap is not None


def test_registry_discover_entry_points_returns_count() -> None:
    registry = PluginRegistry()
    count = registry.discover_entry_points()
    assert count >= 0

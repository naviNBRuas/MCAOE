# Plugin Authoring Guide

MCAOE uses a plugin architecture centered on the `Plugin` interface in `mcaoe.plugins.base`.

## Core Concepts

A plugin:
- Implements the `Plugin` abstract base class
- Provides a `metadata` descriptor with name, description, version
- Implements `can_handle()` to declare compatibility with capabilities and targets
- Implements `execute()` to run a tool and return structured results
- Implements `ingest_output()` to parse tool stdout/stderr into domain entities

## Plugin Interface

```python
from mcaoe.plugins.base import Plugin, PluginMetadata, PluginResult
from mcaoe.models.domain import Session


class MyPlugin(Plugin):
    metadata = PluginMetadata(
        name="my_plugin",
        description="Description of what this plugin does",
        version="0.1.0",
    )

    def can_handle(self, target: str, capability: str) -> bool:
        return capability in {"recon", "fingerprinting"}

    async def execute(self, session: Session, target: str) -> PluginResult:
        # Run a tool and return results
        return PluginResult(
            tool_name="my_tool",
            command=["my_tool", target],
            stdout="...",
            stderr="",
            exit_code=0,
            metadata={"target": target},
        )

    async def ingest_output(self, session: Session, result: PluginResult) -> None:
        # Parse output and populate session
        session.add_host(host)
        session.add_service(service)
```

## Registration

Register plugins via the plugin registry:

```python
from mcaoe.plugins.registry import PluginRegistry

registry = PluginRegistry()
registry.register("my_plugin", MyPlugin())
```

Or auto-discover by placing the module under `mcaoe.plugins.builtins`.

## Best Practices

1. Keep plugins stateless and idempotent
2. Use `ingest_output()` to populate the session rather than doing it in `execute()`
3. Return structured data — avoid raw parsing in the orchestration layer
4. Declare capability compatibility honestly in `can_handle()`
5. Use `slots=True` on dataclasses for memory efficiency

## Testing

Write unit tests for `ingest_output()` with sample tool output strings. Mock the subprocess layer for `execute()` tests.

```python
async def test_my_plugin_ingest():
    plugin = MyPlugin()
    session = create_test_session()
    result = PluginResult(tool_name="my_tool", stdout="...", ...)
    await plugin.ingest_output(session, result)
    assert len(session.hosts) > 0
```

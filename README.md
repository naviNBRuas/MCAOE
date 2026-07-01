# MCAOE — Modular Cybersecurity Analyst Operating Environment

A terminal-native, AI-assisted cybersecurity analyst workbench with containerized tool execution, structured domain models, and a plugin-based architecture.

## Features

- **Plugin System** — Tools (nmap, whatweb, nikto, ffuf) are encapsulated as plugins with structured output ingestion
- **Event-Driven** — Async event bus with dead-letter queues and error boundaries
- **Workflow Engine** — State machine driving discovery → fingerprinting → enumeration → validation
- **Containerized Execution** — Tools run in isolated Docker containers with security profiles and timeouts
- **Knowledge Graph** — Entity-relationship graph built on NetworkX with traversal queries
- **Recommendation Engine** — Rule-based + optional AI-driven recommendations
- **Interactive UI** — Textual-based TUI with TabbedContent, DataTable, Tree, and modal dialogs
- **Session Management** — Persistent SQLite store with CLI list/load/delete
- **AI Integration** — Optional LLM backends (Gemini, GPT) for session summarization
- **Capability Profiles** — 9 pre-defined profiles (recon, fingerprinting, web, fuzzing, etc.)

## Quick Start

```bash
pip install mcaoe

# Configure API key (optional, for AI features)
export MCAOE_GEMINI_API_KEY="your-key"

# Start interactive session
mcaoe --interactive

# Run a canned workflow
mcaoe --target example.com --capability web_assessment
```

## CLI Usage

```
mcaoe [--target HOST] [--capability PROFILE] [--interactive]
      [--session-count] [--list-sessions] [--load-session ID]
      [--delete-session ID] [--container-cleanup]
```

| Flag | Description |
|------|-------------|
| `--target` | Target host/IP/domain |
| `--capability` | Capability profile (default: `recon`) |
| `--interactive` | Open the Textual UI |
| `--session-count` | Show number of stored sessions |
| `--list-sessions` | List all stored sessions |
| `--load-session` | Load a session by ID |
| `--delete-session` | Delete a session by ID |
| `--container-cleanup` | Auto-remove containers on exit |

## Safety

- Analyst-in-the-loop: all execution requires explicit approval via modal dialog
- Tools run in isolated containers with resource limits and no-new-privileges
- API keys stored via OS keyring, never committed
- No autonomous chaining of offensive actions

## Documentation

See the `docs/` directory:
- [Architecture](docs/ARCHITECTURE.md)
- [Plugin Authoring](docs/plugins.md)
- [Development Plan](docs/DEVELOPMENT_PLAN.md)

## License

MIT — see LICENSE file.

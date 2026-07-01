# MCAOE Architecture

## Overview

MCAOE is organized as a layered system with clear separation of concerns:

```
┌──────────────────────────────────────────────────┐
│                    UI Layer                       │
│  Textual TUI (TabbedContent, DataTable, Tree)    │
│  Modal dialogs, Docker status indicator          │
├──────────────────────────────────────────────────┤
│               Application Layer                  │
│  Orchestrator, Workflow Engine, CLI              │
├──────────────────────────────────────────────────┤
│              Domain / Model Layer                │
│  Session, Host, Service, Finding, Technology     │
│  Recommendation, Unknown, Evidence               │
├─────────────┬────────────┬───────────────────────┤
│  Plugins    │  Runtime   │   Intelligence        │
│  (nmap,     │  (Docker,  │   (Knowledge Graph,   │
│   nikto,    │   local)   │    Recommendations,   │
│   ffuf...)  │            │    AI Assistant)      │
├─────────────┴────────────┴───────────────────────┤
│                   Infrastructure                  │
│  Event Bus, SQLite Store, Logging, Observability │
└──────────────────────────────────────────────────┘
```

## Core Components

### Event Bus (`core/events.py`)
- Typed events with async dispatch
- Error boundary wrapping for all handlers
- Dead-letter queue for failed event processing
- Event history for replay and observability

### Plugin System (`plugins/`)
- `Plugin` ABC with `execute()` and `ingest_output()` methods
- `PluginRegistry` for registration and discovery
- Built-in plugins for nmap, whatweb, nikto, ffuf, gobuster, etc.
- Auto-discovery from plugin modules

### Runtime (`runtime/`)
- `DockerRuntimeManager` — container execution with security profiles and log streaming
- `DockerExecutionProvider` — adapter for the execution abstraction
- Security profiles: `recon_standard` (bridge, 1g, 1.5 CPUs) and `defensive_strict` (no network, 768m, 1 CPU)

### Knowledge Graph (`graph/`)
- NetworkX MultiDiGraph backing store
- Entity nodes: hosts, services, technologies, findings, evidence, unknowns
- Relationship edges: hosts, runs, affects, references
- Traversal: neighbors(), paths_between(), nodes_by_kind()

### AI Provider (`ai/`)
- LLMProvider ABC with Gemini and OpenAI implementations
- API key resolution via env vars → system keyring
- Optional: requires `google-generativeai` or `openai` packages
- Analyst assistant combines rule-based and AI summarization

### Recommendations (`recommendations/`)
- Rule-based engine generating context-aware recommendations
- Scored by priority (1=high) and confidence
- Integrated with capability profiles and gap analysis

### Session Management (`database/`)
- SQLite-backed persistence with Session domain model
- CLI commands for list, load, delete, count
- Entity deduplication via add_host/add_service/add_finding methods

## Data Model

```
Session
 ├── targets: list[str]
 ├── hosts: list[Host] (address, os)
 ├── services: list[Service] (port, protocol, name, version)
 ├── technologies: list[Technology] (name, version, confidence)
 ├── findings: list[Finding] (title, severity, description)
 ├── unknowns: list[Unknown] (label, priority)
 ├── evidence: list[Evidence] (source, summary, raw)
 ├── recommendations: list[Recommendation]
 └── commands: list[ExecutedCommand]
```

## Container Profiles

| Profile | Network | Memory | CPUs | No-New-Privs | Read-Only |
|---------|---------|--------|------|-------------|-----------|
| recon_standard | bridge | 1g | 1.5 | yes | no |
| defensive_strict | none | 768m | 1.0 | yes | yes |

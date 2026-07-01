# MCAOE Development & Evolution Plan

This document outlines the strategic roadmap for evolving the Modular Cybersecurity Analyst Operating Environment (MCAOE) from an MVP scaffold into a professional, polished, and stable terminal-native workbench.

## 1. Executive Summary
MCAOE is currently a functional MVP with a solid conceptual foundation (event bus, plugin registry, UI scaffold). All six development phases have been completed, delivering a professional-grade architecture with containerized execution, AI integration, comprehensive documentation, and a polished TUI.

## 2. Completed Phases

### Phase 1: Foundation & Tooling ✓
**Goal:** Establish a robust development environment and CI/CD pipeline.
1. Initialized `pyproject.toml` using Hatch build backend
2. Defined all runtime and development dependencies
3. Configured Ruff for linting/formatting and Mypy for strict type checking
4. Setup GitHub Actions for automated CI checks (Ruff, Mypy, pytest)
5. Introduced pre-commit hooks
6. Added `py.typed` marker for PEP 561 compliance
7. Fixed 6 test failures, 4 Ruff errors, 71 Mypy errors across source and test files

### Phase 2: Architecture Refactoring & Plugin System ✓
**Goal:** Decouple core logic from tool-specific implementations.
1. Redesigned Plugin interface with `ingest_output()` method
2. Moved all hardcoded parsers from `mcaoe.ui.app` and `mcaoe.app` into plugin classes
3. Consolidated duplicate profile definitions into single canonical `profiles/catalog.py`
4. Hardened async EventBus with error boundary wrapping and dead-letter queue
5. Entity deduplication methods on Session model (add_host, add_service, etc.)

### Phase 3: UI/UX Overhaul (Textual) ✓
**Goal:** Transform the UI into a polished, professional dashboard.
1. Refactored `MCAOEApp` layout to use `TabbedContent` with Inventory, Findings, Knowledge Graph, and Activity tabs
2. Implemented `DataTable` for hosts/services/findings views
3. Implemented `Tree` for Knowledge Graph visualization with hierarchical entity grouping
4. Created reusable `TaskApprovalModal` for safe, explicit task execution approval
5. Added Docker connection status indicator (green/red) in the UI header

### Phase 4: Containerization & Execution Engine ✓
**Goal:** Ensure reliable, isolated execution of heavy tools.
1. Created `containers/Dockerfile.tools` with standard tooling image
2. Enhanced `DockerRuntimeManager` with `stream_logs()` async generator for real-time log streaming
3. Implemented execution timeouts with docker stop/rm cleanup via `stop_container()`
4. Added `container_cleanup` flag (default: on) for automated cleanup on timeout/error
5. Security profiles: recon_standard (bridge, 1g, 1.5 CPUs) and defensive_strict (no network, 768m, 1 CPU)

### Phase 5: Intelligence & AI Integration ✓
**Goal:** Elevate the assistant from a rule-based stub to a true AI co-pilot.
1. Implemented LLM provider interface with `LLMProvider` ABC (GeminiProvider, OpenAIProvider)
2. API key resolution via env vars → system keyring with `get_api_key()` / `store_api_key_in_keyring()`
3. Enhanced `AnalystAssistant` with optional LLM-based session summarization
4. Expanded Knowledge Graph with relationship queries (neighbors(), paths_between(), nodes_by_kind())
5. Added `link_technology_to_host()`, `link_finding_to_host()`, `link_evidence_to_entity()` to graph engine
6. Added `ai` optional dependency group in pyproject.toml

### Phase 6: Documentation & Release ✓
**Goal:** Finalize project for open-source or commercial deployment.
1. Setup MkDocs with Material theme (`mkdocs.yml`)
2. Wrote comprehensive Architecture documentation
3. Created Plugin Authoring guide
4. Overhauled README with feature list, CLI usage, quick start
5. All 69+ tests passing, Ruff clean, Mypy strict-mode clean
6. CI pipeline passing on push

## 3. Future Roadmap

### Post-MVP Enhancements
- **Alembic migrations** for schema evolution
- **Plugin auto-discovery** from pip-installed packages via entry points
- **Multi-session comparison** in the UI
- **Export/import** sessions as JSON/YAML
- **Remote agent** support for distributed scanning
- **Web dashboard** mode (optional Flask/FastAPI server)
- **CI/CD integration** — trigger scans from GitHub webhooks
- **Plugin marketplace** — registry for community plugins

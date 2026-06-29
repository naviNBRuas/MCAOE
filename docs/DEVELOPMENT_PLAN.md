# MCAOE Development & Evolution Plan

This document outlines the strategic roadmap for evolving the Modular Cybersecurity Analyst Operating Environment (MCAOE) from an MVP scaffold into a professional, polished, and stable terminal-native workbench.

## 1. Executive Summary
MCAOE is currently an MVP with a solid conceptual foundation (event bus, plugin registry, UI scaffold). To achieve professional-grade stability, we must address several architectural gaps, establish standard Python packaging, overhaul the UI/UX, and encapsulate tool logic appropriately.

## 2. Identified Gaps & Areas for Improvement

### 2.1 Project Infrastructure & Quality Assurance
* **Packaging:** Missing `pyproject.toml` or standard dependency management. Dependencies like `textual`, `pydantic`, and `networkx` must be formalized.
* **CI/CD:** No automated workflows for testing, linting (Ruff), or type-checking (Mypy).
* **Code Quality:** Lack of pre-commit hooks to enforce consistent formatting and static analysis.

### 2.2 Architecture & Decoupling
* **Plugin Encapsulation:** The core `app.py` and `ui/app.py` contain hardcoded ingestion logic for specific tools (e.g., `whatweb`, `nikto`, `ffuf`). This breaks the open-closed principle. Parsers should be tightly coupled to their respective plugins, not the core app.
* **Database & State Management:** The SQLite integration lacks schema migration management (e.g., Alembic). An ORM layer or structured query builder is needed as the domain model grows.
* **Docker Runtime:** The `DockerExecutionProvider` requires standardized `Dockerfile` definitions for the heavy tooling to ensure reproducibility across environments.

### 2.3 User Interface (UI/UX)
* **Widget Utilization:** The current Textual UI relies heavily on basic `RichLog` widgets. A professional UI requires structured data presentation (`DataTable` for hosts/services, `Tree` for knowledge graphs).
* **Interactivity:** Approving tasks currently uses global key bindings. This should be refactored into interactive Modal dialogs for safer, explicit approvals.
* **Navigation:** The layout should utilize `TabbedContent` to prevent visual clutter, separating "Planning", "Execution", and "Reporting" views.

### 2.4 Documentation
* **Developer Docs:** Missing a formal documentation site (e.g., MkDocs) detailing the architecture, event bus system, and how to write new plugins.
* **User Manuals:** Instructions on securely configuring API keys, managing Docker dependencies, and interpreting the knowledge graph.

---

## 3. Phased Implementation Roadmap

The following phases are designed to be implemented sequentially.

### Phase 1: Foundation & Tooling 
**Goal:** Establish a robust development environment and CI/CD pipeline.
1. Initialize `pyproject.toml` using a modern build backend (e.g., Hatch, Poetry).
2. Define all runtime and development dependencies.
3. Configure Ruff for linting/formatting and Mypy for strict type checking.
4. Setup GitHub Actions for automated CI checks.
5. Introduce `pre-commit` hooks.

### Phase 2: Architecture Refactoring & Plugin System
**Goal:** Decouple core logic from tool-specific implementations.
1. Redesign the `Plugin` interface to require an `ingest_output(stdout, stderr)` method.
2. Move all hardcoded parsers from `mcaoe.ui.app` and `mcaoe.app` into their respective plugin classes.
3. Integrate Alembic for SQLite database migrations.
4. Harden the async EventBus with better error boundary handling and dead-letter queues.

### Phase 3: UI/UX Overhaul (Textual)
**Goal:** Transform the UI into a polished, professional dashboard.
1. Refactor `MCAOEApp` layout to use `TabbedContent`.
2. Implement `DataTable` for the "Target Intelligence" and "Findings" views.
3. Implement `Tree` for visualizing the Knowledge Graph.
4. Create reusable Modal Dialogs for task approval, preventing accidental executions.
5. Add real-time visual indicators for Docker connection status and AI readiness.

### Phase 4: Containerization & Execution Engine
**Goal:** Ensure reliable, isolated execution of heavy tools.
1. Create a `containers/` directory with standardized Dockerfiles for tools (Nmap, WhatWeb, Nikto, FFuf).
2. Enhance `DockerExecutionProvider` to stream logs asynchronously to the UI.
3. Implement execution timeouts, resource limits, and automated container cleanup routines.

### Phase 5: Intelligence & AI Integration
**Goal:** Elevate the assistant from a rule-based stub to a true AI co-pilot.
1. Implement the LLM provider interface (via the existing keyring support).
2. Enhance the `RecommendationEngine` to utilize AI for complex correlation.
3. Expand Knowledge Graph capabilities to detect multi-stage attack paths.

### Phase 6: Documentation & Release
**Goal:** Finalize project for open-source or commercial deployment.
1. Setup MkDocs with Material theme in the `docs/` directory.
2. Write Architecture Diagrams and Plugin Authoring guides.
3. Prepare a v1.0.0 release candidate.

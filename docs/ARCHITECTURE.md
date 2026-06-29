# MCAOE Architecture Design Document

## 1. System Overview
MCAOE (Modular Cybersecurity Analyst Operating Environment) is a terminal-native, AI-assisted workbench. It acts as an orchestrator for heavy cybersecurity tools running in isolated Docker containers, providing a unified, local, and lightweight control plane for the analyst.

## 2. Core Principles
* **Analyst-Led (Human-in-the-Loop):** The system must never autonomously chain or launch offensive actions without explicit user approval.
* **Isolation:** All external execution (scanners, enumeration tools) must occur in isolated, ephemeral Docker containers.
* **Modularity:** Core application logic must remain completely agnostic to specific tool implementations. Tools are integrated solely via the Plugin Registry.
* **Asynchronous Event-Driven:** State changes, tool outputs, and AI recommendations are propagated via an async Event Bus, allowing real-time UI updates without blocking.

## 3. High-Level Architecture Components

### 3.1 Presentation Layer (Textual UI)
The terminal user interface built with the `Textual` framework.
* **Responsibilities:** Render dashboards, manage layout (`TabbedContent`, `DataTables`), capture user input, and display real-time event logs.
* **Key Constraint:** Must not contain parsing or business logic. Strictly handles rendering and routing user intents to the Orchestrator.

### 3.2 Orchestration Layer
The `AnalystOrchestrator` acts as the bridge between the UI, the Event Bus, and the Execution Environment.
* **Responsibilities:** Validating task requests against the `SafetyPolicy`, resolving plugin configurations, and submitting tasks to the Execution Provider.

### 3.3 Domain Model & State
Pydantic-based data models representing the cybersecurity domain.
* **Entities:** `Host`, `Service`, `Finding`, `Technology`, `Recommendation`, `WorkflowState`.
* **Knowledge Graph:** A `networkx` based graph mapping relationships (e.g., `Host` -> `Service` -> `Vulnerability`).
* **Persistence:** `SQLiteStore` (to be enhanced with Alembic/ORM) persists the session state to `.mcaoe/mcaoe.sqlite3`.

### 3.4 Execution Providers
Abstractions for running external processes.
* **LocalExecutionProvider:** Runs commands directly on the host (used primarily for testing or very safe native commands).
* **DockerExecutionProvider:** The primary production provider. Manages container lifecycle via the `DockerRuntimeManager`, mounting necessary volumes and proxying stdout/stderr back to the Event Bus.

### 3.5 Plugin Subsystem
The extensibility mechanism of MCAOE.
* **Structure:** Each tool (e.g., Nmap, Nikto) implements a `Plugin` interface.
* **Responsibilities:** Defines the required Docker image, command-line arguments, and critically, the **parsing logic** to convert raw stdout/stderr into Domain Model entities (Findings, Services, Technologies).

### 3.6 AI & Intelligence
* **AnalystAssistant:** The interface to the LLM (Large Language Model) provider. Generates session summaries, workflow hints, and correlates disparate findings.
* **RecommendationEngine:** A rule-based (and later AI-augmented) engine that observes the Event Bus and pushes actionable recommendations to the UI based on the current Workflow Stage and Discovered Entities.

## 4. Event Flow (Task Execution Lifecycle)
1. **User Request:** Analyst requests to run Nmap via the UI.
2. **Planning:** Orchestrator retrieves the Nmap Plugin, generating a task execution plan.
3. **Approval:** UI prompts the Analyst with the planned command. Analyst approves.
4. **Execution:** Orchestrator validates the `SafetyPolicy`, then dispatches to the `DockerExecutionProvider`.
5. **Streaming:** Provider executes the container, streaming raw output to the Event Bus.
6. **Ingestion:** Upon completion, the Orchestrator hands the output back to the Nmap Plugin's parser.
7. **State Mutation:** Parsed entities (e.g., `Host`, `Service`) are saved to the `SQLiteStore` and appended to the Knowledge Graph.
8. **Reactivity:** UI widgets bound to the store/graph update automatically to reflect the new intelligence.

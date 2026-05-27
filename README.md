# MCAOE - Modular Cybersecurity Analyst Operating Environment

This repository contains MCAOE — a terminal-native, AI-assisted cybersecurity analyst workbench.

Secure setup highlights:

- Do not commit API keys. Use OS keyring (see `tools/ai_keyring_cli.py`) or CI secrets.
- A `.env.template` helper is available via `mcaoe.ai.provider.ensure_env_template()`.

See `CONTRIBUTING.md`, `SECURITY.md`, and `SUPPORT.md` for contribution and support guidance.

## MCAOE

Modular Cybersecurity Analyst Operating Environment.

This repository currently contains an MVP scaffold for a terminal-native,
human-in-the-loop cybersecurity analyst workbench. Heavy tooling is intended to
run inside isolated containers, while the local application stays lightweight
and modular.

## What’s in the scaffold

- Typed domain models for hosts, services, findings, recommendations, and sessions
- An async event bus
- A workflow state machine
- An execution-provider abstraction
- A Docker runtime manager stub
- A rule-based recommendation engine
- A networkx-based knowledge-graph engine
- A plugin interface with an Nmap starter plugin
- A minimal Textual app entrypoint

## Safety posture

The project is designed for analyst-led workflows only. It should require
explicit user approval for execution and should not autonomously chain or launch
offensive actions.

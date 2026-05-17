# Agent Behavior Boundary Runtime

Small, inspectable Python modules for deciding when an AI agent should trim context, stay quiet, run background work, or surface a finding.

This repository does not contain private memory DBs, personal session logs, local runtime state, credentials, persona chat logs, bot-control data, model weights, generated media, or vendor caches.

This is a sanitized source/documentation snapshot. It is not a dump of a private assistant, a memory database, or a local runtime environment.

## 30-Second Overview

Agent Behavior Boundary Runtime is a small Python reference project for testing the control layer around an AI agent. It focuses on the parts that decide when an agent should keep context, trim context, stay quiet, search, or interrupt the user.

The experiment is about behavior boundaries, not about shipping a personality. It separates reusable control ideas from private memory systems and persona-specific data:

- prompt budget control for long chat contexts
- resource-aware gating for background work
- novelty/relevance checks before agent-initiated interruptions
- inspectable decision reports for why a boundary allowed or blocked an action

This snapshot is currently a reference implementation with tests and a local example. It does not include a model backend, web UI, private memory connector, training pipeline, deployment config, or private chat data.

## Documentation

Start here if you are reading this repo like a GitHub project page:

- [Getting Started](docs/GETTING_STARTED.md): install, run tests, run the demo, and use the package from another project.
- [Runtime Boundaries](docs/RUNTIME_BOUNDARIES.md): plain-language explanation of the behavior-control problem this project explores.
- [API Reference](docs/API_REFERENCE.md): public functions, expected inputs, and example outputs.
- [Public Release Guide](docs/PUBLIC_RELEASE_GUIDE.md): what should stay out of the repository before publishing changes.
- [FAQ](docs/FAQ.md): quick answers for non-specialist readers.

## Why This Exists

Local AI agents can become hard to reason about when memory, persona, background loops, tools, and model calls all mix together. This project keeps one narrow question visible:

> What boundary checks should run before an agent spends context, uses local resources, searches, or interrupts?

The goal is to make those checks easy to inspect and adapt without exposing any private runtime state.

## What This Is Not

- Not a private memory dump.
- Not a persona dataset.
- Not a chat transcript archive.
- Not a bot controller.
- Not a model-weight or fine-tuning repository.
- Not a claim that this is ready for high-risk or production use.

## Quick Start

```bash
git clone https://github.com/zoziaman/agent-behavior-boundary-runtime.git
cd agent-behavior-boundary-runtime
python -m venv .venv
python -m pip install -e ".[dev]"
python -m pytest
python examples/basic_demo.py
```

Use any normal project folder as the install location. The docs use placeholders such as `<workspace>` when a path is needed; no personal local path is required.

## Repository Layout

```text
src/agent_boundary_runtime/
  prompt_budget.py    # trims oversized prompt/message lists with a decision report
  resource_guard.py   # gates background/network/model work using idle, process, and GPU signals
  curiosity_gate.py   # scores novelty/relevance before optional agent-initiated output

examples/
  basic_demo.py       # runs the three boundary checks with fake inputs

tests/
  test_*.py           # small regression tests for the public modules
```

## Public Naming

The public-facing name used here is **Agent Behavior Boundary Runtime**. Other reasonable neutral names:

- Persona Safety Runtime
- Agent Boundary Control Runtime
- AI Agent Runtime Guardrails

## Security Boundary

See `SECURITY_PUBLIC_CHECK.md` for the current publication checklist. Future contributors should keep private memory exports, session logs, model weights, generated media, credentials, local state, and user-specific persona data out of this repository.

## Contributing

Small documentation fixes, focused tests, and reusable boundary-control improvements are welcome. Do not add private runtime dumps, model artifacts, generated media, local config, or persona-specific data.

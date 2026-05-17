# Getting Started

This guide shows how to install the project, run the checks, and call the boundary modules from your own agent runtime.

## Requirements

- Python 3.10 or newer
- Git
- A terminal

No API key, model download, database, or private memory export is required for the included demo and tests.

## Install From GitHub

Choose any normal workspace folder on your machine. The placeholder `<workspace>` means "wherever you keep source repos"; it is not a required path.

```bash
cd <workspace>
git clone https://github.com/zoziaman/agent-behavior-boundary-runtime.git
cd agent-behavior-boundary-runtime
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

Install the package and test dependency:

```bash
python -m pip install -e ".[dev]"
```

## Verify The Checkout

```bash
python -m pytest
python examples/basic_demo.py
```

The demo uses fake inputs and a fake search result. It does not call a model, network API, or private memory source.

## Use In Another Project

Install this package into your project environment, then call the modules at the points where your agent needs a decision.

```python
from agent_boundary_runtime import enforce_prompt_budget

messages = [
    {"role": "system", "content": "Keep boundary decisions explicit."},
    {"role": "user", "content": "Explain the next safe action."},
]

trimmed_messages, report = enforce_prompt_budget(
    messages,
    mode="technical",
    max_chars=4000,
)

print(report["after_chars"])
```

## Suggested Integration Points

- Before a model call: run `enforce_prompt_budget()` on the message list.
- Before background work: run `assess_resource_policy()` to decide whether work should stay quiet.
- Before agent-initiated output: run `curiosity_tick()` with a resource policy and your own search function.

## State Handling

The modules accept ordinary dictionaries for runtime state. If you persist those dictionaries in your own app, keep the files outside this repository or in ignored local paths. Do not commit private runtime state, chat logs, memory exports, or generated outputs.

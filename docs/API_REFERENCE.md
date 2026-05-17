# API Reference

This project exposes a small public surface from `agent_boundary_runtime`.

## Prompt Budget

```python
from agent_boundary_runtime import enforce_prompt_budget
```

```python
trimmed_messages, report = enforce_prompt_budget(
    messages,
    mode="technical",
    max_chars=4000,
)
```

### Input

- `messages`: list of chat-style dictionaries with `role` and `content`.
- `mode`: optional budget profile name. Built-in examples include `greeting`, `clarification`, `technical`, `research`, and `default`.
- `max_chars`: optional hard character budget.
- `config`: optional prompt-budget config dictionary.

### Output

- `trimmed_messages`: copied and possibly trimmed message list.
- `report`: audit dictionary with fields such as:
  - `before_chars`
  - `after_chars`
  - `budget_chars`
  - `dropped_sections`
  - `capped_sections`
  - `dropped_history_messages`
  - `over_budget_after`

## Resource Guard

```python
from agent_boundary_runtime import assess_resource_policy
```

```python
policy = assess_resource_policy(
    state,
    idle_seconds=600,
    gpu_snapshot={"available": True, "memory_free_mb": 7000, "utilization_gpu_pct": 3},
    busy_processes=[],
)
```

### Input

- `state`: mutable dictionary that stores resource-guard config and last policy.
- `intent`: optional label for the check.
- `idle_seconds`: optional override for tests or external idle detection.
- `gpu_snapshot`: optional GPU state override.
- `busy_processes`: optional busy-process override.

If overrides are omitted, the module tries local checks where available. On systems without supported signals, it falls back conservatively instead of requiring platform-specific dependencies.

### Output

The returned policy includes:

- `mode`
- `allow_background`
- `allow_network`
- `allow_sidecar`
- `allow_heavy_model`
- `allow_interrupt`
- `reasons`
- `next_check_sec`
- `snapshot`

## Curiosity Gate

```python
from agent_boundary_runtime import curiosity_tick
```

```python
result = curiosity_tick(
    runtime_state,
    resource_policy,
    search_fn=my_search_function,
)
```

### Input

- `runtime_state`: mutable dictionary containing `curiosity_gate` state and optional context such as `active_goal` or `recent_turns`.
- `resource_policy`: policy returned by `assess_resource_policy()` or an equivalent dictionary.
- `search_fn`: optional function with the shape `search_fn(query: str, limit: int) -> list[dict]`.

The gate does not perform network access unless you provide `search_fn` and the resource policy allows it.

### Output

The returned result includes:

- `emit`: boolean
- `action`: decision label
- `message`: optional message to surface
- `reason`: optional block reason
- `finding`: optional selected finding
- `topic`: optional selected topic

Common actions include `resource_blocked`, `below_threshold`, `search_cooldown`, `no_search_fn`, `not_novel`, `below_emit_threshold`, `emit_cooldown`, `daily_cap`, and `emit`.

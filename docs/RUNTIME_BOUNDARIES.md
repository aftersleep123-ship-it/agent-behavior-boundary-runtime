# Runtime Boundaries

AI agent behavior becomes difficult to inspect when model prompts, memory, tools, background loops, and personality text all live in the same layer. This project keeps the boundary layer small and explicit.

## The Core Question

Before an agent acts, a runtime can ask a few boring but useful questions:

- Is the prompt too large?
- Is the user currently active?
- Is the machine busy?
- Is this background search allowed right now?
- Is the finding novel enough to mention?
- Can we explain why the action was allowed or blocked?

The modules in this repository answer those questions with plain Python data structures.

## Boundary Types

### Prompt Budget

`prompt_budget.py` trims oversized chat contexts. It returns both the trimmed messages and a report showing what was capped or dropped.

Use it when long histories, retrieved notes, examples, or tool results may crowd out the final instruction.

### Resource Guard

`resource_guard.py` checks local signals such as user idle time, busy process names, and optional GPU load. It returns a policy that says whether background work, network work, sidecar model work, or interruptions are allowed.

Use it before background jobs that could distract the user or consume local machine resources.

### Curiosity Gate

`curiosity_gate.py` is a small decision loop for agent-initiated output. It does not search by itself. You pass in a search function, and the gate decides whether a result is novel and relevant enough to surface.

Use it when an agent has optional background findings but should not interrupt on a timer alone.

## What To Adapt

The default thresholds are examples. Real projects should tune:

- character budgets by task type
- busy process names for the user's environment
- idle thresholds for background work
- novelty and relevance thresholds
- daily caps and cooldowns for agent-initiated output

## What To Keep Separate

Keep these concerns outside the boundary layer:

- private memory storage
- model selection and inference
- user identity or persona data
- chat transcript persistence
- service credentials
- generated media and model weights

That separation is the main point of this snapshot.

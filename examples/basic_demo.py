from __future__ import annotations

from datetime import datetime, timedelta

from agent_boundary_runtime import (
    assess_resource_policy,
    build_default_curiosity_state,
    build_default_resource_guard_state,
    curiosity_tick,
    enforce_prompt_budget,
)


def fake_search(query: str, limit: int) -> list[dict[str, str]]:
    return [
        {
            "title": "Agent boundary control patterns",
            "url": "https://example.com/agent-boundaries",
            "snippet": f"Reference notes for {query}.",
        }
    ][:limit]


def main() -> None:
    messages = [
        {"role": "system", "content": "Keep boundary decisions explicit."},
        {"role": "user", "content": "\n\n".join(["[context]\n" + ("details " * 200), "[task]\nExplain the next safe action."])},
    ]
    trimmed, budget_report = enforce_prompt_budget(messages, mode="technical", max_chars=900)

    state = {"resource_guard": build_default_resource_guard_state()}
    resource_policy = assess_resource_policy(
        state,
        idle_seconds=600,
        gpu_snapshot={"available": True, "memory_free_mb": 7000, "utilization_gpu_pct": 3},
        busy_processes=[],
    )

    curiosity = build_default_curiosity_state()
    curiosity["attention_energy"] = 0.9
    curiosity["boredom"] = 0.8
    curiosity["last_search_at"] = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
    curiosity["last_emit_at"] = (datetime.now() - timedelta(hours=2)).isoformat(timespec="seconds")
    runtime_state = {
        "curiosity_gate": curiosity,
        "active_goal": {"text": "document agent boundary runtime"},
        "recent_turns": [{"role": "user", "content": "agent boundary prompt context runtime"}],
    }
    curiosity_result = curiosity_tick(runtime_state, resource_policy, search_fn=fake_search)

    print("Prompt chars:", budget_report["before_chars"], "->", budget_report["after_chars"])
    print("Trimmed messages:", len(trimmed))
    print("Resource mode:", resource_policy["mode"])
    print("Curiosity action:", curiosity_result["action"])
    if curiosity_result["emit"]:
        print(curiosity_result["message"])


if __name__ == "__main__":
    main()

from datetime import datetime, timedelta

from agent_boundary_runtime.curiosity_gate import build_default_curiosity_state, curiosity_tick


def fake_search(query: str, limit: int) -> list[dict[str, str]]:
    return [
        {
            "title": "New agent boundary runtime evaluation notes",
            "url": "https://example.com/boundary-runtime",
            "snippet": "A local agent boundary and prompt context evaluation reference.",
        }
    ][:limit]


def test_resource_block_prevents_search_and_emit() -> None:
    state = {"curiosity_gate": build_default_curiosity_state()}

    result = curiosity_tick(
        state,
        {"allow_background": False, "allow_network": False, "allow_interrupt": False, "mode": "user_active_quiet"},
        search_fn=fake_search,
    )

    assert result["emit"] is False
    assert result["action"] == "resource_blocked"


def test_emits_only_after_energy_and_novel_finding() -> None:
    curiosity = build_default_curiosity_state()
    curiosity["attention_energy"] = 0.9
    curiosity["boredom"] = 0.9
    curiosity["last_search_at"] = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
    curiosity["last_emit_at"] = (datetime.now() - timedelta(hours=2)).isoformat(timespec="seconds")
    state = {
        "curiosity_gate": curiosity,
        "active_goal": {"text": "reduce prompt context drift"},
        "recent_turns": [{"role": "user", "content": "agent boundary prompt runtime"}],
    }

    result = curiosity_tick(
        state,
        {"allow_background": True, "allow_network": True, "allow_interrupt": True, "mode": "idle_background_allowed"},
        search_fn=fake_search,
    )

    assert result["emit"] is True
    assert "example.com" in result["message"]
    assert state["curiosity_gate"]["emit_count_today"] == 1

from agent_boundary_runtime.resource_guard import assess_resource_policy, build_default_resource_guard_state


def test_blocks_background_when_user_active() -> None:
    state = {"resource_guard": build_default_resource_guard_state()}

    policy = assess_resource_policy(
        state,
        idle_seconds=5,
        gpu_snapshot={"available": True, "memory_free_mb": 7000, "utilization_gpu_pct": 0},
        busy_processes=[],
    )

    assert policy["allow_background"] is False
    assert policy["allow_network"] is False
    assert "user_active_idle_5s" in policy["reasons"]


def test_allows_idle_background_without_busy_processes() -> None:
    state = {"resource_guard": build_default_resource_guard_state()}

    policy = assess_resource_policy(
        state,
        idle_seconds=600,
        gpu_snapshot={"available": True, "memory_free_mb": 7000, "utilization_gpu_pct": 3},
        busy_processes=[],
    )

    assert policy["allow_background"] is True
    assert policy["allow_network"] is True
    assert policy["allow_sidecar"] is True


def test_blocks_busy_process() -> None:
    state = {"resource_guard": build_default_resource_guard_state()}

    policy = assess_resource_policy(
        state,
        idle_seconds=900,
        gpu_snapshot={"available": True, "memory_free_mb": 7000, "utilization_gpu_pct": 3},
        busy_processes=["blender.exe"],
    )

    assert policy["allow_background"] is False
    assert policy["mode"] == "busy_app_quiet"

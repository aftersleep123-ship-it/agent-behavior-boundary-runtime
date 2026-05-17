"""Resource-aware policy checks for local background agent work."""

from __future__ import annotations

import csv
import ctypes
import io
import platform
import subprocess
from copy import deepcopy
from datetime import datetime
from typing import Any


DEFAULT_BUSY_PROCESSES = [
    "blender.exe",
    "code.exe",
    "cyberpunk2077.exe",
    "eldenring.exe",
    "fortniteclient-win64-shipping.exe",
    "league of legends.exe",
    "photoshop.exe",
    "premierepro.exe",
    "resolve.exe",
    "unity.exe",
    "unrealeditor.exe",
    "valorant-win64-shipping.exe",
]


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def build_default_resource_guard_state() -> dict[str, Any]:
    return {
        "enabled": True,
        "busy_process_names": list(DEFAULT_BUSY_PROCESSES),
        "idle_min_background_sec": 120,
        "idle_min_network_sec": 180,
        "idle_min_sidecar_sec": 300,
        "idle_min_interrupt_sec": 90,
        "gpu_util_max_background": 35,
        "gpu_util_max_sidecar": 20,
        "vram_free_min_background_mb": 1600,
        "vram_free_min_sidecar_mb": 3200,
        "allow_network_when_active": False,
        "allow_interrupt_when_active": False,
        "last_snapshot": None,
        "last_policy": None,
        "last_policy_at": None,
    }


def ensure_resource_guard_container(state: dict[str, Any]) -> dict[str, Any]:
    current = state.get("resource_guard")
    if not isinstance(current, dict):
        current = {}
    default = build_default_resource_guard_state()
    for key, value in default.items():
        current.setdefault(key, deepcopy(value))
    if not isinstance(current.get("busy_process_names"), list):
        current["busy_process_names"] = list(DEFAULT_BUSY_PROCESSES)
    else:
        current["busy_process_names"] = [
            str(name).lower().strip() for name in current["busy_process_names"] if str(name).strip()
        ]
    state["resource_guard"] = current
    return current


class _LastInputInfo(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_windows_idle_seconds() -> float | None:
    if platform.system().lower() != "windows":
        return None
    try:
        info = _LastInputInfo()
        info.cbSize = ctypes.sizeof(info)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return None
        tick_count = ctypes.windll.kernel32.GetTickCount()
        return max(0.0, (tick_count - info.dwTime) / 1000.0)
    except Exception:
        return None


def _run_command(args: list[str], timeout: float = 2.0) -> subprocess.CompletedProcess[str] | None:
    try:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=creationflags,
            check=False,
        )
    except Exception:
        return None


def query_gpu_snapshot() -> dict[str, Any]:
    proc = _run_command(
        [
            "nvidia-smi",
            "--query-gpu=memory.used,memory.free,utilization.gpu",
            "--format=csv,noheader,nounits",
        ],
        timeout=2.0,
    )
    if proc is None or proc.returncode != 0 or not proc.stdout.strip():
        return {
            "available": False,
            "memory_used_mb": None,
            "memory_free_mb": None,
            "utilization_gpu_pct": None,
        }
    row = next(csv.reader(io.StringIO(proc.stdout.strip())), [])
    try:
        used = int(str(row[0]).strip())
        free = int(str(row[1]).strip())
        util = int(str(row[2]).strip())
    except Exception:
        return {
            "available": False,
            "memory_used_mb": None,
            "memory_free_mb": None,
            "utilization_gpu_pct": None,
        }
    return {
        "available": True,
        "memory_used_mb": used,
        "memory_free_mb": free,
        "utilization_gpu_pct": util,
    }


def detect_busy_processes(process_names: list[str] | None = None) -> list[str]:
    wanted = {str(name).lower().strip() for name in (process_names or DEFAULT_BUSY_PROCESSES) if str(name).strip()}
    if not wanted:
        return []
    proc = _run_command(["tasklist", "/fo", "csv", "/nh"], timeout=2.0)
    if proc is None or proc.returncode != 0:
        return []
    seen: set[str] = set()
    for row in csv.reader(io.StringIO(proc.stdout)):
        if not row:
            continue
        name = str(row[0]).lower().strip()
        if name in wanted:
            seen.add(name)
    return sorted(seen)


def _gpu_ok(gpu: dict[str, Any], *, util_max: int, free_min: int) -> bool:
    if not gpu.get("available"):
        return True
    util = gpu.get("utilization_gpu_pct")
    free = gpu.get("memory_free_mb")
    if util is not None and int(util) > int(util_max):
        return False
    if free is not None and int(free) < int(free_min):
        return False
    return True


def assess_resource_policy(
    state: dict[str, Any],
    *,
    intent: str = "background",
    idle_seconds: float | None = None,
    gpu_snapshot: dict[str, Any] | None = None,
    busy_processes: list[str] | None = None,
) -> dict[str, Any]:
    """Return a policy describing which background actions are allowed."""

    cfg = ensure_resource_guard_container(state)
    if not cfg.get("enabled", True):
        policy = {
            "mode": "disabled",
            "allow_background": True,
            "allow_network": True,
            "allow_sidecar": True,
            "allow_heavy_model": True,
            "allow_interrupt": True,
            "reasons": ["resource_guard_disabled"],
            "next_check_sec": 60,
            "snapshot": {},
        }
        cfg["last_policy"] = policy
        cfg["last_policy_at"] = _now_iso()
        return policy

    idle = get_windows_idle_seconds() if idle_seconds is None else idle_seconds
    gpu = query_gpu_snapshot() if gpu_snapshot is None else gpu_snapshot
    busy = detect_busy_processes(cfg.get("busy_process_names")) if busy_processes is None else busy_processes

    active_user = idle is not None and idle < float(cfg.get("idle_min_background_sec", 120))
    busy_app = bool(busy)
    gpu_background_ok = _gpu_ok(
        gpu,
        util_max=int(cfg.get("gpu_util_max_background", 35)),
        free_min=int(cfg.get("vram_free_min_background_mb", 1600)),
    )
    gpu_sidecar_ok = bool(gpu.get("available")) and _gpu_ok(
        gpu,
        util_max=int(cfg.get("gpu_util_max_sidecar", 20)),
        free_min=int(cfg.get("vram_free_min_sidecar_mb", 3200)),
    )

    reasons: list[str] = []
    if active_user:
        reasons.append(f"user_active_idle_{int(idle or 0)}s")
    if busy_app:
        reasons.append("busy_process:" + ",".join(str(item).lower() for item in busy[:4]))
    if not gpu_background_ok:
        reasons.append("gpu_busy_or_low_vram")

    idle_for_network = idle is None or idle >= float(cfg.get("idle_min_network_sec", 180))
    idle_for_sidecar = idle is not None and idle >= float(cfg.get("idle_min_sidecar_sec", 300))
    idle_for_interrupt = idle is None or idle >= float(cfg.get("idle_min_interrupt_sec", 90))

    allow_background = not busy_app and not active_user and gpu_background_ok
    allow_network = allow_background and idle_for_network
    if bool(cfg.get("allow_network_when_active")) and not busy_app and gpu_background_ok:
        allow_network = True
    allow_sidecar = allow_background and idle_for_sidecar and gpu_sidecar_ok
    allow_interrupt = allow_background and idle_for_interrupt
    if bool(cfg.get("allow_interrupt_when_active")) and not busy_app and gpu_background_ok:
        allow_interrupt = True

    if busy_app:
        mode = "busy_app_quiet"
        next_check = 120
    elif active_user:
        mode = "user_active_quiet"
        next_check = 60
    elif allow_background:
        mode = "idle_background_allowed"
        next_check = 45
    else:
        mode = "resource_quiet"
        next_check = 90

    snapshot = {
        "checked_at": _now_iso(),
        "intent": intent,
        "idle_seconds": None if idle is None else round(float(idle), 2),
        "busy_processes": busy,
        "gpu": gpu,
    }
    policy = {
        "mode": mode,
        "allow_background": allow_background,
        "allow_network": allow_network,
        "allow_sidecar": allow_sidecar,
        "allow_heavy_model": allow_sidecar,
        "allow_interrupt": allow_interrupt,
        "reasons": reasons,
        "next_check_sec": next_check,
        "snapshot": snapshot,
    }
    cfg["last_snapshot"] = snapshot
    cfg["last_policy"] = policy
    cfg["last_policy_at"] = snapshot["checked_at"]
    state["resource_guard"] = cfg
    return policy


__all__ = [
    "DEFAULT_BUSY_PROCESSES",
    "assess_resource_policy",
    "build_default_resource_guard_state",
    "detect_busy_processes",
    "ensure_resource_guard_container",
    "get_windows_idle_seconds",
    "query_gpu_snapshot",
]

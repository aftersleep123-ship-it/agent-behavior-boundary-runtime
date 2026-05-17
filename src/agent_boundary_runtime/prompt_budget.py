"""Prompt budget control for chat-style message lists."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any


MODE_CHAR_BUDGETS = {
    "greeting": 2600,
    "clarification": 3200,
    "technical": 5600,
    "research": 6200,
    "default": 4600,
}


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def build_default_prompt_budget_state() -> dict[str, Any]:
    return {
        "enabled": True,
        "mode_budgets": dict(MODE_CHAR_BUDGETS),
        "max_section_chars": 1400,
        "max_history_messages": 6,
        "last_report": None,
    }


def ensure_prompt_budget_container(state: dict[str, Any]) -> dict[str, Any]:
    current = state.get("prompt_budget")
    if not isinstance(current, dict):
        current = {}
    default = build_default_prompt_budget_state()
    for key, value in default.items():
        current.setdefault(key, deepcopy(value))
    if not isinstance(current.get("mode_budgets"), dict):
        current["mode_budgets"] = dict(MODE_CHAR_BUDGETS)
    state["prompt_budget"] = current
    return current


def _content_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if "text" in value:
            return _content_text(value.get("text"))
        if "content" in value:
            return _content_text(value.get("content"))
        return " ".join(_content_text(v) for v in value.values()).strip()
    if isinstance(value, list):
        return " ".join(_content_text(v) for v in value).strip()
    return str(value)


def estimate_prompt_chars(messages: list[dict[str, Any]]) -> int:
    total = 0
    for message in messages:
        total += len(str(message.get("role", ""))) + 2
        total += len(_content_text(message.get("content", "")))
    return total


def estimate_prompt_tokens(messages: list[dict[str, Any]]) -> int:
    # A conservative approximation that works without tokenizer dependencies.
    return int(estimate_prompt_chars(messages) / 3.2) + 1


def _split_sections(text: str) -> list[str]:
    return [section.strip() for section in text.split("\n\n") if section.strip()]


def _section_priority(section: str, index: int, total: int) -> int:
    lower = section.lower()
    if index == total - 1:
        return 100
    if any(key in lower for key in ("boundary", "policy", "rule", "safety", "must", "never")):
        return 92
    if any(key in lower for key in ("tool", "evidence", "source", "grounding", "retrieval")):
        return 82
    if any(key in lower for key in ("mode", "task", "current", "goal")):
        return 72
    if any(key in lower for key in ("history", "recent", "context")):
        return 56
    if any(key in lower for key in ("example", "style", "sample")):
        return 28
    if len(section) > 900:
        return 34
    return 50


def _cap_section(section: str, max_chars: int) -> tuple[str, bool]:
    if len(section) <= max_chars:
        return section, False
    head = section[: max(80, max_chars - 90)].rstrip()
    return head + "\n[budget-trimmed: section capped]", True


def _target_budget(config: dict[str, Any], mode: str, max_chars: int | None) -> int:
    if max_chars is not None:
        return int(max_chars)
    budgets = config.get("mode_budgets") or {}
    return int(budgets.get(mode, budgets.get("default", MODE_CHAR_BUDGETS["default"])))


def enforce_prompt_budget(
    messages: list[dict[str, Any]],
    *,
    mode: str = "default",
    config: dict[str, Any] | None = None,
    max_chars: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return a trimmed message list plus an audit report.

    The final message is treated as the most important instruction block. Older
    history and low-priority sections are trimmed before final instructions.
    """

    cfg = deepcopy(config or build_default_prompt_budget_state())
    enabled = bool(cfg.get("enabled", True))
    budget = _target_budget(cfg, mode, max_chars)
    out = deepcopy(messages)
    before = estimate_prompt_chars(out)
    report: dict[str, Any] = {
        "checked_at": _now_iso(),
        "enabled": enabled,
        "mode": mode,
        "budget_chars": budget,
        "before_chars": before,
        "before_tokens_est": estimate_prompt_tokens(out),
        "after_chars": before,
        "after_tokens_est": estimate_prompt_tokens(out),
        "dropped_sections": [],
        "capped_sections": [],
        "dropped_history_messages": 0,
    }

    if not enabled or before <= budget or not out:
        return out, report

    final_index = len(out) - 1
    sections = _split_sections(_content_text(out[final_index].get("content", "")))
    max_section_chars = int(cfg.get("max_section_chars", 1400))

    capped: list[str] = []
    for index, section in enumerate(sections):
        if index == len(sections) - 1:
            capped.append(section)
            continue
        capped_section, did_cap = _cap_section(section, max_section_chars)
        capped.append(capped_section)
        if did_cap:
            report["capped_sections"].append(
                {"index": index, "before_chars": len(section), "after_chars": len(capped_section)}
            )
    sections = capped
    out[final_index]["content"] = "\n\n".join(sections)

    while estimate_prompt_chars(out) > budget and len(sections) > 1:
        candidates = [
            (_section_priority(section, index, len(sections)), len(section), index)
            for index, section in enumerate(sections[:-1])
        ]
        _priority, _length, drop_index = min(candidates)
        removed = sections.pop(drop_index)
        report["dropped_sections"].append(
            {"index": drop_index, "chars": len(removed), "preview": removed[:80]}
        )
        out[final_index]["content"] = "\n\n".join(sections)

    history_indices = [index for index in range(1, max(1, len(out) - 1))]
    max_history = int(cfg.get("max_history_messages", 6))
    while estimate_prompt_chars(out) > budget and len(history_indices) > max_history:
        drop_index = history_indices.pop(0)
        out.pop(drop_index)
        history_indices = [index - 1 if index > drop_index else index for index in history_indices]
        final_index -= 1
        report["dropped_history_messages"] += 1

    if estimate_prompt_chars(out) > budget and sections:
        overflow = estimate_prompt_chars(out) - budget
        final_section = sections[-1]
        cut_to = max(240, len(final_section) - overflow - 32)
        if cut_to < len(final_section):
            sections[-1] = final_section[:cut_to].rstrip() + "\n[budget-trimmed: final instruction preserved]"
            out[final_index]["content"] = "\n\n".join(sections)
            report["capped_sections"].append(
                {"index": len(sections) - 1, "before_chars": len(final_section), "after_chars": len(sections[-1])}
            )

    after = estimate_prompt_chars(out)
    report["after_chars"] = after
    report["after_tokens_est"] = estimate_prompt_tokens(out)
    report["over_budget_after"] = after > budget
    return out, report


__all__ = [
    "MODE_CHAR_BUDGETS",
    "build_default_prompt_budget_state",
    "enforce_prompt_budget",
    "ensure_prompt_budget_container",
    "estimate_prompt_chars",
    "estimate_prompt_tokens",
]

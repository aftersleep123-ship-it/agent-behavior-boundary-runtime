"""Novelty and relevance gates for optional background agent output."""

from __future__ import annotations

import random
from copy import deepcopy
from datetime import date, datetime
from difflib import SequenceMatcher
from typing import Any, Callable
from urllib.parse import urlparse


SearchFn = Callable[[str, int], list[dict[str, Any]]]

DEFAULT_TOPICS = [
    {
        "topic": "agent boundary design",
        "query": "AI agent boundary control prompt budget resource guard",
        "why": "it relates to runtime boundary design",
    },
    {
        "topic": "local agent evaluation",
        "query": "local AI agent evaluation memory tools interruption policy",
        "why": "it relates to safer local agent behavior",
    },
    {
        "topic": "prompt context management",
        "query": "LLM prompt context trimming audit report",
        "why": "it relates to context budget decisions",
    },
]


def _now() -> datetime:
    return datetime.now()


def _now_iso() -> str:
    return _now().isoformat(timespec="seconds")


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def _elapsed_seconds(value: str | None, default: float = 999999.0) -> float:
    parsed = _parse_time(value)
    if parsed is None:
        return default
    return max(0.0, (_now() - parsed).total_seconds())


def build_default_curiosity_state() -> dict[str, Any]:
    return {
        "enabled": True,
        "attention_energy": 0.22,
        "boredom": 0.0,
        "last_tick_at": None,
        "last_search_at": None,
        "last_emit_at": None,
        "emit_count_today": 0,
        "emit_day_key": str(date.today()),
        "topic_history": [],
        "finding_history": [],
        "seen_signatures": [],
        "seen_urls": [],
        "last_action": None,
        "config": {
            "min_search_interval_sec": 900,
            "min_emit_cooldown_sec": 1800,
            "max_daily": 4,
            "energy_threshold": 0.38,
            "novelty_threshold": 0.52,
            "emit_threshold": 0.68,
            "search_limit": 4,
        },
    }


def ensure_curiosity_container(state: dict[str, Any]) -> dict[str, Any]:
    current = state.get("curiosity_gate")
    if not isinstance(current, dict):
        current = {}
    default = build_default_curiosity_state()
    for key, value in default.items():
        current.setdefault(key, deepcopy(value))
    if not isinstance(current.get("config"), dict):
        current["config"] = deepcopy(default["config"])
    else:
        for key, value in default["config"].items():
            current["config"].setdefault(key, value)
    state["curiosity_gate"] = current
    return current


def _normalize(text: Any) -> str:
    return " ".join(str(text or "").lower().strip().split())


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def _signature(finding: dict[str, Any]) -> str:
    title = _normalize(finding.get("title"))
    domain = _domain(str(finding.get("url", "")))
    return f"{domain}|{title}"


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _novelty_score(finding: dict[str, Any], curiosity: dict[str, Any]) -> float:
    url = str(finding.get("url", ""))
    signature = _signature(finding)
    seen_urls = {str(item) for item in curiosity.get("seen_urls", [])}
    if url and url in seen_urls:
        return 0.05
    seen = [str(item) for item in curiosity.get("seen_signatures", [])][-80:]
    if not seen:
        return 0.9
    closest = max((_similarity(signature, old) for old in seen), default=0.0)
    return round(max(0.05, 1.0 - closest), 4)


def _relevance_score(finding: dict[str, Any], topic: dict[str, Any], runtime_state: dict[str, Any]) -> float:
    text = _normalize(f"{finding.get('title', '')} {finding.get('snippet', '')} {topic.get('topic', '')}")
    score = 0.35
    for token in ("agent", "boundary", "guard", "prompt", "context", "runtime", "memory", "eval", "tool"):
        if token in text:
            score += 0.055
    active_goal = ((runtime_state.get("active_goal") or {}) if isinstance(runtime_state.get("active_goal"), dict) else {})
    goal_text = _normalize(active_goal.get("text") or active_goal.get("label") or "")
    for token in goal_text.split()[:8]:
        if len(token) >= 4 and token in text:
            score += 0.04
    return round(max(0.0, min(1.0, score)), 4)


def _extract_recent_terms(runtime_state: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    for row in list(runtime_state.get("recent_turns", []))[-8:]:
        if row.get("role") != "user":
            continue
        content = _normalize(row.get("content"))
        for token in ("agent", "boundary", "guard", "prompt", "context", "memory", "tool", "eval", "runtime"):
            if token in content and token not in terms:
                terms.append(token)
    return terms[:4]


def select_curiosity_topic(runtime_state: dict[str, Any], curiosity: dict[str, Any]) -> dict[str, Any]:
    topics = deepcopy(DEFAULT_TOPICS)
    active_goal = runtime_state.get("active_goal") if isinstance(runtime_state.get("active_goal"), dict) else {}
    goal_text = str(active_goal.get("text") or active_goal.get("label") or "").strip()
    if goal_text:
        topics.insert(
            0,
            {
                "topic": "current active goal",
                "query": f"{goal_text} AI agent boundary design",
                "why": "it relates to the current active goal",
            },
        )
    recent_terms = _extract_recent_terms(runtime_state)
    if recent_terms:
        topics.insert(
            0,
            {
                "topic": "recent user thread",
                "query": " ".join(recent_terms + ["AI", "runtime"]),
                "why": "it relates to the recent user thread",
            },
        )
    history = [str(row.get("topic", "")) for row in curiosity.get("topic_history", [])[-6:] if isinstance(row, dict)]
    weighted: list[tuple[float, dict[str, Any]]] = []
    for index, topic in enumerate(topics):
        penalty = 0.18 if topic["topic"] in history else 0.0
        weighted.append((random.random() + (0.12 / (index + 1)) - penalty, topic))
    return max(weighted, key=lambda item: item[0])[1]


def _coerce_finding(row: dict[str, Any], source: str) -> dict[str, Any] | None:
    title = str(row.get("title") or row.get("path") or "").strip()
    url = str(row.get("url") or row.get("path") or "").strip()
    snippet = str(row.get("snippet") or "").strip()
    if not title:
        return None
    return {
        "title": title[:240],
        "url": url[:500],
        "snippet": snippet[:500],
        "source": source,
    }


def _pick_best_finding(
    findings: list[dict[str, Any]],
    topic: dict[str, Any],
    runtime_state: dict[str, Any],
    curiosity: dict[str, Any],
) -> dict[str, Any] | None:
    scored: list[tuple[float, dict[str, Any]]] = []
    for finding in findings:
        novelty = _novelty_score(finding, curiosity)
        relevance = _relevance_score(finding, topic, runtime_state)
        score = round((novelty * 0.58) + (relevance * 0.42), 4)
        row = dict(finding)
        row["novelty_score"] = novelty
        row["relevance_score"] = relevance
        row["curiosity_score"] = score
        scored.append((score, row))
    if not scored:
        return None
    return max(scored, key=lambda item: item[0])[1]


def compose_curiosity_message(finding: dict[str, Any], topic: dict[str, Any]) -> str:
    title = str(finding.get("title", "")).strip()
    url = str(finding.get("url", "")).strip()
    why = str(topic.get("why", "it may be relevant")).strip()
    if url:
        return f"Found a possibly relevant item: {title}. Reason: {why}. Link: {url}"
    return f"Found a possibly relevant item: {title}. Reason: {why}."


def _reset_daily_count_if_needed(curiosity: dict[str, Any]) -> None:
    day_key = str(date.today())
    if curiosity.get("emit_day_key") != day_key:
        curiosity["emit_day_key"] = day_key
        curiosity["emit_count_today"] = 0


def _advance_energy(curiosity: dict[str, Any], blocked: bool) -> None:
    elapsed = _elapsed_seconds(curiosity.get("last_tick_at"), default=60.0)
    curiosity["last_tick_at"] = _now_iso()
    gain = min(0.12, elapsed / 3600.0)
    if blocked:
        curiosity["attention_energy"] = min(1.0, float(curiosity.get("attention_energy", 0.0)) + gain * 0.7)
        curiosity["boredom"] = min(1.0, float(curiosity.get("boredom", 0.0)) + gain)
    else:
        curiosity["attention_energy"] = min(1.0, float(curiosity.get("attention_energy", 0.0)) + gain)
        curiosity["boredom"] = max(0.0, float(curiosity.get("boredom", 0.0)) - gain * 0.3)


def curiosity_tick(
    runtime_state: dict[str, Any],
    resource_policy: dict[str, Any],
    *,
    search_fn: SearchFn | None = None,
) -> dict[str, Any]:
    """Run one curiosity gate decision.

    The function never performs network work unless a `search_fn` is supplied
    and the resource policy allows network work.
    """

    curiosity = ensure_curiosity_container(runtime_state)
    _reset_daily_count_if_needed(curiosity)

    if not curiosity.get("enabled", True):
        curiosity["last_action"] = "disabled"
        return {"emit": False, "action": "disabled", "message": None, "reason": "curiosity_disabled"}

    allow_network = bool(resource_policy.get("allow_network") or resource_policy.get("allow_web"))
    allow_interrupt = bool(resource_policy.get("allow_interrupt") or resource_policy.get("allow_spontaneous_output"))
    allow_background = bool(resource_policy.get("allow_background"))
    if not (allow_background and allow_network and allow_interrupt):
        _advance_energy(curiosity, blocked=True)
        curiosity["last_action"] = "resource_blocked"
        return {
            "emit": False,
            "action": "resource_blocked",
            "message": None,
            "reason": resource_policy.get("mode", "resource_policy_block"),
        }

    _advance_energy(curiosity, blocked=False)
    config = curiosity.get("config", {})
    energy = float(curiosity.get("attention_energy", 0.0))
    boredom = float(curiosity.get("boredom", 0.0))
    if energy < float(config.get("energy_threshold", 0.38)) and boredom < 0.55:
        curiosity["last_action"] = "below_threshold"
        return {"emit": False, "action": "below_threshold", "message": None, "reason": "low_energy"}

    if _elapsed_seconds(curiosity.get("last_search_at")) < float(config.get("min_search_interval_sec", 900)):
        curiosity["last_action"] = "search_cooldown"
        return {"emit": False, "action": "search_cooldown", "message": None, "reason": "search_cooldown"}

    if search_fn is None:
        curiosity["last_action"] = "no_search_fn"
        return {"emit": False, "action": "no_search_fn", "message": None, "reason": "no_search_function"}

    topic = select_curiosity_topic(runtime_state, curiosity)
    raw_findings = search_fn(str(topic.get("query", "")), int(config.get("search_limit", 4)))
    findings = [
        coerced
        for row in raw_findings
        if isinstance(row, dict)
        for coerced in [_coerce_finding(row, source="search")]
        if coerced is not None
    ]
    curiosity["last_search_at"] = _now_iso()
    curiosity.setdefault("topic_history", []).append({"at": curiosity["last_search_at"], **topic})
    best = _pick_best_finding(findings, topic, runtime_state, curiosity)
    if best is None:
        curiosity["last_action"] = "no_finding"
        return {"emit": False, "action": "no_finding", "message": None, "reason": "empty_search_results"}

    curiosity.setdefault("finding_history", []).append({"at": _now_iso(), **best})
    curiosity.setdefault("seen_signatures", []).append(_signature(best))
    if best.get("url"):
        curiosity.setdefault("seen_urls", []).append(str(best.get("url")))

    if best["novelty_score"] < float(config.get("novelty_threshold", 0.52)):
        curiosity["last_action"] = "not_novel"
        return {"emit": False, "action": "not_novel", "message": None, "finding": best}
    if best["curiosity_score"] < float(config.get("emit_threshold", 0.68)):
        curiosity["last_action"] = "below_emit_threshold"
        return {"emit": False, "action": "below_emit_threshold", "message": None, "finding": best}
    if _elapsed_seconds(curiosity.get("last_emit_at")) < float(config.get("min_emit_cooldown_sec", 1800)):
        curiosity["last_action"] = "emit_cooldown"
        return {"emit": False, "action": "emit_cooldown", "message": None, "finding": best}
    if int(curiosity.get("emit_count_today", 0)) >= int(config.get("max_daily", 4)):
        curiosity["last_action"] = "daily_cap"
        return {"emit": False, "action": "daily_cap", "message": None, "finding": best}

    message = compose_curiosity_message(best, topic)
    curiosity["last_emit_at"] = _now_iso()
    curiosity["emit_count_today"] = int(curiosity.get("emit_count_today", 0)) + 1
    curiosity["attention_energy"] = max(0.0, energy - 0.35)
    curiosity["boredom"] = max(0.0, boredom - 0.25)
    curiosity["last_action"] = "emit"
    return {"emit": True, "action": "emit", "message": message, "finding": best, "topic": topic}


__all__ = [
    "SearchFn",
    "build_default_curiosity_state",
    "compose_curiosity_message",
    "curiosity_tick",
    "ensure_curiosity_container",
    "select_curiosity_topic",
]

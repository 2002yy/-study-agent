"""G18 decision 4: auto-escalation judge for deep research.

Two layers:
1. Deterministic heuristics (this module) — cheap, hermetic, always-on gate.
2. An optional LLM pre-judgement hook can be wired later behind the same
   interface; the heuristic stays as the conservative floor.

Sensitivity is user-tunable (decision 4): "conservative" requires strong
signals; "balanced" (default) needs moderate ones; "eager" escalates on weak
ones. Regardless of sensitivity, short conversational questions never
escalate, and an explicit deep-research prefix always does.
"""

from __future__ import annotations

import re

DEEP_RESEARCH_PREFIX = "请深度研究："

_SENSITIVITY_MIN_SCORE = {
    "conservative": 5,
    "balanced": 3,
    "eager": 2,
}

# Multi-part / comparison signals: the question spans several aspects.
_MULTI_PART = re.compile(
    r"[；;]|以及|并且|同时|对比|比较|各(有)?什么|分别|vs\.?\b|and\s+compare|pros\s+and\s+cons",
    re.I,
)
# Research verbs that imply investigation depth.
_RESEARCH_VERB = re.compile(
    r"深入|全面|充分|调研|研究|综述|梳理|来龙去脉|最新进展|现状|评测|选型|"
    r"in depth|deep dive|comprehensive|state of the art|landscape|survey|"
    r"thoroughly|research",
    re.I,
)
# Conversational one-liners must never escalate.
_CONVERSATIONAL = re.compile(
    r"^\s*(hi|hello|hey|thanks|thank you|你好|您好|谢谢|早上好|晚上好)[!！。.\s]*$",
    re.I,
)


def escalation_score(user_input: str) -> int:
    """0..5 heuristic complexity score for a chat question."""
    text = str(user_input or "").strip()
    if not text:
        return 0
    score = 0
    if len(text) >= 40:
        score += 1
    if len(text) >= 90:
        score += 1
    if _MULTI_PART.search(text):
        score += 1
    if _RESEARCH_VERB.search(text):
        score += 1
    # Multiple explicit question marks suggest several information needs.
    if text.count("？") + text.count("?") >= 2:
        score += 1
    return score


def should_use_deep_research(
    user_input: str,
    *,
    sensitivity: str = "balanced",
) -> bool:
    """Decide whether a chat question escalates to the deep-research pipeline."""
    text = str(user_input or "").strip()
    if not text or _CONVERSATIONAL.match(text):
        return False
    if text.startswith(DEEP_RESEARCH_PREFIX):
        return True
    threshold = _SENSITIVITY_MIN_SCORE.get(sensitivity)
    if threshold is None:
        return False
    return escalation_score(text) >= threshold

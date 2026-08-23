"""G18 decision 4: auto-escalation judge heuristics."""

from __future__ import annotations

from src.web.deep_research import escalation_score, should_use_deep_research


def test_explicit_prefix_always_escalates():
    assert should_use_deep_research(
        "请深度研究：Rust async runtime landscape", sensitivity="conservative"
    )


def test_conversational_questions_never_escalate():
    for text in ["你好", "hi!", "谢谢！", "thanks"]:
        assert not should_use_deep_research(text, sensitivity="eager")


def test_multi_part_research_question_escalates_on_balanced():
    text = (
        "对比一下目前主流的 Rust async runtime（tokio、async-std、smol）："
        "各自的性能现状如何？生态成熟度怎么样？以及 2026 年的最新进展？"
    )
    assert should_use_deep_research(text, sensitivity="balanced")


def test_simple_factual_question_does_not_escalate():
    assert not should_use_deep_research("Python 的 list.append 返回什么？")


def test_conservative_requires_stronger_signals():
    # Three signals: comparison marker, research verbs, and length (>=40).
    moderate = (
        "请深入对比 Rust 与 Go 在内存管理机制上的设计差异与性能现状，"
        "并分别说明两者生态成熟度以及各自的适用场景"
    )
    score = escalation_score(moderate)
    assert 3 <= score < 5, score
    assert should_use_deep_research(moderate, sensitivity="balanced")
    assert not should_use_deep_research(moderate, sensitivity="conservative")


def test_unknown_sensitivity_never_escalates():
    assert not should_use_deep_research("深入调研某主题", sensitivity="turbo")

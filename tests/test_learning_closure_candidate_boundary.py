from __future__ import annotations

from src.application.closure_input_builder import build_structured_closure_input
from src.domain.runtime_entities import ChatTurn
from src.structured_closure import normalize_structured_closure_result


COMMIT_SHA = "a" * 40


def test_closure_input_projects_only_commit_pinned_github_source_calls():
    turn = ChatTurn(
        id="turn-source",
        thread_id="thread-1",
        user_message="源码里 resume 是怎么恢复的？",
        assistant_message="先看 SessionService。",
        status="completed",
        rag_snapshot={
            "web_tools": {
                "calls": [
                    {
                        "name": "web_search",
                        "arguments": {"query": "untrusted web result"},
                        "result": {"ok": True},
                    },
                    {
                        "name": "github_search",
                        "arguments": {
                            "repo_url": "https://github.com/2002yy/study-agent",
                            "query": "SessionService resume",
                        },
                        "result": {
                            "ok": True,
                            "commit_sha": COMMIT_SHA,
                            "provider_status": "success",
                            "score": 999,
                        },
                    },
                    {
                        "name": "github_search",
                        "arguments": {
                            "repo_url": "https://github.com/2002yy/study-agent",
                            "query": "missing commit",
                        },
                        "result": {"ok": True},
                    },
                ]
            }
        },
        pedagogy_snapshot={"move": "invite_explanation"},
    )

    structured = build_structured_closure_input(
        thread_id="thread-1",
        closure_eligibility="learning_summary",
        task_contract={"task_intent": "learn"},
        learning_state={"objective": "理解 durable resume"},
        all_turns=[turn],
        completed_turns=[turn],
    )

    assert structured["github_learning_sources"] == [
        {
            "source_ref": "github_source:turn-source:1",
            "turn_id": "turn-source",
            "tool_name": "github_search",
            "repo_url": "https://github.com/2002yy/study-agent",
            "query": "SessionService resume",
            "commit_sha": COMMIT_SHA,
        }
    ]
    assert "github_source:turn-source:1" in structured["allowed_source_refs"]
    serialized = str(structured["github_learning_sources"])
    assert "provider_status" not in serialized
    assert "score" not in serialized


def test_durable_candidate_requires_learning_summary_real_eval_and_known_source_ref():
    structured = {
        "schema_version": "learning-closure-input-v1",
        "summary_kind": "learning_summary",
        "allowed_source_refs": ["github_source:turn-source:0"],
        "final_pedagogy_evaluation": {
            "id": "eval-1",
            "turn_id": "turn-eval",
            "learner_input": "恢复时 durable state 是 owner，不需要重放完整 turns。",
            "deterministic_result": {"is_claim": True},
            "semantic_result": {
                "claims": ["恢复 durable learning state 不需要重放完整聊天 turns。"]
            },
        },
        "github_learning_sources": [
            {
                "source_ref": "github_source:turn-source:0",
                "repo_url": "https://github.com/2002yy/study-agent",
                "query": "durable resume",
                "commit_sha": COMMIT_SHA,
            }
        ],
    }
    raw = {
        "candidates": [],
        "durable_learning_candidate": {
            "source_ref": "github_source:turn-source:0",
            "claim_text": "恢复 durable learning state 不需要重放完整聊天 turns。",
            "claim_kind": "invariant",
            "scope": "project",
            "next_step": "验证刷新后仍可恢复。",
        },
    }

    normalized = normalize_structured_closure_result(raw, structured_input=structured)

    durable = normalized["durable_learning_candidate"]
    assert durable is not None
    assert durable["source_ref"] == "github_source:turn-source:0"
    assert durable["evaluation_id"] == "eval-1"
    assert durable["evaluation_turn_id"] == "turn-eval"

    unknown = normalize_structured_closure_result(
        {
            **raw,
            "durable_learning_candidate": {
                **raw["durable_learning_candidate"],
                "source_ref": "github_source:invented",
            },
        },
        structured_input=structured,
    )
    assert unknown["durable_learning_candidate"] is None

    self_report = normalize_structured_closure_result(
        raw,
        structured_input={
            **structured,
            "final_pedagogy_evaluation": {
                "id": "eval-self-report",
                "turn_id": "turn-self-report",
                "learner_input": "我懂了",
                "deterministic_result": {"is_claim": False},
                "semantic_result": None,
            },
        },
    )
    assert self_report["durable_learning_candidate"] is None

from __future__ import annotations

import json

from src.application.chat_service import _normalized_turn_truth
from src.domain.answer_claims import (
    answer_content_hash,
    build_answer_claim_snapshot,
    deterministic_claim_id,
)
from src.domain.runtime_entities import ChatTurn
from src.infrastructure.sqlite.database import RuntimeDatabase
from src.repositories.runtime_repository import RuntimeRepository


ANSWER = "FastAPI validates request data from Python type hints."


def _rag() -> dict:
    return {
        "status": "found",
        "results": [
            {
                "chunk": {
                    "chunk_id": "chunk-1",
                    "title": "FastAPI validation",
                    "source_path": "docs/fastapi.md",
                    "text": ANSWER,
                },
                "score": 0.92,
            }
        ],
    }


def _pedagogy() -> dict:
    return {
        "evidence_ids": ["chunk-1"],
        "evidence_disclosure": "single_evidence_unit",
        "evidence_units": [
            {
                "source_id": "chunk-1",
                "type": "document_chunk",
                "content": ANSWER,
                "citation": "docs/fastapi.md",
                "disclosure_role": "supporting_material",
                "reliability": 0.9,
            }
        ],
    }


def _supplied_snapshot() -> dict:
    claim_id = deterministic_claim_id(
        answer_hash=answer_content_hash(ANSWER),
        claim_text=ANSWER,
    )
    return build_answer_claim_snapshot(
        answer=ANSWER,
        claims=[
            {
                "text": ANSWER,
                "kind": "factual",
                "status": "asserted",
                "source": "application_supplied",
            }
        ],
        claim_links=[
            {
                "claim_id": claim_id,
                "evidence_id": "chunk-1",
                "support_type": "direct_support",
                "confidence": 0.95,
            }
        ],
        known_evidence_ids=["chunk-1"],
        producer="test-producer",
        status="supplied",
    ).to_dict()


def test_completed_chat_turn_accepts_hash_matched_claim_truth_and_projects_links():
    rag = _rag()
    rag["answer_claim_snapshot"] = _supplied_snapshot()

    turn = ChatTurn(
        id="turn-1",
        thread_id="thread-1",
        assistant_message=ANSWER,
        status="completed",
        rag_snapshot=rag,
        pedagogy_snapshot=_pedagogy(),
    )

    assert turn.answer_claim_snapshot["status"] == "supplied"
    assert turn.answer_claim_snapshot["answer_hash"] == answer_content_hash(ANSWER)
    assert turn.answer_claim_snapshot["claims"][0]["text"] == ANSWER
    assert turn.evidence_snapshot["claim_links"] == [
        {
            "claim_id": turn.answer_claim_snapshot["claims"][0]["id"],
            "evidence_id": "chunk-1",
            "support_type": "direct_support",
            "confidence": 0.95,
        }
    ]


def test_completed_chat_turn_rejects_claims_for_unknown_evidence():
    snapshot = _supplied_snapshot()
    snapshot["claim_links"][0]["evidence_id"] = "missing"
    rag = _rag()
    rag["answer_claim_snapshot"] = snapshot

    turn = ChatTurn(
        id="turn-2",
        thread_id="thread-1",
        assistant_message=ANSWER,
        status="completed",
        rag_snapshot=rag,
        pedagogy_snapshot=_pedagogy(),
    )

    assert turn.answer_claim_snapshot["status"] == "rejected"
    assert "unknown evidence id" in turn.answer_claim_snapshot["reason"]
    assert turn.answer_claim_snapshot["claims"] == []
    assert turn.evidence_snapshot["claim_links"] == []


def test_streaming_interrupted_and_failed_turns_invalidate_supplied_claims():
    for status in ("streaming", "interrupted", "failed", "abandoned"):
        rag = _rag()
        rag["answer_claim_snapshot"] = _supplied_snapshot()
        turn = ChatTurn(
            id=f"turn-{status}",
            thread_id="thread-1",
            assistant_message=ANSWER,
            status=status,
            rag_snapshot=rag,
            pedagogy_snapshot=_pedagogy(),
        )

        assert turn.answer_claim_snapshot["status"] == "unavailable"
        assert turn.answer_claim_snapshot["answer_hash"] == ""
        assert turn.answer_claim_snapshot["reason"] == f"turn_status:{status}"
        assert turn.evidence_snapshot["claim_links"] == []


def test_completion_boundary_persists_final_hash_when_no_claim_producer_exists():
    streaming = ChatTurn(
        id="turn-complete",
        thread_id="thread-1",
        user_message="Explain FastAPI validation",
        assistant_message="",
        status="streaming",
        role="nahida",
        mode="socratic",
        model="flash",
        rag_snapshot=_rag(),
        pedagogy_snapshot=_pedagogy(),
        operation_id="op-1",
    )

    completed = _normalized_turn_truth(
        turn=streaming,
        fallback_turn_id=streaming.id,
        thread_id=streaming.thread_id,
        user_message=streaming.user_message,
        assistant_message=ANSWER,
        status="completed",
        role=streaming.role,
        mode=streaming.mode,
        model=streaming.model,
        route_snapshot={},
        rag_snapshot=streaming.rag_snapshot,
        pedagogy_snapshot=streaming.pedagogy_snapshot,
        parent_turn_id=None,
        operation_id=streaming.operation_id,
        conversation_instruction="",
    )

    assert completed.answer_claim_snapshot == {
        "schema_version": "answer-claim-snapshot-v1",
        "answer_hash": answer_content_hash(ANSWER),
        "claims": [],
        "claim_links": [],
        "producer": "none",
        "status": "unavailable",
        "reason": "producer_unavailable",
    }


def test_continuation_invalidates_old_claim_truth_until_new_final_answer():
    completed_rag = _rag()
    completed_rag["answer_claim_snapshot"] = _supplied_snapshot()
    previous = ChatTurn(
        id="turn-continuation",
        thread_id="thread-1",
        user_message="Explain validation",
        assistant_message=ANSWER,
        status="completed",
        role="nahida",
        mode="socratic",
        model="flash",
        rag_snapshot=completed_rag,
        pedagogy_snapshot=_pedagogy(),
        operation_id="op-old",
    )

    resumed = _normalized_turn_truth(
        turn=previous,
        fallback_turn_id=previous.id,
        thread_id=previous.thread_id,
        user_message=previous.user_message,
        assistant_message=f"{ANSWER} More detail follows...",
        status="streaming",
        role=previous.role,
        mode=previous.mode,
        model=previous.model,
        route_snapshot={},
        rag_snapshot=previous.rag_snapshot,
        pedagogy_snapshot=previous.pedagogy_snapshot,
        parent_turn_id=None,
        operation_id="op-new",
        conversation_instruction="",
    )

    assert resumed.answer_claim_snapshot["status"] == "unavailable"
    assert resumed.answer_claim_snapshot["answer_hash"] == ""
    assert resumed.answer_claim_snapshot["reason"] == "turn_status:streaming"
    assert resumed.evidence_snapshot["claim_links"] == []


def test_retry_child_does_not_inherit_parent_claim_snapshot():
    child = ChatTurn(
        id="turn-retry-child",
        thread_id="thread-1",
        parent_turn_id="turn-failed-parent",
        status="pending",
        rag_snapshot=_rag(),
        pedagogy_snapshot=_pedagogy(),
    )

    assert child.answer_claim_snapshot["status"] == "unavailable"
    assert child.answer_claim_snapshot["reason"] == "turn_status:pending"
    assert child.answer_claim_snapshot["claims"] == []


def test_legacy_completed_row_without_claim_snapshot_projects_unavailable_without_rewrite(
    tmp_path,
):
    database = RuntimeDatabase(tmp_path / "runtime.db")
    repository = RuntimeRepository(database)
    repository.ensure_chat_thread("legacy-thread")

    with database.connect() as connection:
        connection.execute(
            """
            INSERT INTO chat_turns(
                id, thread_id, user_message, assistant_message, status, role, mode, model,
                route_snapshot, rag_snapshot, pedagogy_snapshot, parent_turn_id, operation_id,
                conversation_instruction, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-turn",
                "legacy-thread",
                "question",
                ANSWER,
                "completed",
                "nahida",
                "socratic",
                "flash",
                "{}",
                json.dumps(_rag(), ensure_ascii=False),
                json.dumps(_pedagogy(), ensure_ascii=False),
                None,
                None,
                "",
                "2026-07-27T00:00:00+00:00",
                "2026-07-27T00:00:00+00:00",
            ),
        )

    stored = repository.get_chat_turn("legacy-turn")

    assert stored is not None
    assert stored.answer_claim_snapshot["status"] == "unavailable"
    assert stored.answer_claim_snapshot["answer_hash"] == answer_content_hash(ANSWER)
    assert stored.answer_claim_snapshot["reason"] == "producer_unavailable"

    with database.connect() as connection:
        raw = connection.execute(
            "SELECT rag_snapshot FROM chat_turns WHERE id = 'legacy-turn'"
        ).fetchone()[0]
    assert "answer_claim_snapshot" not in json.loads(raw)

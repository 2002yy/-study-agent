from __future__ import annotations

import json

from src.domain.runtime_entities import ChatTurn
from src.infrastructure.sqlite.database import RuntimeDatabase
from src.repositories.runtime_repository import RuntimeRepository


def _rag_snapshot() -> dict:
    return {
        "status": "found",
        "results": [
            {
                "chunk": {
                    "chunk_id": "chunk-1",
                    "title": "TaskContract",
                    "source_path": "docs/task_contract.md",
                    "start_line": 10,
                    "end_line": 20,
                    "text": "contract text",
                },
                "score": 0.82,
            }
        ],
    }


def _pedagogy_snapshot() -> dict:
    return {
        "mode": "socratic",
        "phase": "scaffold",
        "move": "give_hint",
        "evidence_ids": ["chunk-1"],
        "evidence_disclosure": "single_evidence_unit",
        "evidence_units": [
            {
                "source_id": "chunk-1",
                "type": "document_chunk",
                "content": "contract text",
                "citation": "docs/task_contract.md:L10-L20",
                "disclosure_role": "supporting_material",
                "reliability": 0.9,
            }
        ],
    }


def test_chat_turn_attaches_server_evidence_snapshot_before_persistence():
    rag = _rag_snapshot()
    turn = ChatTurn(
        id="turn-1",
        thread_id="thread-1",
        status="completed",
        rag_snapshot=rag,
        pedagogy_snapshot=_pedagogy_snapshot(),
    )

    assert rag["evidence_snapshot"] == turn.evidence_snapshot
    assert turn.evidence_snapshot["schema_version"] == "evidence-snapshot-v1"
    assert turn.evidence_snapshot["refs"][0]["id"] == "chunk-1"
    assert turn.evidence_snapshot["refs"][0]["lifecycle_status"] == "selected"
    assert turn.evidence_snapshot["claim_links"] == [
        {
            "claim_id": "pedagogy-plan",
            "evidence_id": "chunk-1",
            "support_type": "explicit_pedagogy_reference",
            "confidence": 1.0,
        }
    ]


def test_repository_round_trip_preserves_server_evidence_snapshot(tmp_path):
    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "runtime.db"))
    repository.ensure_chat_thread("thread-1")
    turn = ChatTurn(
        id="turn-1",
        thread_id="thread-1",
        status="completed",
        rag_snapshot=_rag_snapshot(),
        pedagogy_snapshot=_pedagogy_snapshot(),
    )

    repository.add_chat_turn(turn)
    stored = repository.get_chat_turn("turn-1")

    assert stored is not None
    assert stored.evidence_snapshot == turn.evidence_snapshot
    assert stored.rag_snapshot["evidence_snapshot"] == turn.evidence_snapshot


def test_legacy_row_without_snapshot_is_projected_on_read_without_migration(tmp_path):
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
                "answer",
                "completed",
                "nahida",
                "socratic",
                "flash",
                "{}",
                json.dumps(_rag_snapshot(), ensure_ascii=False),
                json.dumps(_pedagogy_snapshot(), ensure_ascii=False),
                None,
                None,
                "",
                "2026-07-26T00:00:00+00:00",
                "2026-07-26T00:00:00+00:00",
            ),
        )

    stored = repository.get_chat_turn("legacy-turn")

    assert stored is not None
    assert stored.evidence_snapshot["schema_version"] == "evidence-snapshot-v1"
    assert stored.evidence_snapshot["refs"][0]["id"] == "chunk-1"

    with database.connect() as connection:
        raw = connection.execute(
            "SELECT rag_snapshot FROM chat_turns WHERE id = 'legacy-turn'"
        ).fetchone()[0]
    assert "evidence_snapshot" not in json.loads(raw)


def test_truly_empty_legacy_turn_remains_unchanged():
    turn = ChatTurn(id="empty", thread_id="thread", status="completed")

    assert turn.rag_snapshot == {}
    assert turn.evidence_snapshot == {
        "schema_version": "evidence-snapshot-v1",
        "disclosure_policy": "none",
        "refs": [],
        "claim_links": [],
    }

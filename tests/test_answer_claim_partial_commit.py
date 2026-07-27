from __future__ import annotations

from src.application.chat_service import ChatCommand
from tests.test_chat_service import _service


def test_partial_commit_cannot_inject_client_answer_claim_snapshot(tmp_path):
    service, repository = _service(tmp_path)
    prepared = service.start_turn(
        ChatCommand(
            user_input="server question",
            thread_id="chat-claim-injection",
            turn_id="turn-claim-injection",
        )
    )
    server_rag = prepared.turn.rag_snapshot

    stored, changed = service.commit_partial_turn(
        thread_id="chat-claim-injection",
        turn_id="turn-claim-injection",
        operation_id=prepared.turn.operation_id or "",
        user_input="client replacement",
        assistant_message="partial answer",
        role="client-role",
        mode="client-mode",
        model="client-model",
        route_snapshot={"role": "client-role"},
        rag_snapshot={
            "answer_claim_snapshot": {
                "schema_version": "answer-claim-snapshot-v1",
                "answer_hash": "forged",
                "claims": [
                    {
                        "id": "claim_forged",
                        "text": "forged claim",
                        "kind": "factual",
                        "status": "asserted",
                        "source": "application_supplied",
                    }
                ],
                "claim_links": [],
                "producer": "client",
                "status": "validated",
                "reason": "",
            }
        },
        conversation_instruction="client replacement",
    )

    assert changed is True
    assert stored.status == "interrupted"
    assert stored.rag_snapshot == server_rag
    assert stored.answer_claim_snapshot["status"] == "unavailable"
    assert stored.answer_claim_snapshot["reason"] == "turn_status:interrupted"
    assert all(
        claim.get("text") != "forged claim"
        for claim in stored.answer_claim_snapshot["claims"]
    )
    persisted = repository.get_chat_turn("turn-claim-injection")
    assert persisted is not None
    assert persisted.rag_snapshot == server_rag

"""Regression tests for server-owned Evidence Gate truth at answer publication."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

from src.application.answer_claim_binder import (
    ANSWER_CLAIM_BINDER_PRODUCER,
    AnswerClaimBindingRequest,
    AnswerClaimBindingRow,
    bind_answer_claims,
    factual_claims_fully_bound,
)
from src.application.research_evidence import research_binding_rows
from src.domain.answer_claims import (
    AnswerClaimSnapshotV1,
    AnswerClaimV1,
    answer_content_hash,
    deterministic_claim_id,
)
from src.domain.evidence import ClaimEvidenceLinkV1

ANSWER = "该版本已正式发布。"
EVIDENCE_ID = "evidence_support_1"


def _run_with_brief(brief: Mapping[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        id="web_lookup_1",
        research_context={"claim_engine_evidence_brief": dict(brief)},
    )


def _brief(*, gate_status: str = "pass", rows: list[dict[str, Any]] | None = None, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "research-evidence-brief-v1",
        "gate_status": gate_status,
        "conditional_wording_required": False,
        "unresolved_conflicts": [],
        "open_critical_claim_ids": [],
        "open_gap_ids": [],
        "eligible_evidence": rows or [],
    }
    payload.update(extra)
    return payload


def _evidence(
    evidence_id: str = EVIDENCE_ID,
    *,
    relation: str = "supports",
    strength: float | str = 0.9,
) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "claim_id": "research_claim_1",
        "relation": relation,
        "strength": strength,
        "source_role": "primary",
        "source_cluster_id": "cluster_1",
        "title": "Official source",
        "url": "https://official.example/source",
        "locator": "paragraph 4",
        "anchored_spans": ["official confirmation"],
        "caveats": [],
    }


def _binding_row(*, relation: str = "supports", strength: str = "0.9") -> AnswerClaimBindingRow:
    return AnswerClaimBindingRow(
        evidence_id=EVIDENCE_ID,
        title="Official source",
        url="https://official.example/source",
        source_role="primary",
        source_cluster_id="cluster_1",
        relation=relation,
        strength=strength,
        locator="paragraph 4",
        anchored_spans=("official confirmation",),
    )


def _model_payload(evidence_id: str = EVIDENCE_ID) -> str:
    return json.dumps(
        {
            "refused": False,
            "segments": [
                {
                    "segment_ref": "s1",
                    "kind": "factual",
                    "status": "asserted",
                    "evidence_support": [evidence_id],
                }
            ],
        },
        ensure_ascii=False,
    )


def test_projection_requires_full_evidence_gate_pass() -> None:
    row = _evidence()
    assert research_binding_rows(_run_with_brief(_brief(rows=[row])))
    assert research_binding_rows(
        _run_with_brief(_brief(gate_status="block", rows=[row]))
    ) == []
    assert research_binding_rows(
        _run_with_brief(_brief(gate_status="partial", rows=[row]))
    ) == []
    assert research_binding_rows(
        _run_with_brief(
            _brief(rows=[row], conditional_wording_required=True)
        )
    ) == []
    assert research_binding_rows(
        _run_with_brief(
            _brief(rows=[row], unresolved_conflicts=[{"claim_id": "c1"}])
        )
    ) == []
    assert research_binding_rows(
        _run_with_brief(_brief(rows=[row], open_critical_claim_ids=["c1"]))
    ) == []
    assert research_binding_rows(
        _run_with_brief(_brief(rows=[row], open_gap_ids=["g1"]))
    ) == []


def test_projection_exposes_only_positive_strong_support() -> None:
    rows = [
        _evidence("support_strong", relation="supports", strength=0.8),
        _evidence("support_threshold", relation="supports", strength=0.7),
        _evidence("support_weak", relation="supports", strength=0.69),
        _evidence("contradiction", relation="contradicts", strength=0.95),
        _evidence("qualifier", relation="qualifies", strength=0.95),
        _evidence("background", relation="background", strength=1.0),
    ]
    projected = research_binding_rows(_run_with_brief(_brief(rows=rows)))
    assert [row["evidence_id"] for row in projected] == [
        "support_strong",
        "support_threshold",
    ]


def test_binder_rejects_known_contradictory_evidence_id() -> None:
    bound = bind_answer_claims(
        request=AnswerClaimBindingRequest(
            question="发布了吗？",
            final_answer=ANSWER,
            evidence_rows=(_binding_row(relation="contradicts", strength="0.95"),),
        ),
        model_fn=lambda _messages: _model_payload(),
    )
    assert bound.snapshot.status == "rejected"
    assert bound.snapshot.reason == "ineligible_evidence_support"


def test_binder_rejects_known_weak_support_id() -> None:
    bound = bind_answer_claims(
        request=AnswerClaimBindingRequest(
            question="发布了吗？",
            final_answer=ANSWER,
            evidence_rows=(_binding_row(strength="0.4"),),
        ),
        model_fn=lambda _messages: _model_payload(),
    )
    assert bound.snapshot.status == "rejected"
    assert bound.snapshot.reason == "ineligible_evidence_support"


def test_binder_preserves_server_owned_strength_in_link() -> None:
    bound = bind_answer_claims(
        request=AnswerClaimBindingRequest(
            question="发布了吗？",
            final_answer=ANSWER,
            evidence_rows=(_binding_row(strength="0.81"),),
        ),
        model_fn=lambda _messages: _model_payload(),
    )
    assert bound.snapshot.status == "validated"
    assert len(bound.snapshot.claim_links) == 1
    link = bound.snapshot.claim_links[0]
    assert link.support_type == "direct_support"
    assert link.confidence == 0.81


def test_publication_fallback_rejects_low_confidence_positive_link() -> None:
    answer_hash = answer_content_hash(ANSWER)
    claim_id = deterministic_claim_id(answer_hash=answer_hash, claim_text=ANSWER)
    snapshot = AnswerClaimSnapshotV1(
        answer_hash=answer_hash,
        claims=(
            AnswerClaimV1(
                id=claim_id,
                text=ANSWER,
                kind="factual",
                status="asserted",
                source="provider_structured",
            ),
        ),
        claim_links=(
            ClaimEvidenceLinkV1(
                claim_id=claim_id,
                evidence_id=EVIDENCE_ID,
                support_type="direct_support",
                confidence=0.2,
            ),
        ),
        producer=ANSWER_CLAIM_BINDER_PRODUCER,
        status="validated",
    )
    assert factual_claims_fully_bound(snapshot) is False


def test_newline_is_a_deterministic_segment_boundary() -> None:
    answer = "该版本已正式发布。\n建议立即升级。"
    seen: list[str] = []

    def model_fn(messages: Sequence[Mapping[str, Any]]) -> str:
        seen.append(str(messages[1]["content"]))
        return json.dumps(
            {
                "refused": False,
                "segments": [
                    {
                        "segment_ref": "s1",
                        "kind": "factual",
                        "status": "asserted",
                        "evidence_support": [EVIDENCE_ID],
                    },
                    {
                        "segment_ref": "s2",
                        "kind": "recommendation",
                        "evidence_support": [],
                    },
                ],
            },
            ensure_ascii=False,
        )

    bound = bind_answer_claims(
        request=AnswerClaimBindingRequest(
            question="发布了吗？",
            final_answer=answer,
            evidence_rows=(_binding_row(),),
        ),
        model_fn=model_fn,
    )
    assert bound.snapshot.status == "validated"
    assert "[s1]" in seen[0] and "[s2]" in seen[0]

"""Tests for the production answer-claim binder.

The binder turns an already-generated final answer into structured claims
bound to existing server-owned evidence ids.  Every test uses a fake model
function; no provider is called and no ChatTurn is written (wiring batch is
separate).
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

import pytest

from src.application.answer_claim_binder import (
    ANSWER_CLAIM_BINDER_PRODUCER,
    AnswerClaimBindingRequest,
    AnswerClaimBindingRow,
    bind_answer_claims,
)
from src.domain.answer_claims import (
    ANSWER_CLAIM_SCHEMA_VERSION,
    answer_content_hash,
    deterministic_claim_id,
)


def _row(evidence_id: str = "evidence_abc123", **extra: Any) -> AnswerClaimBindingRow:
    return AnswerClaimBindingRow(
        evidence_id=evidence_id,
        title=extra.get("title", "Example release"),
        url=extra.get("url", "https://official.example/release"),
        source_role=extra.get("source_role", "official_statement"),
        source_cluster_id=extra.get("source_cluster_id", "cluster_1"),
        relation=extra.get("relation", "supports"),
        strength=extra.get("strength", "strong"),
        locator=extra.get("locator", "第四段"),
        anchored_spans=extra.get("anchored_spans", ("official confirmation",)),
        caveats=extra.get("caveats", ()),
    )


def _answer() -> str:
    return "该版本已正式发布，并修复了已知问题。"


def _payload(
    claims: list[dict[str, Any]],
    claim_links: list[dict[str, Any]],
    *,
    refused: bool = False,
) -> str:
    return json.dumps(
        {"refused": refused, "claims": claims, "claim_links": claim_links},
        ensure_ascii=False,
    )


def _claim_payload(
    text: str,
    *,
    ref: str = "c1",
    kind: str = "factual",
    status: str = "asserted",
) -> dict[str, Any]:
    return {"id": ref, "text": text, "kind": kind, "status": status, "source": "provider_structured"}


def _link(claim_id: str, evidence_id: str, *, support_type: str = "direct_support") -> dict[str, Any]:
    return {
        "claim_id": claim_id,
        "evidence_id": evidence_id,
        "support_type": support_type,
        "confidence": 0.9,
    }


def _snapshot_of(model_result: Any) -> Any:
    return model_result.snapshot


def _request(answer: str = "", rows: tuple[AnswerClaimBindingRow, ...] = ()) -> AnswerClaimBindingRequest:
    return AnswerClaimBindingRequest(
        question="该版本发布了吗？",
        final_answer=answer or _answer(),
        evidence_rows=rows,
    )


def test_binds_single_factual_claim_to_existing_evidence() -> None:
    request = _request(rows=(_row(),))

    def model_fn(messages: Sequence[Mapping[str, Any]]) -> str:
        assert all(message["role"] in {"system", "user"} for message in messages)
        answer = "".join(str(m["content"]) for m in messages)
        assert "evidence_abc123" in answer
        assert "official.example" not in answer or "https://official.example" in answer
        return _payload(
            [_claim_payload("该版本已正式发布。", ref="c1")],
            [_link("c1", "evidence_abc123")],
        )

    bound = bind_answer_claims(request=request, model_fn=model_fn)
    snapshot = bound.snapshot
    assert snapshot.status == "validated"
    assert snapshot.producer == ANSWER_CLAIM_BINDER_PRODUCER
    assert snapshot.answer_hash == answer_content_hash(request.final_answer)
    assert len(snapshot.claims) == 1
    claim = snapshot.claims[0]
    expected_id = deterministic_claim_id(
        answer_hash=snapshot.answer_hash, claim_text="该版本已正式发布。"
    )
    # Server-assigned deterministic id wins over any upstream claim id.
    assert claim.id == expected_id
    assert snapshot.claim_links[0].claim_id == expected_id
    assert snapshot.claim_links[0].evidence_id == "evidence_abc123"
    assert snapshot.claim_links[0].support_type == "direct_support"
    assert snapshot.to_dict()["schema_version"] == ANSWER_CLAIM_SCHEMA_VERSION


def test_multiple_claims_bind_to_different_evidence() -> None:
    request = _request(
        rows=(_row("evidence_a1"), _row("evidence_b2")),
    )

    def model_fn(messages: Sequence[Mapping[str, Any]]) -> str:
        return _payload(
            [
                _claim_payload("该版本已正式发布。", ref="c1"),
                _claim_payload("修复了已知问题。", ref="c2"),
            ],
            [
                _link("c1", "evidence_a1"),
                _link("c2", "evidence_b2"),
            ],
        )

    snapshot = _snapshot_of(bind_answer_claims(request=request, model_fn=model_fn))
    assert snapshot.status == "validated"
    assert len(snapshot.claims) == 2
    assert len(snapshot.claim_links) == 2
    assert {link.evidence_id for link in snapshot.claim_links} == {
        "evidence_a1",
        "evidence_b2",
    }
    assert len({link.claim_id for link in snapshot.claim_links}) == 2


def test_same_evidence_supports_multiple_claims() -> None:
    request = _request(rows=(_row("evidence_a1"),))

    def model_fn(messages: Sequence[Mapping[str, Any]]) -> str:
        return _payload(
            [
                _claim_payload("该版本已正式发布。", ref="c1"),
                _claim_payload("修复了已知问题。", ref="c2"),
            ],
            [
                _link("c1", "evidence_a1"),
                _link("c2", "evidence_a1"),
            ],
        )

    snapshot = _snapshot_of(bind_answer_claims(request=request, model_fn=model_fn))
    assert snapshot.status == "validated"
    assert len(snapshot.claim_links) == 2
    assert all(link.evidence_id == "evidence_a1" for link in snapshot.claim_links)


def test_hallucinated_unknown_evidence_id_is_rejected() -> None:
    request = _request(rows=(_row("evidence_a1"),))

    def model_fn(messages: Sequence[Mapping[str, Any]]) -> str:
        return _payload(
            [_claim_payload("该版本已正式发布。", ref="c1")],
            [_link("c1", "evidence_a1"), _link("c1", "evidence_never_existed")],
        )

    snapshot = _snapshot_of(bind_answer_claims(request=request, model_fn=model_fn))
    assert snapshot.status == "rejected"
    assert snapshot.claims == ()
    assert snapshot.claim_links == ()


def test_strong_claim_without_evidence_is_never_marked_supported() -> None:
    request = _request(rows=(_row("evidence_a1"),))

    def model_fn(messages: Sequence[Mapping[str, Any]]) -> str:
        return _payload(
            [
                _claim_payload("该版本已正式发布。", ref="c1"),
                # A factual assertion the answer makes that no evidence row
                # supports: the producer must leave it unlinked, never invent
                # a direct_support link for it.
                _claim_payload("据说还包含未公开的功能。", ref="c2"),
            ],
            [_link("c1", "evidence_a1")],
        )

    snapshot = _snapshot_of(bind_answer_claims(request=request, model_fn=model_fn))
    assert snapshot.status == "validated"
    by_text = {claim.text: claim for claim in snapshot.claims}
    assert "据说还包含未公开的功能。" in by_text
    unsupported_claim = by_text["据说还包含未公开的功能。"]
    linked_claim_ids = {link.claim_id for link in snapshot.claim_links}
    assert unsupported_claim.id not in linked_claim_ids
    assert not any(
        link.claim_id == unsupported_claim.id and link.support_type == "direct_support"
        for link in snapshot.claim_links
    )


def test_malformed_structured_output_fails_closed() -> None:
    request = _request(rows=(_row(),))
    calls = {"count": 0}

    def broken(messages: Sequence[Mapping[str, Any]]) -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            return "not json at all"
        return json.dumps({"refused": "yes"})

    snapshot = _snapshot_of(
        bind_answer_claims(request=request, model_fn=broken, max_attempts=2)
    )
    assert snapshot.status == "rejected"
    assert snapshot.reason == "malformed_structured_output"
    assert calls["count"] == 2
    # Malformed output never reaches any learner-facing field.
    assert "not json" not in snapshot.reason
    assert snapshot.claims == ()


def test_provider_exception_fails_closed_without_leaking_raw_error() -> None:
    request = _request(rows=(_row(),))

    def exploding(messages: Sequence[Mapping[str, Any]]) -> str:
        raise RuntimeError("raw provider body with secret detail")

    snapshot = _snapshot_of(bind_answer_claims(request=request, model_fn=exploding))
    assert snapshot.status == "rejected"
    assert snapshot.reason == "producer_failed:RuntimeError"
    assert "secret detail" not in snapshot.reason
    assert "secret detail" not in snapshot.to_dict()["reason"]


def test_provider_failure_then_malformed_uses_last_error_reason() -> None:
    request = _request(rows=(_row(),))
    attempts = {"count": 0}

    def flaky(messages: Sequence[Mapping[str, Any]]) -> str:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise TimeoutError("timeout")
        return "[]"

    snapshot = _snapshot_of(
        bind_answer_claims(request=request, model_fn=flaky, max_attempts=2)
    )
    assert snapshot.status == "rejected"
    assert snapshot.reason == "malformed_structured_output"


def test_producer_refusal_is_rejected() -> None:
    request = _request(rows=(_row(),))

    def refusing(messages: Sequence[Mapping[str, Any]]) -> str:
        return _payload([], [], refused=True)

    snapshot = _snapshot_of(bind_answer_claims(request=request, model_fn=refusing))
    assert snapshot.status == "rejected"
    assert snapshot.reason == "producer_refused"


def test_final_answer_text_is_never_modified() -> None:
    request = _request(rows=(_row(),))
    original = request.final_answer

    def model_fn(messages: Sequence[Mapping[str, Any]]) -> str:
        return _payload([_claim_payload("该版本已正式发布。")], [_link("x", "evidence_a1")])

    bound = bind_answer_claims(request=request, model_fn=model_fn)
    assert request.final_answer == original
    # The snapshot hash binds the original canonical text.
    assert bound.snapshot.answer_hash == answer_content_hash(original)
    assert answer_content_hash(original + " 额外文字") != bound.snapshot.answer_hash


def test_empty_rows_yield_no_known_evidence_ids() -> None:
    request = _request(rows=())

    def model_fn(messages: Sequence[Mapping[str, Any]]) -> str:
        # With no evidence offered, even a link to a plausible id must fail.
        return _payload(
            [_claim_payload("该版本已正式发布。")],
            [_link("x", "evidence_abc123")],
        )

    snapshot = _snapshot_of(bind_answer_claims(request=request, model_fn=model_fn))
    assert snapshot.status == "rejected"


def test_duplicate_and_blank_evidence_rows_are_deduplicated() -> None:
    request = _request(
        rows=(_row("evidence_a1"), _row("evidence_a1"), _row("  ")),
    )

    seen_context: dict[str, str] = {}

    def model_fn(messages: Sequence[Mapping[str, Any]]) -> str:
        seen_context["user"] = "".join(
            str(message["content"]) for message in messages if message["role"] == "user"
        )
        return _payload([], [])

    snapshot = _snapshot_of(bind_answer_claims(request=request, model_fn=model_fn))
    # No claims -> still validated with zero claims (empty claim set is legal).
    assert snapshot.status == "validated"
    assert snapshot.claims == ()
    # Only one row rendered, not three.
    assert seen_context["user"].count("[evidence_a1]") == 1


def test_evidence_context_is_bounded() -> None:
    huge_spans = tuple(f"anchor text number {index} " + "x" * 2000 for index in range(50))
    request = _request(
        rows=(_row("evidence_a1", anchored_spans=huge_spans),),
    )

    seen: dict[str, str] = {}

    def model_fn(messages: Sequence[Mapping[str, Any]]) -> str:
        seen["user"] = "".join(
            str(message["content"]) for message in messages if message["role"] == "user"
        )
        return _payload([], [])

    bind_answer_claims(request=request, model_fn=model_fn)
    assert len(seen["user"]) < 16000
    assert "[evidence_a1]" in seen["user"]


def test_invalid_claim_fields_fail_closed() -> None:
    request = _request(rows=(_row(),))

    def model_fn(messages: Sequence[Mapping[str, Any]]) -> str:
        return _payload(
            [
                {
                    "id": "c1",
                    "text": "该版本已正式发布。",
                    "kind": "not_a_kind",
                    "status": "asserted",
                    "source": "provider_structured",
                }
            ],
            [],
        )

    snapshot = _snapshot_of(bind_answer_claims(request=request, model_fn=model_fn))
    assert snapshot.status == "rejected"


def test_binding_requires_final_answer() -> None:
    request = _request(answer="   ", rows=(_row(),))

    def model_fn(messages: Sequence[Mapping[str, Any]]) -> str:
        raise AssertionError("binder must reject empty answers before the call")

    with pytest.raises(ValueError):
        bind_answer_claims(request=request, model_fn=model_fn)


def test_link_to_undefined_claim_ref_is_rejected() -> None:
    request = _request(rows=(_row("evidence_a1"),))

    def model_fn(messages: Sequence[Mapping[str, Any]]) -> str:
        # The link references "ghost" which no claim declares.
        return _payload(
            [_claim_payload("该版本已正式发布。", ref="c1")],
            [_link("ghost", "evidence_a1")],
        )

    snapshot = _snapshot_of(bind_answer_claims(request=request, model_fn=model_fn))
    assert snapshot.status == "rejected"
    assert snapshot.claims == ()


def test_claim_ref_collision_is_rejected() -> None:
    request = _request(rows=(_row("evidence_a1"),))

    def model_fn(messages: Sequence[Mapping[str, Any]]) -> str:
        # Two claims reuse the same local ref: ref mapping becomes ambiguous,
        # so the link rewrite must not silently pick one.
        return _payload(
            [
                _claim_payload("该版本已正式发布。", ref="c1"),
                _claim_payload("修复了已知问题。", ref="c1"),
            ],
            [_link("c1", "evidence_a1")],
        )

    snapshot = _snapshot_of(bind_answer_claims(request=request, model_fn=model_fn))
    assert snapshot.status == "rejected"

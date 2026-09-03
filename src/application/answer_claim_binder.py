"""Production answer-claim binder (RQ1-C answer/citation binding batch).

The binder runs AFTER the final answer is generated and BEFORE the ChatTurn
completes.  It turns the already-produced answer into structured factual
claims bound to existing server-owned evidence ids.  It is deliberately NOT an
answer generator:

- it never rewrites the final answer text;
- it never invents evidence ids (unknown references fail closed);
- it never reads rubric or qualification expected answers;
- it runs only when the turn carries research evidence (wired in a later
  batch; this module stays a pure, injectable service).

Fail-closed contract: malformed structured output, provider failures and
unverifiable bindings yield a ``rejected`` / ``unavailable`` snapshot with a
canonical reason; a fabricated ``validated`` snapshot is impossible because the
domain layer rejects unknown evidence ids before a snapshot can be built.

Evidence context is bounded on purpose: each row renders only metadata and
short anchored-span excerpts (never the full page body), matching the frozen
external-data boundary of the research runtime.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence

from src.domain.answer_claims import (
    AnswerClaimSnapshotV1,
    answer_content_hash,
    build_answer_claim_snapshot,
    deterministic_claim_id,
    rejected_answer_claim_snapshot,
)

BINDER_SCHEMA_VERSION = "answer-claim-binder-v2"
ANSWER_CLAIM_BINDER_PRODUCER = "answer_claim_binder_v2"

# Bounded context budget: metadata rows plus short anchored excerpts only.
_MAX_EVIDENCE_ROWS = 24
_MAX_CONTEXT_CHARS = 16000
_MAX_ROW_CHARS = 1600
_MAX_ANCHOR_CHARS = 300
_MAX_CAVEAT_CHARS = 200
_MAX_ANCHORED_SPANS_PER_ROW = 6
_MAX_CAVEATS_PER_ROW = 6
_MAX_SEGMENTS = 16
_MAX_SEGMENT_CHARS = 1200

_ALLOWED_SEGMENT_KINDS = frozenset(
    {"factual", "instructional", "question", "recommendation", "uncertainty"}
)
_SEGMENT_BOUNDARY = re.compile(r"(?<=[。！？；!?;.])")

BinderModelFn = Callable[[Sequence[Mapping[str, Any]]], str]


@dataclass(frozen=True)
class AnswerClaimBindingRow:
    """One bounded evidence row offered to the binder.

    ``anchored_spans`` are short excerpts of the source text that the
    extractor already anchored to claims (locator-verified), not page bodies.
    """

    evidence_id: str
    title: str = ""
    url: str = ""
    source_role: str = ""
    source_cluster_id: str = ""
    relation: str = ""
    strength: str = ""
    locator: str = ""
    anchored_spans: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()


@dataclass(frozen=True)
class AnswerClaimBindingRequest:
    question: str
    final_answer: str
    evidence_rows: tuple[AnswerClaimBindingRow, ...] = ()


@dataclass(frozen=True)
class BoundAnswerClaims:
    snapshot: AnswerClaimSnapshotV1
    raw_output: str = ""
    attempt_count: int = 0


def bind_answer_claims(
    *,
    request: AnswerClaimBindingRequest,
    model_fn: BinderModelFn,
    producer: str = ANSWER_CLAIM_BINDER_PRODUCER,
    max_attempts: int = 1,
) -> BoundAnswerClaims:
    """Bind one final answer to existing evidence ids, failing closed.

    The final answer text is never modified; the returned snapshot carries the
    canonical answer hash of the original text.  Any malformed or unverifiable
    producer output resolves to a ``rejected`` snapshot instead of raising.

    ``max_attempts`` is the server-authorized physical model-call ceiling for
    this binding (bounded by the binder retry capability).  Defaults to one
    attempt; a caller holding an authoritative remaining budget may allow the
    second retry.  The physical attempt count is always reported back on the
    result so callers can record authoritative model-call accounting.
    """
    answer = _clean_text(request.final_answer)
    if not answer:
        raise ValueError("answer claim binding requires a final answer")
    segments = _segment_answer(answer)
    if not segments:
        # Overlong answers fail closed: partial coverage would let
        # unsupported factual statements vanish.
        return BoundAnswerClaims(
            snapshot=rejected_answer_claim_snapshot(
                answer=answer,
                producer=producer,
                reason="answer_not_segmentable",
            ),
            attempt_count=0,
        )
    rows = tuple(_bounded_rows(request.evidence_rows))
    known_evidence_ids = tuple(row.evidence_id for row in rows)
    messages = _binding_messages(
        question=request.question, answer=answer, segments=segments, rows=rows
    )

    attempts = max(0, min(int(max_attempts), 2))
    last_error = ""
    for attempt in range(1, attempts + 1):
        try:
            raw = model_fn(messages)
        except Exception as exc:  # noqa: BLE001 - provider failures are results
            last_error = f"producer_failed:{type(exc).__name__}"
            continue
        parsed, parse_error = _parse_binder_output(
            raw_output=raw,
            answer=answer,
            segments=segments,
            known_evidence_ids=known_evidence_ids,
            producer=producer,
        )
        if parsed is not None:
            return BoundAnswerClaims(
                snapshot=parsed, raw_output=raw, attempt_count=attempt
            )
        last_error = parse_error or "malformed_structured_output"
    return BoundAnswerClaims(
        snapshot=rejected_answer_claim_snapshot(
            answer=answer,
            producer=producer,
            reason=last_error or "producer_unavailable",
        ),
        attempt_count=attempts,
    )


def _parse_binder_output(
    *,
    raw_output: str,
    answer: str,
    segments: tuple[str, ...],
    known_evidence_ids: tuple[str, ...],
    producer: str,
) -> tuple[AnswerClaimSnapshotV1 | None, str]:
    """Parse the segment protocol v2 output.

    Returns ``(snapshot, "")`` on success, ``(None, reason_token)`` when the
    output is structurally unusable so the attempt loop may retry, and
    ``(rejected_snapshot, "")`` for determinate refusals that must not burn
    further retries (``refused=true``).
    """
    if not raw_output or not raw_output.strip():
        return None, "empty_producer_output"
    try:
        payload = json.loads(_strip_json_fence(raw_output))
    except (TypeError, ValueError):
        return None, "malformed_structured_output"
    if not isinstance(payload, Mapping):
        return None, "malformed_structured_output"
    refused = payload.get("refused")
    if not isinstance(refused, bool):
        return None, "malformed_structured_output"
    if refused:
        return (
            rejected_answer_claim_snapshot(
                answer=answer,
                producer=producer,
                reason="producer_refused",
            ),
            "",
        )
    raw_segments = payload.get("segments")
    if not isinstance(raw_segments, list):
        return None, "malformed_structured_output"
    segment_entries = tuple(_object(entry) for entry in raw_segments)
    if len(segment_entries) != len(segments):
        return None, "segment_coverage_mismatch"
    ref_to_text: dict[str, str] = {
        _segment_ref(index): text for index, text in enumerate(segments)
    }
    claims: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    seen_refs: set[str] = set()
    for entry in segment_entries:
        ref = _clean_identifier(entry.get("segment_ref"))
        if not ref or ref not in ref_to_text:
            return None, "segment_coverage_mismatch"
        if ref in seen_refs:
            return None, "segment_coverage_mismatch"
        seen_refs.add(ref)
        kind = str(entry.get("kind") or "").strip()
        status = str(entry.get("status") or "").strip()
        raw_support = entry.get("evidence_support")
        if kind not in _ALLOWED_SEGMENT_KINDS:
            return None, "malformed_structured_output"
        if kind == "factual":
            if status not in {"asserted", "qualified"}:
                return None, "malformed_structured_output"
        else:
            if status:
                return None, "malformed_structured_output"
        if not isinstance(raw_support, list) or not all(
            isinstance(item, str) for item in raw_support
        ):
            return None, "malformed_structured_output"
        support_ids = tuple(
            _clean_identifier(item) for item in raw_support
        )
        if kind != "factual":
            if support_ids:
                return None, "non_factual_segment_support"
            continue
        if not support_ids:
            # A factual statement the model cannot bind to eligible evidence
            # must never vanish: the whole binding is rejected.
            return None, "unbound_factual_segment"
        unknown = [item for item in support_ids if item not in known_evidence_ids]
        if unknown:
            return None, "unknown_evidence_id"
        claim_id = deterministic_claim_id(
            answer_hash=answer_content_hash(answer), claim_text=ref_to_text[ref]
        )
        claims.append(
            {
                "text": ref_to_text[ref],
                "kind": "factual",
                "status": status,
                "source": "provider_structured",
            }
        )
        for evidence_id in support_ids:
            links.append(
                {
                    "claim_id": claim_id,
                    "evidence_id": evidence_id,
                    "support_type": "direct_support",
                    "confidence": 1.0,
                }
            )
    try:
        return (
            build_answer_claim_snapshot(
                answer=answer,
                claims=claims,
                claim_links=links,
                known_evidence_ids=known_evidence_ids,
                producer=producer,
                status="validated",
                trust_upstream_claim_ids=False,
            ),
            "",
        )
    except (TypeError, ValueError):
        return None, "malformed_structured_output"


def _segment_ref(index: int) -> str:
    return f"s{index + 1}"


def _segment_answer(answer: str) -> tuple[str, ...]:
    """Deterministic server-side segmentation of the immutable answer.

    The model never invents claim identity: it receives the exact segment refs
    (s1, s2, ...) and must classify every one of them.  Overlong single
    segments fail closed (too long to be classified safely) and answers with
    more than ``_MAX_SEGMENTS`` segments are refused, because partial coverage
    would otherwise let unsupported factual statements vanish.
    """
    raw_parts = _SEGMENT_BOUNDARY.split(answer)
    segments: list[str] = []
    for part in raw_parts:
        candidate = part.strip(" \t\n\r")
        if not candidate:
            continue
        if len(candidate) > _MAX_SEGMENT_CHARS:
            return ()
        if len(segments) >= _MAX_SEGMENTS:
            return ()
        segments.append(candidate)
    return tuple(segments)


def factual_claims_fully_bound(snapshot: AnswerClaimSnapshotV1) -> bool:
    """True when every factual claim (asserted or qualified) has support.

    A link whose ``support_type`` is ``contradicts`` never satisfies support;
    only positive support types count.  Uncertainty-classified statements are
    not factual claims and need no evidence.
    """
    bound_claim_ids = {
        link.claim_id
        for link in snapshot.claim_links
        if link.claim_id and link.support_type in _POSITIVE_SUPPORT_TYPES
    }
    return all(
        claim.kind != "factual" or claim.id in bound_claim_ids
        for claim in snapshot.claims
    )


_POSITIVE_SUPPORT_TYPES = frozenset({"direct_support", "indirect_support"})


def _binding_messages(
    *,
    question: str,
    answer: str,
    segments: tuple[str, ...],
    rows: tuple[AnswerClaimBindingRow, ...],
) -> list[dict[str, str]]:
    context = _render_context(rows)
    numbered = "\n".join(
        f"[{_segment_ref(index)}] {segment}" for index, segment in enumerate(segments)
    )
    system = (
        "You classify every sentence of an already-written final answer "
        "against a fixed list of server-owned evidence items.\n"
        "Rules:\n"
        "1. Never modify, restate-instead-of-quoting or add to the answer. "
        "The server already split it into segments; you classify those exact "
        "segments only.\n"
        "2. segments: return EXACTLY one entry per segment ref shown in the "
        "user message. Missing, duplicate or unknown refs are rejected.\n"
        "3. kind: factual/instructional/question/recommendation/uncertainty. "
        "Use uncertainty for genuinely unverifiable or speculative wording; "
        "a qualified factual statement (weakened with hedging) is still "
        "factual and still needs evidence support.\n"
        "4. factual segments: status asserted or qualified, and "
        "evidence_support MUST list at least one evidence_id that directly "
        "states the claim. Never bind contradicts-style disagreement as "
        "support and never put evidence on non-factual segments.\n"
        "5. non-factual segments: omit status and keep evidence_support empty.\n"
        "6. If you cannot produce a safe binding for the whole answer, set "
        "refused=true with an empty segments list.\n"
        'Respond with JSON only: {"refused": bool, "segments": '
        '[{"segment_ref": "s1", "kind": "...", "status": "asserted|qualified", '
        '"evidence_support": ["evidence_id"]}]}.'
    )
    user = (
        "Question:\n{question}\n\n"
        "Final answer segments (read-only input to classify):\n{numbered}\n\n"
        "Available evidence (bounded metadata; use the evidence_id values "
        "verbatim):\n{context}"
    ).format(
        question=_clean_text(question)[:_MAX_CONTEXT_CHARS],
        numbered=numbered[:_MAX_CONTEXT_CHARS],
        context=context or "(none)",
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _render_context(rows: tuple[AnswerClaimBindingRow, ...]) -> str:
    rendered: list[str] = []
    budget = _MAX_CONTEXT_CHARS
    for row in rows:
        line = _render_row(row)
        if budget - len(line) < 0:
            break
        budget -= len(line)
        rendered.append(line)
    return "\n".join(rendered)


def _render_row(row: AnswerClaimBindingRow) -> str:
    spans = " | ".join(
        _clip(span, _MAX_ANCHOR_CHARS)
        for span in row.anchored_spans[:_MAX_ANCHORED_SPANS_PER_ROW]
    )
    caveats = " | ".join(
        _clip(caveat, _MAX_CAVEAT_CHARS)
        for caveat in row.caveats[:_MAX_CAVEATS_PER_ROW]
    )
    parts = [
        f"[{row.evidence_id}]",
        _clip(row.title, 200),
        _clip(row.url, 500),
        _clip(row.source_role, 100),
        _clip(row.source_cluster_id, 100),
        _clip(row.relation, 100),
        _clip(row.strength, 100),
        _clip(row.locator, 300),
    ]
    if spans:
        parts.append(f"anchors: {spans}")
    if caveats:
        parts.append(f"caveats: {caveats}")
    line = " | ".join(part for part in parts if part)
    return line[:_MAX_ROW_CHARS]


def _bounded_rows(
    rows: Iterable[AnswerClaimBindingRow],
) -> Iterable[AnswerClaimBindingRow]:
    seen: set[str] = set()
    count = 0
    for row in rows:
        evidence_id = _clean_text(row.evidence_id)
        if not evidence_id or evidence_id in seen:
            continue
        seen.add(evidence_id)
        count += 1
        if count > _MAX_EVIDENCE_ROWS:
            return
        yield AnswerClaimBindingRow(
            evidence_id=evidence_id,
            title=_clean_text(row.title),
            url=_clean_text(row.url),
            source_role=_clean_text(row.source_role),
            source_cluster_id=_clean_text(row.source_cluster_id),
            relation=_clean_text(row.relation),
            strength=_clean_text(row.strength),
            locator=_clean_text(row.locator),
            anchored_spans=tuple(
                _clip(span, _MAX_ANCHOR_CHARS)
                for span in row.anchored_spans
            )[: _MAX_ANCHORED_SPANS_PER_ROW],
            caveats=tuple(
                _clip(caveat, _MAX_CAVEAT_CHARS) for caveat in row.caveats
            )[: _MAX_CAVEATS_PER_ROW],
        )


def _clip(value: str, limit: int) -> str:
    return _clean_text(value)[:limit]


def _clean_identifier(value: Any) -> str:
    identifier = str(value or "").strip()
    if not identifier:
        return ""
    if len(identifier) > 160 or any(character.isspace() for character in identifier):
        return ""
    return identifier


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _strip_json_fence(value: str) -> str:
    text = str(value).strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def _object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "ANSWER_CLAIM_BINDER_PRODUCER",
    "AnswerClaimBindingRequest",
    "AnswerClaimBindingRow",
    "BINDER_SCHEMA_VERSION",
    "BoundAnswerClaims",
    "bind_answer_claims",
]

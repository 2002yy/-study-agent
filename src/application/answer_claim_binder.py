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
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence

from src.domain.answer_claims import (
    AnswerClaimSnapshotV1,
    build_answer_claim_snapshot,
    rejected_answer_claim_snapshot,
)

BINDER_SCHEMA_VERSION = "answer-claim-binder-v1"
ANSWER_CLAIM_BINDER_PRODUCER = "answer_claim_binder_v1"

# Bounded context budget: metadata rows plus short anchored excerpts only.
_MAX_EVIDENCE_ROWS = 24
_MAX_CONTEXT_CHARS = 16000
_MAX_ROW_CHARS = 1600
_MAX_ANCHOR_CHARS = 300
_MAX_CAVEAT_CHARS = 200
_MAX_ANCHORED_SPANS_PER_ROW = 6
_MAX_CAVEATS_PER_ROW = 6

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
    rows = tuple(_bounded_rows(request.evidence_rows))
    known_evidence_ids = tuple(row.evidence_id for row in rows)
    messages = _binding_messages(question=request.question, answer=answer, rows=rows)

    attempts = max(0, min(int(max_attempts), 2))
    last_error = ""
    for attempt in range(1, attempts + 1):
        try:
            raw = model_fn(messages)
        except Exception as exc:  # noqa: BLE001 - provider failures are results
            last_error = f"producer_failed:{type(exc).__name__}"
            continue
        parsed = _parse_binder_output(
            raw_output=raw,
            answer=answer,
            known_evidence_ids=known_evidence_ids,
            producer=producer,
        )
        if parsed is not None:
            return BoundAnswerClaims(
                snapshot=parsed, raw_output=raw, attempt_count=attempt
            )
        last_error = "malformed_structured_output"
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
    known_evidence_ids: tuple[str, ...],
    producer: str,
) -> AnswerClaimSnapshotV1 | None:
    if not raw_output or not raw_output.strip():
        return None
    try:
        payload = json.loads(_strip_json_fence(raw_output))
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, Mapping):
        return None
    refused = payload.get("refused")
    if not isinstance(refused, bool):
        return None
    if refused:
        return rejected_answer_claim_snapshot(
            answer=answer,
            producer=producer,
            reason="producer_refused",
        )
    raw_claims = payload.get("claims")
    raw_links = payload.get("claim_links")
    if not isinstance(raw_claims, list) or not isinstance(raw_links, list):
        return None
    claim_dicts = tuple(_object(claim) for claim in raw_claims)
    link_dicts = tuple(_object(link) for link in raw_links)
    try:
        # Stage 1: build deterministic claims without links.  Upstream claim
        # ids are local refs only (the model cannot know server ids); any id
        # that does not match the deterministic identity is ignored for the
        # rewrite map and rejected later if a link still references it.
        staged_claims = [
            {key: value for key, value in claim.items() if key != "id"}
            for claim in claim_dicts
        ]
        staged = build_answer_claim_snapshot(
            answer=answer,
            claims=staged_claims,
            known_evidence_ids=known_evidence_ids,
            producer=producer,
            status="validated",
            trust_upstream_claim_ids=False,
        )
        ref_to_claim_id: dict[str, str] = {}
        for raw_claim, claim in zip(claim_dicts, staged.claims):
            ref = _clean_identifier(raw_claim.get("id"))
            if ref:
                if ref in ref_to_claim_id:
                    # Ambiguous local ref: the rewrite would silently pick one
                    # claim, so the whole payload fails closed.
                    return None
                ref_to_claim_id[ref] = claim.id
        # Stage 2: rewrite claim_links local refs to deterministic ids and
        # run the full validation (unknown evidence ids fail closed here).
        rewritten_links = []
        for raw_link in link_dicts:
            link = dict(raw_link)
            claim_ref = link.get("claim_id")
            if claim_ref in ref_to_claim_id:
                link["claim_id"] = ref_to_claim_id[claim_ref]
            rewritten_links.append(link)
        return build_answer_claim_snapshot(
            answer=answer,
            claims=staged_claims,
            claim_links=rewritten_links,
            known_evidence_ids=known_evidence_ids,
            producer=producer,
            status="validated",
            trust_upstream_claim_ids=False,
        )
    except (TypeError, ValueError):
        return None


def factual_claims_fully_bound(snapshot: AnswerClaimSnapshotV1) -> bool:
    """True when every asserted factual claim carries at least one link.

    The binder itself reports honest unbound claims (never invents a link);
    the publication gate uses this to refuse publishing a final answer that
    still contains an unsupported strong factual assertion.
    """
    bound_claim_ids = {
        link.claim_id for link in snapshot.claim_links if link.claim_id
    }
    return all(
        claim.kind != "factual" or claim.status != "asserted" or claim.id in bound_claim_ids
        for claim in snapshot.claims
    )


def _binding_messages(*, question: str, answer: str, rows: tuple[AnswerClaimBindingRow, ...]) -> list[dict[str, str]]:
    context = _render_context(rows)
    system = (
        "You bind factual assertions of an already-written answer to a fixed "
        "list of server-owned evidence items.\n"
        "Rules:\n"
        "1. Never modify, restate-instead-of-quoting or add to the answer. You "
        "only classify its existing statements.\n"
        "2. claims: text must be a statement actually present in the answer "
        "(short paraphrase allowed), kind one of factual/instructional/"
        "question/recommendation/uncertainty, status asserted/qualified/"
        "withdrawn. Give each claim a local id ref such as \"c1\", \"c2\" - "
        "the server replaces refs with deterministic ids.\n"
        "3. claim_links: reference ONLY evidence ids from the provided list "
        "and reference claims by their local id ref. Never invent or guess an "
        "evidence id.\n"
        "4. support_type: direct_support only when the evidence excerpt "
        "directly states the claim; indirect_support for partial context; "
        "contradicts when evidence conflicts.\n"
        "5. A factual assertion that none of the evidence supports must stay "
        "without a link - it is never marked supported.\n"
        "6. If you cannot produce a safe binding for the whole answer, set "
        "refused=true with empty claims and claim_links.\n"
        'Respond with JSON only: {"refused": bool, "claims": [...], '
        '"claim_links": [...]}.'
    )
    user = (
        "Question:\n{question}\n\n"
        "Final answer (read-only input to classify):\n{answer}\n\n"
        "Available evidence (bounded metadata; use the evidence_id values "
        "verbatim):\n{context}"
    ).format(
        question=_clean_text(question)[:_MAX_CONTEXT_CHARS],
        answer=answer[:_MAX_CONTEXT_CHARS],
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

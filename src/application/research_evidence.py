"""Privacy-bounded projection of durable ResearchRun source assessments."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

_ITEM_FIELDS = (
    "title",
    "url",
    "link",
    "href",
    "published_at",
    "published",
    "date",
    "pubDate",
)
_ASSESSMENT_FIELDS = (
    "source_id",
    "title",
    "url",
    "domain",
    "source_type",
    "relevance",
    "directness",
    "freshness",
    "selected",
    "rejection_reason",
    "duplicate_of",
    "worth_reading",
    "selection_reason",
)
_READ_SUMMARY_FIELDS = (
    "attempted",
    "successful",
    "failed",
    "skipped",
    "used_chars",
)


def research_sources_snapshot(run: Any) -> dict[str, Any]:
    """Return only source identity/assessment fields needed by EvidenceSnapshot.

    Full snippets, extracted article content, query attempts, tokens, credentials
    and arbitrary provider payloads are intentionally excluded from ChatTurn truth.
    """

    context = getattr(run, "research_context", None)
    context = context if isinstance(context, dict) else {}
    read_summary = context.get("read_summary")
    read_summary = read_summary if isinstance(read_summary, dict) else {}
    return {
        "run_id": str(getattr(run, "id", "") or ""),
        "provider_status": str(getattr(run, "provider_status", "") or ""),
        "stop_reason": str(getattr(run, "stop_reason", "") or ""),
        "source_truth_version": _nonnegative_int(context.get("source_truth_version")),
        "read_summary": {
            key: read_summary[key]
            for key in _READ_SUMMARY_FIELDS
            if key in read_summary and _is_scalar(read_summary[key])
        },
        "selected_sources": _safe_records(
            getattr(run, "selected_sources", ()) or ()
        ),
        "rejected_sources": _safe_records(
            getattr(run, "rejected_sources", ()) or ()
        ),
    }


def _safe_records(records: Iterable[Any]) -> list[dict[str, Any]]:
    return [
        safe
        for record in records
        if (safe := _safe_record(record)) is not None
    ]


def _safe_record(record: Any) -> dict[str, Any] | None:
    if not isinstance(record, dict):
        return None
    item = _object(record.get("item"))
    assessment = _object(record.get("assessment"))
    safe_item = {
        key: item[key]
        for key in _ITEM_FIELDS
        if key in item and _is_scalar(item[key])
    }
    safe_assessment = {
        key: assessment[key]
        for key in _ASSESSMENT_FIELDS
        if key in assessment and _is_scalar(assessment[key])
    }
    if not safe_item and not safe_assessment:
        return None
    safe: dict[str, Any] = {"item": safe_item, "assessment": safe_assessment}
    read = _object(record.get("read"))
    read_status = str(record.get("read_status") or read.get("status") or "").strip()
    if read_status in {"read", "failed", "skipped", "structured"}:
        safe["read_status"] = read_status
    evidence_state = record.get("evidence_state")
    if isinstance(evidence_state, str) and evidence_state in {
        "inherited_candidate",
        "revalidated",
        "new",
        "invalid_or_rejected",
    }:
        safe["evidence_state"] = evidence_state
    return safe


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _nonnegative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


# Server-owned bounded rows for answer-claim binding (RQ1-C answer batch).
# Only these whitelisted fields may leave the durable research_context toward
# the binder model call; page bodies and arbitrary provider payloads never do.
_BINDING_ROW_FIELDS = (
    "evidence_id",
    "claim_id",
    "relation",
    "strength",
    "source_role",
    "source_cluster_id",
    "title",
    "url",
    "locator",
    "published_at",
)
_BINDING_SEQUENCE_FIELDS = ("anchored_spans", "caveats")
_MAX_BINDING_ROWS = 24
_MAX_BINDING_SEQUENCE_ITEMS = 6
_MAX_BINDING_ITEM_CHARS = 300
_BINDING_CONTEXT_KEY = "claim_engine_evidence_brief"
_BINDING_EVIDENCE_KEY = "eligible_evidence"
# Any of these durable research-runtime traces marks the run as a
# claim-engine ResearchRun (provenance == research_run) even when the current
# Evidence Brief carries zero eligible rows (old runs, gated-out runs).  Plain
# search/tool-loop runs never contain them.
_RESEARCH_PROVENANCE_KEYS = (
    "claim_engine_evidence_brief",
    "claim_engine_runtime",
    "claim_engine_metrics",
    "claim_engine_assessments",
    "claim_engine_evidence",
    "deep",
)


def research_run_provenance(run: Any) -> bool:
    """True when the server-side run object is a claim-engine ResearchRun.

    This is the only provenance gate for answer-validation plans: the caller
    must already hold a real run resolved from the repository; a matching
    context key on that object is required so look-alike fields can never be
    mistaken for a ResearchRun.
    """
    context = getattr(run, "research_context", None)
    if not isinstance(context, dict):
        return False
    return any(key in context for key in _RESEARCH_PROVENANCE_KEYS)


def research_binding_rows(run: Any) -> list[dict[str, Any]]:
    """Project bounded evidence rows from the server-owned Evidence Brief.

    The rows feed the answer-claim binder only.  ``run`` must be a server
    object loaded from the repository; client-supplied content is never an
    input here.  Missing or malformed briefs yield an empty list so callers
    fail safe instead of treating old runs as validated.
    """
    context = getattr(run, "research_context", None)
    context = context if isinstance(context, dict) else {}
    brief = context.get(_BINDING_CONTEXT_KEY)
    if not isinstance(brief, Mapping):
        return []
    eligible = brief.get(_BINDING_EVIDENCE_KEY)
    if not isinstance(eligible, list):
        return []
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_row in eligible:
        if not isinstance(raw_row, Mapping):
            continue
        evidence_id = _scalar_text(raw_row.get("evidence_id"))
        if not evidence_id or evidence_id in seen:
            continue
        seen.add(evidence_id)
        rows.append(
            {
                field: _scalar_text(raw_row.get(field))
                for field in _BINDING_ROW_FIELDS
            }
            | {
                field: tuple(
                    text
                    for item in _sequence(raw_row.get(field))[
                        : _MAX_BINDING_SEQUENCE_ITEMS
                    ]
                    if (text := _scalar_text(item)[:_MAX_BINDING_ITEM_CHARS])
                )
                for field in _BINDING_SEQUENCE_FIELDS
            }
        )
        if len(rows) >= _MAX_BINDING_ROWS:
            break
    return rows


def _sequence(value: Any) -> tuple[Any, ...]:
    return tuple(value) if isinstance(value, (list, tuple)) else ()


def _scalar_text(value: Any) -> str:
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, (int, float, bool)):
        return str(value)
    return ""

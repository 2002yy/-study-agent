"""Privacy-bounded projection of durable ResearchRun source assessments."""

from __future__ import annotations

from typing import Any, Iterable

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

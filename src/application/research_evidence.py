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
)


def research_sources_snapshot(run: Any) -> dict[str, Any]:
    """Return only source identity/assessment fields needed by EvidenceSnapshot.

    Full snippets, extracted article content, query attempts, tokens, credentials
    and arbitrary provider payloads are intentionally excluded from ChatTurn truth.
    """

    return {
        "run_id": str(getattr(run, "id", "") or ""),
        "provider_status": str(getattr(run, "provider_status", "") or ""),
        "stop_reason": str(getattr(run, "stop_reason", "") or ""),
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
    return {"item": safe_item, "assessment": safe_assessment}


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))

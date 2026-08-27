"""Bounded operational cursor for Claim Engine runtime execution.

``ResearchState`` remains the semantic durable truth.  This module stores only
resume/audit cursor data needed to continue one active run after a checkpoint;
it owns no database writes and contains no page bodies, prompts, or raw model
responses.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Literal, Mapping

from src.web.research.model_gateway import (
    ResearchModelAttemptStart,
    ResearchModelCallAudit,
)

CLAIM_ENGINE_RUNTIME_CONTEXT_KEY = "claim_engine_runtime"
RESEARCH_RUNTIME_SCHEMA_VERSION = "research-runtime-v1"

RuntimeLoadStatus = Literal["absent", "available", "unavailable"]
RuntimePhase = Literal[
    "bootstrap",
    "planning",
    "searching",
    "assessing",
    "ranking",
    "reading",
    "extracting",
    "gating",
    "synthesizing",
    "completed",
    "unavailable",
]

_PHASES = {
    "bootstrap",
    "planning",
    "searching",
    "assessing",
    "ranking",
    "reading",
    "extracting",
    "gating",
    "synthesizing",
    "completed",
    "unavailable",
}
_QUERY_STATUSES = {"ok", "empty", "unavailable"}
_READ_STATUSES = {"success", "failed", "skipped"}
_MAX_CURSOR_ITEMS = 100


@dataclass(frozen=True)
class RuntimePlannedQuery:
    id: str
    gap_id: str
    claim_id: str
    intent: str
    query: str
    desired_source_role: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "gap_id": self.gap_id,
            "claim_id": self.claim_id,
            "intent": self.intent,
            "query": self.query,
            "desired_source_role": self.desired_source_role,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "RuntimePlannedQuery":
        data = _strict_mapping(
            raw,
            {"id", "gap_id", "claim_id", "intent", "query", "desired_source_role"},
            "runtime planned query",
        )
        return cls(
            id=_required_text(data.get("id"), 300, "query id"),
            gap_id=_required_text(data.get("gap_id"), 300, "gap id"),
            claim_id=_required_text(data.get("claim_id"), 300, "claim id"),
            intent=_required_text(data.get("intent"), 100, "query intent"),
            query=_required_text(data.get("query"), 1000, "query"),
            desired_source_role=_optional_text(data.get("desired_source_role"), 100),
        )


@dataclass(frozen=True)
class RuntimeQueryOutcome:
    query_id: str
    status: str
    result_count: int
    providers: tuple[str, ...] = ()
    error_code: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "status": self.status,
            "result_count": self.result_count,
            "providers": list(self.providers),
            "error_code": self.error_code,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "RuntimeQueryOutcome":
        data = _strict_mapping(
            raw,
            {"query_id", "status", "result_count", "providers", "error_code"},
            "runtime query outcome",
        )
        status = _required_text(data.get("status"), 50, "query status")
        if status not in _QUERY_STATUSES:
            raise ValueError("invalid runtime query status")
        return cls(
            query_id=_required_text(data.get("query_id"), 300, "query id"),
            status=status,
            result_count=_bounded_int(data.get("result_count"), 0, 10000, "result_count"),
            providers=_text_tuple(data.get("providers"), 20, 100),
            error_code=_optional_text(data.get("error_code"), 200),
        )


@dataclass(frozen=True)
class RuntimeCandidate:
    id: str
    url: str
    title: str
    snippet: str = ""
    source: str = ""
    published_at: str = ""
    query_ids: tuple[str, ...] = ()
    intents: tuple[str, ...] = ()
    providers: tuple[str, ...] = ()
    first_seen_rank: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "source": self.source,
            "published_at": self.published_at,
            "query_ids": list(self.query_ids),
            "intents": list(self.intents),
            "providers": list(self.providers),
            "first_seen_rank": self.first_seen_rank,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "RuntimeCandidate":
        data = _strict_mapping(
            raw,
            {
                "id",
                "url",
                "title",
                "snippet",
                "source",
                "published_at",
                "query_ids",
                "intents",
                "providers",
                "first_seen_rank",
            },
            "runtime candidate",
        )
        return cls(
            id=_required_text(data.get("id"), 300, "candidate id"),
            url=_required_text(data.get("url"), 2000, "candidate url"),
            title=_required_text(data.get("title"), 500, "candidate title"),
            snippet=_optional_text(data.get("snippet"), 2000),
            source=_optional_text(data.get("source"), 200),
            published_at=_optional_text(data.get("published_at"), 100),
            query_ids=_text_tuple(data.get("query_ids"), 20, 300),
            intents=_text_tuple(data.get("intents"), 20, 100),
            providers=_text_tuple(data.get("providers"), 20, 100),
            first_seen_rank=_bounded_int(
                data.get("first_seen_rank"), 0, 10000, "first_seen_rank"
            ),
        )


@dataclass(frozen=True)
class RuntimeReadOutcome:
    candidate_id: str
    status: str
    evidence_id: str = ""
    content_chars: int = 0
    error_code: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "status": self.status,
            "evidence_id": self.evidence_id,
            "content_chars": self.content_chars,
            "error_code": self.error_code,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "RuntimeReadOutcome":
        data = _strict_mapping(
            raw,
            {"candidate_id", "status", "evidence_id", "content_chars", "error_code"},
            "runtime read outcome",
        )
        status = _required_text(data.get("status"), 50, "read status")
        if status not in _READ_STATUSES:
            raise ValueError("invalid runtime read status")
        return cls(
            candidate_id=_required_text(
                data.get("candidate_id"), 300, "candidate id"
            ),
            status=status,
            evidence_id=_optional_text(data.get("evidence_id"), 300),
            content_chars=_bounded_int(
                data.get("content_chars"), 0, 10_000_000, "content_chars"
            ),
            error_code=_optional_text(data.get("error_code"), 200),
        )


@dataclass(frozen=True)
class RuntimeFailure:
    code: str
    phase: str
    item_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "phase": self.phase, "item_id": self.item_id}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "RuntimeFailure":
        data = _strict_mapping(raw, {"code", "phase", "item_id"}, "runtime failure")
        phase = _required_text(data.get("phase"), 50, "failure phase")
        if phase not in _PHASES:
            raise ValueError("invalid runtime failure phase")
        return cls(
            code=_required_text(data.get("code"), 200, "failure code"),
            phase=phase,
            item_id=_optional_text(data.get("item_id"), 300),
        )


@dataclass(frozen=True)
class ResearchRuntimeCursor:
    round_index: int = 0
    phase: RuntimePhase = "bootstrap"
    planned_queries: tuple[RuntimePlannedQuery, ...] = ()
    query_outcomes: tuple[RuntimeQueryOutcome, ...] = ()
    candidates: tuple[RuntimeCandidate, ...] = ()
    planned_read_ids: tuple[str, ...] = ()
    read_outcomes: tuple[RuntimeReadOutcome, ...] = ()
    model_calls: tuple[ResearchModelCallAudit, ...] = ()
    inflight_model_call: ResearchModelAttemptStart | None = None
    failures: tuple[RuntimeFailure, ...] = ()
    schema_version: str = RESEARCH_RUNTIME_SCHEMA_VERSION

    @property
    def completed_query_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.query_id for item in self.query_outcomes))

    @property
    def completed_read_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.candidate_id for item in self.read_outcomes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "round_index": self.round_index,
            "phase": self.phase,
            "planned_queries": [item.to_dict() for item in self.planned_queries],
            "query_outcomes": [item.to_dict() for item in self.query_outcomes],
            "candidates": [item.to_dict() for item in self.candidates],
            "planned_read_ids": list(self.planned_read_ids),
            "read_outcomes": [item.to_dict() for item in self.read_outcomes],
            "model_calls": [item.to_dict() for item in self.model_calls],
            "inflight_model_call": (
                self.inflight_model_call.to_dict() if self.inflight_model_call else None
            ),
            "failures": [item.to_dict() for item in self.failures],
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ResearchRuntimeCursor":
        data = _strict_mapping(
            raw,
            {
                "schema_version",
                "round_index",
                "phase",
                "planned_queries",
                "query_outcomes",
                "candidates",
                "planned_read_ids",
                "read_outcomes",
                "model_calls",
                "inflight_model_call",
                "failures",
            },
            "research runtime cursor",
        )
        if data.get("schema_version") != RESEARCH_RUNTIME_SCHEMA_VERSION:
            raise ValueError("unsupported research runtime schema")
        phase = _required_text(data.get("phase"), 50, "runtime phase")
        if phase not in _PHASES:
            raise ValueError("invalid research runtime phase")
        planned_queries = _object_tuple(
            data.get("planned_queries"), RuntimePlannedQuery.from_dict, "planned_queries"
        )
        query_outcomes = _object_tuple(
            data.get("query_outcomes"), RuntimeQueryOutcome.from_dict, "query_outcomes"
        )
        candidates = _object_tuple(
            data.get("candidates"), RuntimeCandidate.from_dict, "candidates"
        )
        read_outcomes = _object_tuple(
            data.get("read_outcomes"), RuntimeReadOutcome.from_dict, "read_outcomes"
        )
        model_calls = _object_tuple(
            data.get("model_calls"), ResearchModelCallAudit.from_dict, "model_calls"
        )
        failures = _object_tuple(
            data.get("failures"), RuntimeFailure.from_dict, "failures"
        )
        inflight_raw = data.get("inflight_model_call")
        inflight = (
            None
            if inflight_raw is None
            else ResearchModelAttemptStart.from_dict(
                _as_mapping(inflight_raw, "inflight_model_call")
            )
        )
        cursor = cls(
            round_index=_bounded_int(data.get("round_index"), 0, 1000, "round_index"),
            phase=phase,  # type: ignore[arg-type]
            planned_queries=planned_queries,
            query_outcomes=query_outcomes,
            candidates=candidates,
            planned_read_ids=_text_tuple(
                data.get("planned_read_ids"), _MAX_CURSOR_ITEMS, 300
            ),
            read_outcomes=read_outcomes,
            model_calls=model_calls,
            inflight_model_call=inflight,
            failures=failures,
        )
        _validate_cursor_links(cursor)
        return cursor


@dataclass(frozen=True)
class RuntimeCursorLoadResult:
    status: RuntimeLoadStatus
    cursor: ResearchRuntimeCursor | None = None
    reason: str = ""

    @property
    def available(self) -> bool:
        return self.status == "available" and self.cursor is not None


def attach_runtime_cursor(
    research_context: Mapping[str, Any], cursor: ResearchRuntimeCursor
) -> dict[str, Any]:
    validated = ResearchRuntimeCursor.from_dict(cursor.to_dict())
    updated = dict(research_context)
    updated[CLAIM_ENGINE_RUNTIME_CONTEXT_KEY] = validated.to_dict()
    return updated


def load_runtime_cursor(research_context: Mapping[str, Any]) -> RuntimeCursorLoadResult:
    if CLAIM_ENGINE_RUNTIME_CONTEXT_KEY not in research_context:
        return RuntimeCursorLoadResult(
            status="absent",
            reason="claim_engine_runtime_absent",
        )
    raw = research_context.get(CLAIM_ENGINE_RUNTIME_CONTEXT_KEY)
    if not isinstance(raw, Mapping):
        return RuntimeCursorLoadResult(
            status="unavailable",
            reason="invalid_claim_engine_runtime",
        )
    try:
        cursor = ResearchRuntimeCursor.from_dict(raw)
    except (TypeError, ValueError):
        return RuntimeCursorLoadResult(
            status="unavailable",
            reason="invalid_claim_engine_runtime",
        )
    return RuntimeCursorLoadResult(status="available", cursor=cursor)


def begin_model_attempt(
    cursor: ResearchRuntimeCursor,
    marker: ResearchModelAttemptStart,
) -> ResearchRuntimeCursor:
    if cursor.inflight_model_call is not None:
        raise ValueError("research runtime already has an inflight model call")
    return replace(cursor, inflight_model_call=marker)


def finish_model_attempt(
    cursor: ResearchRuntimeCursor,
    audit: ResearchModelCallAudit,
) -> ResearchRuntimeCursor:
    inflight = cursor.inflight_model_call
    if inflight is None or inflight.call_id != audit.call_id:
        raise ValueError("research model completion does not match inflight call")
    return replace(
        cursor,
        model_calls=(*cursor.model_calls, audit),
        inflight_model_call=None,
    )


def recover_interrupted_model_attempt(
    cursor: ResearchRuntimeCursor,
) -> ResearchRuntimeCursor:
    inflight = cursor.inflight_model_call
    if inflight is None:
        return cursor
    failure = RuntimeFailure(
        code="interrupted_unknown",
        phase=cursor.phase,
        item_id=inflight.call_id,
    )
    return replace(
        cursor,
        inflight_model_call=None,
        failures=(*cursor.failures, failure),
    )


def _validate_cursor_links(cursor: ResearchRuntimeCursor) -> None:
    planned_query_ids = [item.id for item in cursor.planned_queries]
    if len(planned_query_ids) != len(set(planned_query_ids)):
        raise ValueError("runtime planned query ids must be unique")
    planned_query_set = set(planned_query_ids)
    if any(item.query_id not in planned_query_set for item in cursor.query_outcomes):
        raise ValueError("runtime query outcome references unknown query")
    if len(cursor.completed_query_ids) != len(cursor.query_outcomes):
        raise ValueError("runtime query outcomes must be unique per query")

    candidate_ids = [item.id for item in cursor.candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("runtime candidate ids must be unique")
    if any(
        query_id not in planned_query_set
        for item in cursor.candidates
        for query_id in item.query_ids
    ):
        raise ValueError("runtime candidate references unknown query")
    candidate_set = set(candidate_ids)
    if any(candidate_id not in candidate_set for candidate_id in cursor.planned_read_ids):
        raise ValueError("runtime read plan references unknown candidate")
    if any(item.candidate_id not in candidate_set for item in cursor.read_outcomes):
        raise ValueError("runtime read outcome references unknown candidate")
    if len(cursor.completed_read_ids) != len(cursor.read_outcomes):
        raise ValueError("runtime read outcomes must be unique per candidate")

    call_ids = [item.call_id for item in cursor.model_calls]
    if len(call_ids) != len(set(call_ids)):
        raise ValueError("runtime model audit call ids must be unique")
    if cursor.inflight_model_call and cursor.inflight_model_call.call_id in set(call_ids):
        raise ValueError("completed model call cannot remain inflight")


def _object_tuple(value: Any, parser: Any, label: str) -> tuple[Any, ...]:
    if not isinstance(value, list) or len(value) > _MAX_CURSOR_ITEMS:
        raise ValueError(f"invalid {label}")
    return tuple(parser(_as_mapping(item, label)) for item in value)


def _as_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} item must be an object")
    return value


def _strict_mapping(
    raw: Mapping[str, Any], allowed: set[str], label: str
) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise TypeError(f"{label} must be an object")
    data = dict(raw)
    if set(data) != allowed:
        raise ValueError(f"{label} fields do not match schema")
    return data


def _required_text(value: Any, limit: int, label: str) -> str:
    text = _optional_text(value, limit)
    if not text:
        raise ValueError(f"{label} must be non-empty")
    return text


def _optional_text(value: Any, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def _bounded_int(value: Any, minimum: int, maximum: int, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be an integer") from exc
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{label} is out of range")
    return parsed


def _text_tuple(value: Any, max_items: int, item_limit: int) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or len(value) > max_items:
        raise ValueError("invalid text sequence")
    values = tuple(_required_text(item, item_limit, "sequence item") for item in value)
    if len(values) != len(set(values)):
        raise ValueError("text sequence values must be unique")
    return values


__all__ = [
    "CLAIM_ENGINE_RUNTIME_CONTEXT_KEY",
    "RESEARCH_RUNTIME_SCHEMA_VERSION",
    "ResearchRuntimeCursor",
    "RuntimeCandidate",
    "RuntimeCursorLoadResult",
    "RuntimeFailure",
    "RuntimePlannedQuery",
    "RuntimeQueryOutcome",
    "RuntimeReadOutcome",
    "attach_runtime_cursor",
    "begin_model_attempt",
    "finish_model_attempt",
    "load_runtime_cursor",
    "recover_interrupted_model_attempt",
]

"""Batch-C closure matrix for failure, stop, API and UI truth.

This is deliberately a cross-layer contract test rather than another runtime
implementation: Batch B already characterizes each failure path. Batch C locks
that every catalog value still has a production writer, API responses preserve
canonical stop truth verbatim, and the learner-facing UI has a complete display
projection with an unknown-safe fallback.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from src.api.models.news import WebLookupRunResponse
from src.application.research_stop_gate import ResearchStopGate, ResearchStopSignal
from src.web.research.failure_contracts import (
    RESEARCH_FAILURE_CODES,
    RESEARCH_STOP_REASONS,
    require_research_stop_reason,
)

ROOT = Path(__file__).resolve().parents[1]

FAILURE_WRITER_PATHS = (
    "src/application/active_research_runtime.py",
    "src/web/research/runtime.py",
)
STOP_WRITER_PATHS = (
    "src/application/research_stop_gate.py",
    "src/application/active_research_runtime.py",
    "src/application/web_lookup_service.py",
    "src/repositories/web_lookup_repository.py",
    "src/infrastructure/sqlite/database.py",
)
UI_CATALOG_PATH = "frontend/src/features/web-lookup/researchStopReason.ts"
UI_CONSUMER_PATH = "frontend/src/features/web-lookup/ChatResearchRecovery.tsx"
UI_TRANSPORT_PATH = "frontend/src/features/web-lookup/researchApi.ts"
API_ROUTE_PATH = "src/api/routes/web_lookup_routes.py"


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _api_response(stop_reason: str) -> WebLookupRunResponse:
    return WebLookupRunResponse(
        id="research-matrix-1",
        query="matrix contract",
        status="completed",
        items=[],
        source_block="",
        warnings=[],
        error="",
        stop_reason=stop_reason,
        version=1,
        created_at="2026-09-02T00:00:00Z",
        updated_at="2026-09-02T00:00:01Z",
        completed_at="2026-09-02T00:00:01Z",
    )


def test_writer_side_stop_guard_is_closed_but_reader_contract_is_not() -> None:
    assert require_research_stop_reason("evidence_gate_pass") == "evidence_gate_pass"
    with pytest.raises(ValueError):
        require_research_stop_reason("future_provider_specific_stop")

    # API models are readers/transport. Frozen 7A/11A requires unknown legacy
    # or future strings to remain readable rather than being rewritten or lost.
    future = "future_provider_specific_stop"
    assert _api_response(future).stop_reason == future


def test_stop_gate_rejects_an_unregistered_new_writer_reason() -> None:
    with pytest.raises(ValueError, match="unknown research stop reason"):
        ResearchStopGate.evaluate(
            ResearchStopSignal(
                gate_pass=False,
                hard_budget_exhausted=False,
                has_actionable_gaps=True,
                all_actionable_saturated=False,
                wave_limit_reached=False,
                has_evidence=False,
                unavailable_reason="provider_timeout",
            )
        )


def test_failure_catalog_has_a_production_writer_surface() -> None:
    writer_source = "\n".join(_source(path) for path in FAILURE_WRITER_PATHS)
    missing = sorted(
        code for code in RESEARCH_FAILURE_CODES if f'"{code}"' not in writer_source
    )
    assert missing == []


def test_stop_catalog_has_a_production_writer_surface() -> None:
    writer_source = "\n".join(_source(path) for path in STOP_WRITER_PATHS)
    missing = sorted(
        reason
        for reason in RESEARCH_STOP_REASONS
        if f'"{reason}"' not in writer_source and f"'{reason}'" not in writer_source
    )
    assert missing == []


def test_api_preserves_every_canonical_stop_reason_verbatim() -> None:
    for reason in RESEARCH_STOP_REASONS:
        response = _api_response(reason)
        assert response.stop_reason == reason
        assert response.model_dump()["stop_reason"] == reason

    route_source = _source(API_ROUTE_PATH)
    assert "return WebLookupRunResponse(**asdict(run))" in route_source

    transport_source = _source(UI_TRANSPORT_PATH)
    assert "stop_reason: run.stop_reason" in transport_source


def test_ui_display_catalog_exactly_matches_backend_stop_catalog() -> None:
    source = _source(UI_CATALOG_PATH)
    match = re.search(
        r"KNOWN_RESEARCH_STOP_REASONS\s*=\s*\[(.*?)\]\s*as const",
        source,
        flags=re.DOTALL,
    )
    assert match is not None
    ui_reasons = set(re.findall(r'"([a-z0-9_]+)"', match.group(1)))
    assert ui_reasons == RESEARCH_STOP_REASONS


def test_ui_unknown_reason_has_a_safe_non_echo_fallback() -> None:
    catalog_source = _source(UI_CATALOG_PATH)
    assert (
        "RESEARCH_STOP_REASON_LABELS[reason as KnownResearchStopReason] ?? fallback"
        in catalog_source
    )
    assert "return reason" not in catalog_source

    consumer_source = _source(UI_CONSUMER_PATH)
    assert "researchStopReasonDisplay" in consumer_source
    assert "progress.stop_reason ??" not in consumer_source
    assert "run.stop_reason ||" not in consumer_source

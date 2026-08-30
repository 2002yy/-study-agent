from __future__ import annotations

from typing import Any, cast

import pytest

from src.application import runtime_repository
from src.application.research_web_lookup_dispatch import (
    ClaimEngineDispatchWebLookupService,
    _AuditedRepositoryProxy,
    _dispatch_mode,
)
from src.application.web_lookup_service import WebLookupService
from src.domain.evidence import build_evidence_snapshot
from src.domain.runtime_entities import WebLookupRun
from src.infrastructure.sqlite.database import RuntimeDatabase
from src.repositories.web_lookup_repository import WebLookupRepository
from src.web.research.active_adapter import ActiveResearchGateway
from src.web.research.contracts import (
    EvidenceGap,
    EvidenceRequirement,
    ResearchBudget,
    ResearchClaim,
    ResearchEvidence,
    ResearchQuestion,
    build_research_state,
)
from src.web.research.state import attach_claim_engine_state
from src.web.research_contract import build_research_context


def _budget() -> ResearchBudget:
    return ResearchBudget(
        max_candidates=20,
        max_reads=8,
        soft_timeout_seconds=45,
        hard_timeout_seconds=60,
        max_total_chars=16000,
    )


def _claim_engine_context(
    mode: str,
    *,
    evidence_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    state = build_research_state(
        mode=cast(Any, mode),
        questions=(),
        claims=(),
        evidence=tuple(
            ResearchEvidence(
                evidence_id=evidence_id,
                lifecycle_status="selected",
                extraction_status="eligible",
            )
            for evidence_id in evidence_ids
        ),
        evidence_links=(),
        source_clusters=(),
        gaps=(),
        conflict_gaps=(),
        budget=_budget(),
        known_evidence_ids=evidence_ids,
    )
    return attach_claim_engine_state(
        {"source_truth_version": 2},
        state,
        known_evidence_ids=evidence_ids,
    )


def _selected_source() -> dict[str, Any]:
    return {
        "item": {
            "title": "Authoritative source",
            "url": "https://example.com/report",
        },
        "assessment": {
            "title": "Authoritative source",
            "url": "https://example.com/report",
            "selected": True,
            "worth_reading": True,
        },
        "read_status": "read",
    }


def _active_context_with_open_claim() -> dict[str, Any]:
    question = ResearchQuestion(
        id="question_active",
        question_surface="bounded factual query",
        priority="critical",
        state="unresolved",
    )
    claim = ResearchClaim(
        id="claim_active",
        question_id=question.id,
        text="bounded factual query",
        kind="factual",
        priority="critical",
        state="pending",
        evidence_requirement=EvidenceRequirement(
            source_roles=("primary", "independent_secondary"),
            min_independent_sources=1,
        ),
    )
    gap = EvidenceGap(
        id="gap_active",
        claim_id=claim.id,
        gap_type="missing_evidence",
        desired_source_role="primary",
        priority="critical",
    )
    state = build_research_state(
        mode="active",
        questions=(question,),
        claims=(claim,),
        evidence=(),
        evidence_links=(),
        source_clusters=(),
        gaps=(gap,),
        conflict_gaps=(),
        budget=_budget(),
        reference_date="2026-08-27",
        known_evidence_ids=(),
    )
    return attach_claim_engine_state(
        {"source_truth_version": 2},
        state,
        known_evidence_ids=(),
    )


def _server_owned_id_for_source(source: dict[str, Any]) -> str:
    snapshot = build_evidence_snapshot(
        rag={
            "research_sources": {
                "run_id": "run_dispatch",
                "provider_status": "found",
                "source_truth_version": 2,
                "selected_sources": [source],
                "rejected_sources": [],
            }
        }
    )
    assert len(snapshot.refs) == 1
    return snapshot.refs[0].id


def test_dispatch_mode_defaults_absent_and_shadow_to_legacy() -> None:
    absent = WebLookupRun(id="run_absent", research_context={})
    shadow = WebLookupRun(
        id="run_shadow",
        research_context=_claim_engine_context("shadow"),
    )

    assert _dispatch_mode(absent) == "legacy"
    assert _dispatch_mode(shadow) == "legacy"


def test_dispatch_mode_requires_server_owned_evidence_validation() -> None:
    source = _selected_source()
    evidence_id = _server_owned_id_for_source(source)
    active = WebLookupRun(
        id="run_dispatch",
        research_context=_claim_engine_context(
            "active",
            evidence_ids=(evidence_id,),
        ),
        selected_sources=[source],
        provider_status="found",
    )
    assert _dispatch_mode(active) == "active"

    forged_context = _claim_engine_context("active")
    forged_context["claim_engine"]["evidence"] = [
        {
            "evidence_id": "forged_evidence_id",
            "locator": "",
            "anchored_spans": [],
            "lifecycle_status": "selected",
            "extraction_status": "eligible",
            "published_at": "",
        }
    ]
    forged = WebLookupRun(
        id="run_forged",
        research_context=forged_context,
    )
    assert _dispatch_mode(forged) == "legacy"


def test_dispatch_service_switches_gateway_only_for_valid_active_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRepository:
        def __init__(self, run: WebLookupRun) -> None:
            self.run = run

        def get(self, run_id: str) -> WebLookupRun | None:
            return self.run if run_id == self.run.id else None

    executed_gateways: list[Any] = []

    def fake_execute(
        self: WebLookupService,
        run_id: str,
        *,
        raise_on_error: bool = False,
        stale_after_seconds: int = 120,
    ) -> WebLookupRun:
        del raise_on_error, stale_after_seconds
        executed_gateways.append(self.gateway)
        result = self.repository.get(run_id)
        assert result is not None
        return result

    monkeypatch.setattr(WebLookupService, "execute", fake_execute)

    legacy_gateway = object()
    active_created: list[ActiveResearchGateway] = []

    def active_factory() -> ActiveResearchGateway:
        gateway = ActiveResearchGateway(search_backend=cast(Any, object()))
        active_created.append(gateway)
        return gateway

    legacy_run = WebLookupRun(id="legacy", status="pending", research_context={})
    legacy_service = ClaimEngineDispatchWebLookupService(
        cast(WebLookupRepository, FakeRepository(legacy_run)),
        gateway=cast(Any, legacy_gateway),
        active_gateway_factory=active_factory,
    )
    assert legacy_service.execute("legacy") == legacy_run
    assert executed_gateways[-1] is legacy_gateway
    assert active_created == []

    active_run = WebLookupRun(
        id="active",
        status="pending",
        research_context=_claim_engine_context("active"),
    )
    active_service = ClaimEngineDispatchWebLookupService(
        cast(WebLookupRepository, FakeRepository(active_run)),
        gateway=cast(Any, legacy_gateway),
        active_gateway_factory=active_factory,
        active_runtime_factory=lambda repository, gateway: cast(
            Any,
            type(
                "FakeRuntime",
                (),
                {
                    "execute": lambda self, run_id, **kwargs: (
                        executed_gateways.append(gateway)
                        or repository.get(run_id)
                    )
                },
            )(),
        ),
    )
    assert active_service.execute("active") == active_run
    assert executed_gateways[-1] is active_created[-1]
    assert len(active_created) == 1


class _AuditGateway:
    def __init__(self) -> None:
        self.audit: dict[str, Any] | None = None

    def last_search_audit(self) -> dict[str, Any] | None:
        return dict(self.audit) if self.audit is not None else None


class _RecordingRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def checkpoint(self, run_id: str, **kwargs: Any) -> WebLookupRun:
        self.calls.append(("checkpoint", kwargs))
        return WebLookupRun(id=run_id)

    def complete(self, run_id: str, **kwargs: Any) -> WebLookupRun:
        self.calls.append(("complete", kwargs))
        return WebLookupRun(id=run_id)

    def fail(self, run_id: str, error: str, **kwargs: Any) -> WebLookupRun:
        self.calls.append(("fail", {"error": error, **kwargs}))
        return WebLookupRun(id=run_id)


def _checkpoint_kwargs(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "operation_id": "op1",
        "research_context": {},
        "query_attempts": attempts,
        "selected_sources": [],
        "rejected_sources": [],
        "items": [],
        "warnings": [],
    }


def test_audit_proxy_preserves_each_search_audit_through_terminal_write() -> None:
    repository = _RecordingRepository()
    gateway = _AuditGateway()
    proxy = _AuditedRepositoryProxy(
        cast(WebLookupRepository, repository),
        cast(ActiveResearchGateway, gateway),
    )

    gateway.audit = {
        "status": "ok",
        "reason": "results_found",
        "providers_attempted": ["searxng"],
        "provider_errors": [],
        "provider_audits": [],
        "provider_outcomes": [],
        "searched_at": "2026-08-27T00:00:00+00:00",
    }
    proxy.checkpoint("run1", **_checkpoint_kwargs([{"query": "q1"}]))

    gateway.audit = {
        "status": "partial",
        "reason": "results_with_provider_failures",
        "providers_attempted": ["searxng", "duckduckgo_html"],
        "provider_errors": ["duckduckgo_html:timeout"],
        "provider_audits": [],
        "provider_outcomes": [],
        "searched_at": "2026-08-27T00:00:01+00:00",
    }
    attempts = [{"query": "q1"}, {"query": "q2"}]
    proxy.checkpoint("run1", **_checkpoint_kwargs(attempts))
    proxy.complete(
        "run1",
        items=[],
        source_block="",
        warnings=[],
        research_context={},
        query_attempts=attempts,
        selected_sources=[],
        rejected_sources=[],
        operation_id="op1",
    )

    terminal_attempts = repository.calls[-1][1]["query_attempts"]
    assert terminal_attempts[0]["provider_audit"]["status"] == "ok"
    assert terminal_attempts[1]["provider_audit"]["status"] == "partial"
    assert terminal_attempts[0]["provider_audit"]["schema_version"] == (
        "research-provider-audit-v1"
    )


def test_active_gateway_clears_stale_audit_before_backend_exception() -> None:
    class Backend:
        def __init__(self) -> None:
            self.calls = 0

        def search_exact(
            self,
            query: str,
            *,
            max_results: int = 5,
        ) -> dict[str, Any]:
            del query, max_results
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("backend exploded")
            return {
                "status": "ok",
                "reason": "results_found",
                "results": [],
                "providers_attempted": ["searxng"],
                "provider_errors": [],
                "provider_audits": [],
                "provider_outcomes": [],
                "searched_at": "2026-08-27T00:00:00+00:00",
            }

    gateway = ActiveResearchGateway(search_backend=Backend())
    gateway.search_detailed("first")
    assert gateway.last_search_audit() is not None

    with pytest.raises(RuntimeError, match="backend exploded"):
        gateway.search_detailed("second")

    assert gateway.last_search_audit() is None
    assert gateway.warnings() == []


def test_active_dispatch_persists_provider_audit_in_real_repository(
    tmp_path: Any,
) -> None:
    class EmptyBackend:
        def search_exact(
            self,
            query: str,
            *,
            max_results: int = 5,
        ) -> dict[str, Any]:
            del query, max_results
            return {
                "status": "empty",
                "reason": "providers_returned_no_results",
                "results": [],
                "providers_attempted": ["searxng", "bing_rss"],
                "provider_errors": [],
                "provider_audits": [
                    {
                        "provider": "searxng",
                        "attempt": 1,
                        "status": "empty",
                        "reason": "no_results",
                        "result_count": 0,
                        "elapsed_seconds": 0.01,
                        "query_sha256": "0" * 64,
                        "query_chars": 12,
                    }
                ],
                "provider_outcomes": [
                    {
                        "provider": "searxng",
                        "status": "empty",
                        "reason": "no_results",
                        "attempts": 1,
                        "result_count": 0,
                    }
                ],
                "searched_at": "2026-08-27T00:00:00+00:00",
            }

    repository = WebLookupRepository(RuntimeDatabase(tmp_path / "dispatch.sqlite"))
    context = build_research_context("bounded factual query").to_dict()
    context.update(_active_context_with_open_claim())
    run = repository.create(
        WebLookupRun(
            id="run_active_integration",
            query="bounded factual query",
            stage="planned",
            status="pending",
            research_context=context,
            max_items=5,
        )
    )
    service = ClaimEngineDispatchWebLookupService(
        repository,
        active_gateway_factory=lambda: ActiveResearchGateway(
            search_backend=EmptyBackend()
        ),
    )

    completed = service.execute(run.id)

    assert completed.status == "partial"
    assert completed.provider_status == "insufficient"
    assert completed.stop_reason == "evidence_saturated"
    assert completed.query_attempts
    audit = completed.query_attempts[0]["provider_audit"]
    assert audit["schema_version"] == "research-provider-audit-v1"
    assert audit["status"] == "empty"
    assert audit["providers_attempted"] == ["searxng", "bing_rss"]
    assert "results" not in audit


def test_runtime_factory_returns_dispatch_service(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STUDY_AGENT_RUNTIME_DB", str(tmp_path / "factory.sqlite"))
    runtime_repository.get_web_lookup_service.cache_clear()
    runtime_repository.get_web_lookup_repository.cache_clear()
    try:
        service = runtime_repository.get_web_lookup_service()
        assert isinstance(service, ClaimEngineDispatchWebLookupService)
    finally:
        runtime_repository.get_web_lookup_service.cache_clear()
        runtime_repository.get_web_lookup_repository.cache_clear()

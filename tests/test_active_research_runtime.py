from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from json import loads
from pathlib import Path
from types import SimpleNamespace
from threading import Event, Thread
from time import perf_counter
from typing import Any

import pytest

from src.application.active_research_runtime import (
    ACTIVE_RESEARCH_BRIEF_KEY,
    ACTIVE_RESEARCH_METRICS_KEY,
    ACTIVE_RESEARCH_READ_PLAN_KEY,
    ACTIVE_RESEARCH_WAVE_BASELINE_KEY,
    ActiveResearchRuntimeExecutor,
    _append_gap_queries,
    _restore_completed_read_targets,
)
from src.application.research_web_lookup_dispatch import (
    _dispatch_state,
    ClaimEngineDispatchWebLookupService,
)
from src.api.routes.chat_routes import _research_progress
from src.domain.runtime_entities import WebLookupRun
from src.infrastructure.sqlite.database import RuntimeDatabase
from src.repositories.web_lookup_repository import WebLookupRepository
from src.web.research.active_adapter import ActiveResearchGateway
from src.web.research.claim_planner import ClaimBootstrapResult, RuntimeClaimPlanner
from src.web.research.contracts import (
    EvidenceGap,
    EvidenceRequirement,
    ResearchBudget,
    ResearchClaim,
    ResearchQuestion,
    build_research_state,
)
from src.web.research.model_gateway import ResearchModelGateway
from src.web.research.runtime import CLAIM_ENGINE_RUNTIME_CONTEXT_KEY, ResearchRuntimeCursor
from src.web.research.state import attach_claim_engine_state


def _active_context(*, policy_allowed: bool = True) -> dict[str, Any]:
    state = build_research_state(
        mode="active",
        questions=(),
        claims=(),
        evidence=(),
        evidence_links=(),
        source_clusters=(),
        gaps=(),
        conflict_gaps=(),
        budget=ResearchBudget(
            max_candidates=20,
            max_reads=8,
            soft_timeout_seconds=45,
            hard_timeout_seconds=60,
            max_total_chars=16000,
        ),
        reference_date="2026-08-27",
        known_evidence_ids=(),
    )
    return attach_claim_engine_state(
        {
            "source_truth_version": 2,
            "run_attempt": 0,
            "external_data_policy": {
                "web_allowed": policy_allowed,
                "reason": "allowed" if policy_allowed else "web_disabled_by_user",
            },
        },
        state,
        known_evidence_ids=(),
    )


class _StructuredClient:
    def __init__(
        self,
        *,
        on_call: Callable[[int], None] | None = None,
        malformed_extraction: bool = False,
        claims_count: int = 1,
    ) -> None:
        self.chat = SimpleNamespace(completions=self)
        self.calls: list[dict[str, Any]] = []
        self.on_call = on_call
        self.malformed_extraction = malformed_extraction
        self.claims_count = claims_count

    def with_options(self, **kwargs: Any) -> "_StructuredClient":
        assert kwargs == {"max_retries": 0}
        return self

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.on_call is not None:
            self.on_call(len(self.calls))
        system = str(kwargs["messages"][0]["content"])
        request = loads(str(kwargs["messages"][1]["content"]))
        if "claim planner" in system:
            claims = [
                {
                    "surface": "The verified release date is current",
                    "kind": "factual",
                    "priority": "critical",
                    "policy_profile": "current_fact",
                }
            ]
            if self.claims_count > 1:
                claims.append(
                    {
                        "surface": "The release announcement is published by the official project",
                        "kind": "factual",
                        "priority": "major",
                        "policy_profile": "current_fact",
                    }
                )
            payload = {
                "schema_version": "research-runtime-claim-plan-v1",
                "claims": claims,
            }
        elif "search candidates" in system:
            payload = {
                "schema_version": "candidate-assessment-v1",
                "assessments": [
                    {
                        "candidate_id": item["candidate_id"],
                        "relevance": "answer_relevant",
                        "relevance_confidence": 0.98,
                        "source_role": (
                            "primary" if index == 0 else "independent_secondary"
                        ),
                        "source_role_confidence": 0.95,
                        "expected_gain_signals": [
                            "new_primary" if index == 0 else "new_independent_cluster"
                        ],
                    }
                    for index, item in enumerate(request["candidates"])
                ],
            }
        else:
            # H7: anchors must differ per claim AND exist in the read excerpt
            # (the strict parser rejects anchors absent from the excerpt), and
            # the fake output must be deterministic per claim input.
            claim_text = str(request["claim_text"])
            if "official project" in claim_text:
                locator = "2026-08-01"
                anchored_spans = ["2026-08-01"]
            else:
                locator = "release date"
                anchored_spans = ["release date"]
            payload = {
                "schema_version": "research-evidence-extraction-v1",
                "candidate_id": (
                    "model_minted_candidate"
                    if self.malformed_extraction
                    else request["candidate_id"]
                ),
                "claim_id": request["claim_id"],
                "source_role": request["source_role"],
                "source_cluster_id": request["source_cluster_id"],
                "relation": "supports",
                "strength": 0.95,
                "locator": locator,
                "anchored_spans": anchored_spans,
                "caveats": [],
                "published_at": request["published_at"],
            }
        content = __import__("json").dumps(payload)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=content),
                    finish_reason="stop",
                )
            ],
            usage=SimpleNamespace(
                prompt_tokens=10,
                completion_tokens=10,
                total_tokens=20,
            ),
        )


class _SearchBackend:
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
        results = [
            {
                "title": "Primary release",
                "url": "https://official.example/release",
                "snippet": "Verified release announcement",
                "published_at": "2026-08-01",
                "provider": "searxng",
            },
            {
                "title": "Independent verification",
                "url": "https://independent.example/report",
                "snippet": "Independent verification of the date",
                "published_at": "2026-08-02",
                "provider": "bing_rss",
            },
        ]
        return {
            "status": "ok",
            "reason": "results_found",
            "results": results,
            "providers_attempted": ["searxng", "bing_rss", "duckduckgo_html"],
            "provider_errors": [],
            "provider_audits": [],
            "provider_outcomes": [],
            "searched_at": "2026-08-27T00:00:00+00:00",
        }


class _EmptySearchBackend:
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
        return {
            "status": "empty",
            "reason": "no_results",
            "results": [],
            "providers_attempted": ["searxng"],
            "provider_errors": [],
            "provider_audits": [],
            "provider_outcomes": [],
            "searched_at": "2026-08-29T00:00:00+00:00",
        }


class _FloodSearchBackend:
    """Return a full pool of candidates on the first query (B5-H2)."""

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
        results = [
            {
                "title": f"Flood result {index}",
                "url": f"https://flood.example/{self.calls}-{index}",
                "snippet": f"Flood snippet {index}",
                "published_at": "2026-08-01",
                "provider": "searxng",
            }
            for index in range(20)
        ]
        return {
            "status": "ok",
            "reason": "results_found",
            "results": results,
            "providers_attempted": ["searxng"],
            "provider_errors": [],
            "provider_audits": [],
            "provider_outcomes": [],
            "searched_at": "2026-08-27T00:00:00+00:00",
        }


class _ProvenanceSearchBackend:
    """Claim A queries return shared+a-only; claim B queries shared+b-only (B5-H3)."""

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
        urls = (
            ["https://shared.example/source", "https://a-only.example/source"]
            if self.calls <= 2
            else ["https://shared.example/source", "https://b-only.example/source"]
        )
        results = [
            {
                "title": f"Result {url}",
                "url": url,
                "snippet": "Verified release announcement",
                "published_at": "2026-08-01",
                "provider": "searxng",
            }
            for url in urls
        ]
        return {
            "status": "ok",
            "reason": "results_found",
            "results": results,
            "providers_attempted": ["searxng"],
            "provider_errors": [],
            "provider_audits": [],
            "provider_outcomes": [],
            "searched_at": "2026-08-27T00:00:00+00:00",
        }


class _ReadGateway:
    def __init__(self, on_read: Callable[[], None] | None = None) -> None:
        self.on_read = on_read
        self.calls = 0

    def read(self, url: str, *, max_chars: int = 6000) -> dict[str, Any]:
        self.calls += 1
        if self.on_read is not None:
            self.on_read()
        return {
            "ok": True,
            "url": url,
            "title": "Read source",
            "content": "Verified fact: The release date is 2026-08-01."[:max_chars],
        }


class _TrackingRepository(WebLookupRepository):
    def __init__(self, database: RuntimeDatabase) -> None:
        super().__init__(database)
        self.visible_stages: list[str] = []

    def set_stage(
        self,
        run_id: str,
        *,
        stage: str,
        operation_id: str,
    ) -> WebLookupRun:
        self.visible_stages.append(stage)
        return super().set_stage(run_id, stage=stage, operation_id=operation_id)


def _service(
    repository: WebLookupRepository,
    client: _StructuredClient,
    *,
    search_backend: Any | None = None,
    read_gateway: Any | None = None,
) -> ClaimEngineDispatchWebLookupService:
    def gateway_factory() -> ActiveResearchGateway:
        return ActiveResearchGateway(
            search_backend=search_backend or _SearchBackend(),
            read_gateway=read_gateway or _ReadGateway(),
        )

    def runtime_factory(
        repo: WebLookupRepository,
        gateway: ActiveResearchGateway,
    ) -> ActiveResearchRuntimeExecutor:
        model = ResearchModelGateway(
            client=client,
            model_name="test-model",
            timeout_seconds=20,
        )
        return ActiveResearchRuntimeExecutor(repo, gateway, model_gateway=model)

    return ClaimEngineDispatchWebLookupService(
        repository,
        active_gateway_factory=gateway_factory,
        active_runtime_factory=runtime_factory,
    )


def test_active_single_wave_builds_strict_evidence_and_passes_gate(tmp_path: Any) -> None:
    repository = _TrackingRepository(RuntimeDatabase(tmp_path / "active.sqlite"))
    run = repository.create(
        WebLookupRun(
            id="run_active_single_wave",
            query="What is the verified current release date?",
            stage="planned",
            status="pending",
            research_context=_active_context(),
            max_items=5,
        )
    )
    client = _StructuredClient()

    completed = _service(repository, client).execute(run.id, raise_on_error=True)

    assert completed.status == "completed"
    assert completed.provider_status == "found"
    assert completed.stop_reason == "evidence_gate_pass"
    assert len(completed.items) == 2
    assert len(completed.selected_sources) == 2
    assert all(item["read_status"] == "read" for item in completed.selected_sources)
    assert all(
        item["extraction"]["status"] == "eligible"
        for item in completed.selected_sources
    )
    brief = completed.research_context[ACTIVE_RESEARCH_BRIEF_KEY]
    assert brief["gate_status"] == "pass"
    assert brief["conditional_wording_required"] is False
    assert len(brief["eligible_evidence"]) == 2
    assert brief["open_critical_claim_ids"] == []
    assert "Search results" not in completed.source_block
    metrics = completed.research_context[ACTIVE_RESEARCH_METRICS_KEY]
    assert metrics["candidate_count"] == 2
    assert metrics["read_count"] == 2
    assert metrics["cluster_count"] == 2
    assert all(attempt.get("provider_audit") for attempt in completed.query_attempts)
    runtime = completed.research_context["claim_engine_runtime"]
    assert runtime["inflight_model_call"] is None
    assert runtime["inflight_external_call"] is None
    assert len(runtime["model_calls"]) == len(client.calls)
    assert client.calls
    assert all(1.0 <= float(call["timeout"]) <= 20.0 for call in client.calls)
    assert {
        tuple(candidate["providers"])
        for candidate in runtime["candidates"]
    } == {("searxng",), ("bing_rss",)}
    assert repository.visible_stages == ["searching", "assessing", "reading", "gating"]
    progress = _research_progress(completed)
    assert progress["candidate_count"] == 2
    assert progress["read_count"] == 2
    assert progress["cluster_count"] == 2
    assert progress["open_critical_gap_count"] == 0
    assert progress["gate_status"] == "pass"


def test_active_model_policy_denial_fails_closed_before_external_call(tmp_path: Any) -> None:
    repository = WebLookupRepository(RuntimeDatabase(tmp_path / "deny.sqlite"))
    run = repository.create(
        WebLookupRun(
            id="run_active_policy_deny",
            query="Research this",
            stage="planned",
            status="pending",
            research_context=_active_context(policy_allowed=False),
        )
    )
    client = _StructuredClient()

    failed = _service(repository, client).execute(run.id)

    assert failed.status == "failed"
    assert failed.provider_status == "unavailable"
    assert failed.stop_reason == "claim_planning_blocked_by_policy"
    assert client.calls == []
    audits = failed.research_context["claim_engine_policy_audits"]
    assert audits[-1]["status"] == "blocked_by_policy"


def _two_gap_state(*, same_claim_text: bool = False) -> Any:
    question = ResearchQuestion(id="question_1", question_surface="Compare releases")
    requirement = EvidenceRequirement(
        source_roles=("primary", "independent_secondary"),
        min_independent_sources=2,
        requires_primary_source=True,
    )
    claims = (
        ResearchClaim(
            id="claim_1",
            question_id=question.id,
            text="Alpha framework current release",
            kind="factual",
            priority="critical",
            state="searching",
            evidence_requirement=requirement,
        ),
        ResearchClaim(
            id="claim_2",
            question_id=question.id,
            text=(
                "Alpha framework current release"
                if same_claim_text
                else "Beta framework current release"
            ),
            kind="factual",
            priority="critical",
            state="searching",
            evidence_requirement=requirement,
        ),
    )
    gaps = (
        EvidenceGap(
            id="gap_1",
            claim_id="claim_1",
            gap_type="missing_primary",
            desired_source_role="primary",
            priority="critical",
        ),
        EvidenceGap(
            id="gap_2",
            claim_id="claim_2",
            gap_type="missing_primary",
            desired_source_role="primary",
            priority="critical",
        ),
    )
    return build_research_state(
        mode="active",
        questions=(question,),
        claims=claims,
        evidence=(),
        evidence_links=(),
        source_clusters=(),
        gaps=gaps,
        conflict_gaps=(),
        budget=ResearchBudget(
            max_candidates=20,
            max_reads=8,
            soft_timeout_seconds=45,
            hard_timeout_seconds=60,
            max_total_chars=16000,
        ),
        reference_date="2026-08-29",
        known_evidence_ids=(),
    )


def test_two_gap_wave_appends_four_unique_queries_per_gap_once() -> None:
    state = _two_gap_state()

    first_wave = _append_gap_queries(ResearchRuntimeCursor(), state)
    second_wave = _append_gap_queries(first_wave, state)

    assert Counter(query.gap_id for query in first_wave.planned_queries) == {
        "gap_1": 4,
        "gap_2": 4,
    }
    assert len(first_wave.planned_queries) == 8
    assert len({query.id for query in first_wave.planned_queries}) == 8
    assert second_wave.planned_queries == first_wave.planned_queries


def test_semantic_query_dedupe_still_saturates_each_active_gap(tmp_path: Any) -> None:
    state = _two_gap_state(same_claim_text=True)
    context = attach_claim_engine_state(
        _active_context(),
        state,
        known_evidence_ids=(),
    )
    repository = _TrackingRepository(RuntimeDatabase(tmp_path / "active-gaps.sqlite"))
    run = repository.create(
        WebLookupRun(
            id="run_active_gap_saturation",
            query="Compare identical research surfaces",
            stage="planned",
            status="pending",
            research_context=context,
            max_items=5,
        )
    )
    search = _EmptySearchBackend()
    client = _StructuredClient()

    completed = _service(repository, client, search_backend=search).execute(
        run.id,
        raise_on_error=True,
    )

    assert completed.status == "partial"
    assert completed.stop_reason == "evidence_saturated"
    cursor = ResearchRuntimeCursor.from_dict(
        completed.research_context[CLAIM_ENGINE_RUNTIME_CONTEXT_KEY]
    )
    assert cursor.wave_index == 3
    assert cursor.active_gap_ids == ("gap_1", "gap_2")
    assert cursor.no_gain_batches_by_gap == {"gap_1": 3, "gap_2": 3}
    assert cursor.no_gain_batches_by_claim == {"claim_1": 3, "claim_2": 3}
    assert len(cursor.gain_history) == 3
    assert all(item["substantive_gain"] is False for item in cursor.gain_history)
    assert len(cursor.planned_queries) == 4
    assert len({item.query.casefold() for item in cursor.planned_queries}) == 4
    assert search.calls == 4
    assert client.calls == []


def test_malformed_extraction_never_becomes_evidence_and_resume_skips_calls(
    tmp_path: Any,
) -> None:
    repository = WebLookupRepository(RuntimeDatabase(tmp_path / "malformed.sqlite"))
    run = repository.create(
        WebLookupRun(
            id="run_active_malformed_extraction",
            query="What is the verified current release date?",
            stage="planned",
            status="pending",
            research_context=_active_context(),
        )
    )
    client = _StructuredClient(malformed_extraction=True)

    partial = _service(repository, client).execute(run.id, raise_on_error=True)

    assert partial.status == "partial"
    assert partial.provider_status == "insufficient"
    assert partial.stop_reason == "evidence_saturated"
    assert partial.items == []
    assert all(item["read_status"] == "read" for item in partial.selected_sources)
    assert all(
        list((item.get("extractions") or {}).values())[0]["status"] == "extractor_failed"
        for item in partial.selected_sources
    )
    partial_brief = partial.research_context[ACTIVE_RESEARCH_BRIEF_KEY]
    assert partial_brief["gate_status"] in {"block", "partial"}
    assert partial_brief["conditional_wording_required"] is True
    assert "只能使用条件化措辞" in partial.source_block
    assert partial.research_context[ACTIVE_RESEARCH_BRIEF_KEY]["eligible_evidence"] == []

    resumed_client = _StructuredClient(on_call=lambda _index: (_ for _ in ()).throw(AssertionError("model call repeated")))
    resumed_search = _SearchBackend()
    resumed_read = _ReadGateway()
    resumed = _service(
        repository,
        resumed_client,
        search_backend=resumed_search,
        read_gateway=resumed_read,
    ).execute(run.id, raise_on_error=True)

    assert resumed.status == "partial"
    assert resumed.stop_reason == "evidence_saturated"
    assert resumed_client.calls == []
    assert resumed_read.calls == 0


def test_model_crash_after_success_before_semantic_persist_recovers_via_new_attempt(
    tmp_path: Any,
) -> None:
    """B5-H1: a completed model audit must never persist without its semantic result.

    A crash between the model audit callback and the semantic-result checkpoint
    leaves the durable truth as an inflight call, so recovery resolves through
    interrupted_unknown with a bounded new attempt instead of raising
    "completed model call cannot remain inflight".
    """
    repository = _TrackingRepository(RuntimeDatabase(tmp_path / "active_crash.sqlite"))
    run = repository.create(
        WebLookupRun(
            id="run_active_crash_semantic_persist",
            query="What is the verified current release date?",
            stage="planned",
            status="pending",
            research_context=_active_context(),
            max_items=5,
        )
    )
    client = _StructuredClient()

    class _CrashAfterModelSuccessPlanner(RuntimeClaimPlanner):
        def __init__(self, inner: RuntimeClaimPlanner, repo: WebLookupRepository) -> None:
            self._inner = inner
            self._repo = repo
            self.calls = 0

        def plan(self, **kwargs: Any) -> ClaimBootstrapResult:
            self.calls += 1
            bootstrap = self._inner.plan(**kwargs)
            if self.calls == 1:
                # The model succeeded and the audit callback ran; before the
                # semantic result is persisted the durable truth must still be
                # an inflight call with no completed audit.
                durable = self._repo.get(run.id)
                assert durable is not None
                cursor = ResearchRuntimeCursor.from_dict(
                    durable.research_context[CLAIM_ENGINE_RUNTIME_CONTEXT_KEY]
                )
                assert cursor.inflight_model_call is not None
                assert cursor.model_calls == ()
                # Simulate the process dying: fail the run through its real
                # owner so the executor fallback short-circuits and the durable
                # state stays at the last checkpoint (the inflight marker).
                self._repo.fail(
                    run.id,
                    "simulated crash before semantic persist",
                    operation_id=durable.active_operation_id,
                )
                raise RuntimeError("simulated crash before semantic persist")
            return bootstrap

    model = ResearchModelGateway(
        client=client,
        model_name="test-model",
        timeout_seconds=20,
    )
    # Shared across execute() calls so the crash triggers exactly once.
    crash_planner = _CrashAfterModelSuccessPlanner(
        RuntimeClaimPlanner(model),
        repository,
    )

    def runtime_factory(
        repo: WebLookupRepository,
        gateway: ActiveResearchGateway,
    ) -> ActiveResearchRuntimeExecutor:
        return ActiveResearchRuntimeExecutor(
            repo,
            gateway,
            model_gateway=model,
            claim_planner=crash_planner,
        )

    service = ClaimEngineDispatchWebLookupService(
        repository,
        active_gateway_factory=lambda: ActiveResearchGateway(
            search_backend=_SearchBackend(),
            read_gateway=_ReadGateway(),
        ),
        active_runtime_factory=runtime_factory,
    )

    with pytest.raises(RuntimeError, match="simulated crash"):
        service.execute(run.id, raise_on_error=True)

    crashed = repository.get(run.id)
    assert crashed is not None
    # The wrapper intentionally failed the run to short-circuit the executor
    # fallback; the H1 invariant is that the durable cursor still holds the
    # inflight marker with no completed audit.
    crashed_cursor = ResearchRuntimeCursor.from_dict(
        crashed.research_context[CLAIM_ENGINE_RUNTIME_CONTEXT_KEY]
    )
    assert crashed_cursor.inflight_model_call is not None
    assert crashed_cursor.model_calls == ()

    recovered = service.execute(run.id, raise_on_error=True)

    assert recovered.status == "completed"
    cursor = ResearchRuntimeCursor.from_dict(
        recovered.research_context[CLAIM_ENGINE_RUNTIME_CONTEXT_KEY]
    )
    assert cursor.inflight_model_call is None
    assert any(item.code == "interrupted_unknown" for item in cursor.failures)
    planning_audits = [
        item
        for item in cursor.model_calls
        if item.logical_call_id.startswith("research_claim_plan")
    ]
    assert len(planning_audits) == 1
    assert planning_audits[0].status == "completed"
    assert planning_audits[0].attempt == 2
    assert planning_audits[0].call_id.endswith(":attempt:2")
    assert any(
        item.code == "interrupted_unknown"
        and item.item_id.endswith(":attempt:1")
        for item in cursor.failures
    )
    assert len({item.call_id for item in cursor.model_calls}) == len(cursor.model_calls)


def test_crash_after_extraction_preserves_wave_baseline_and_gain(tmp_path: Any) -> None:
    class _CrashAfterExtractionRepository(_TrackingRepository):
        def __init__(self, database: RuntimeDatabase) -> None:
            super().__init__(database)
            self.crashed = False

        def checkpoint(self, run_id: str, **kwargs: Any) -> WebLookupRun:
            persisted = super().checkpoint(run_id, **kwargs)
            if self.crashed:
                return persisted
            has_eligible_extraction = any(
                isinstance(record.get("extractions"), dict)
                and any(
                    isinstance(detail, dict) and detail.get("status") == "eligible"
                    for detail in record["extractions"].values()
                )
                for record in kwargs["selected_sources"]
            )
            cursor = ResearchRuntimeCursor.from_dict(
                persisted.research_context[CLAIM_ENGINE_RUNTIME_CONTEXT_KEY]
            )
            if has_eligible_extraction and not cursor.gain_history:
                self.crashed = True
                assert persisted.active_operation_id
                self.fail(
                    run_id,
                    "simulated crash after extraction",
                    operation_id=persisted.active_operation_id,
                )
                raise RuntimeError("simulated crash after extraction")
            return persisted

    repository = _CrashAfterExtractionRepository(
        RuntimeDatabase(tmp_path / "active-extraction-crash.sqlite")
    )
    run = repository.create(
        WebLookupRun(
            id="run_active_extraction_crash",
            query="What is the verified current release date?",
            stage="planned",
            status="pending",
            research_context=_active_context(),
            max_items=5,
        )
    )
    client = _StructuredClient()
    search = _SearchBackend()
    reader = _ReadGateway()
    service = _service(
        repository,
        client,
        search_backend=search,
        read_gateway=reader,
    )

    with pytest.raises(RuntimeError, match="simulated crash after extraction"):
        service.execute(run.id, raise_on_error=True)

    crashed = repository.get(run.id)
    assert crashed is not None
    baseline = crashed.research_context[ACTIVE_RESEARCH_WAVE_BASELINE_KEY]
    assert baseline["evidence"] == []
    crashed_state = _dispatch_state(crashed)
    assert crashed_state is not None
    assert len(crashed_state.evidence) == 1
    crashed_cursor = ResearchRuntimeCursor.from_dict(
        crashed.research_context[CLAIM_ENGINE_RUNTIME_CONTEXT_KEY]
    )
    assert crashed_cursor.wave_index == 1
    assert crashed_cursor.wave_id == f"research_wave:{run.id}:1"
    assert crashed_cursor.gain_history == ()
    search_calls = search.calls
    read_calls = reader.calls

    recovered = service.execute(run.id, raise_on_error=True)

    assert recovered.status == "completed"
    cursor = ResearchRuntimeCursor.from_dict(
        recovered.research_context[CLAIM_ENGINE_RUNTIME_CONTEXT_KEY]
    )
    assert len(cursor.gain_history) == 1
    assert cursor.gain_history[0]["substantive_gain"] is True
    assert "new_eligible_evidence" in cursor.gain_history[0]["gain_reasons"]
    assert search.calls == search_calls
    assert reader.calls == read_calls
    assert len({item.id for item in cursor.planned_queries}) == len(
        cursor.planned_queries
    )


def test_full_candidate_pool_stops_pending_external_searches(tmp_path: Any) -> None:
    """B5-H2: a full candidate pool must stop pending external searches.

    The first query fills the pool to its frozen cap (20); the second planned
    query would only burn shared budget on results the pool would drop, so it
    must be skipped before any external call is issued.
    """
    repository = _TrackingRepository(RuntimeDatabase(tmp_path / "active_flood.sqlite"))
    run = repository.create(
        WebLookupRun(
            id="run_active_flood_pool",
            query="What is the verified current release date?",
            stage="planned",
            status="pending",
            research_context=_active_context(),
            max_items=5,
        )
    )
    client = _StructuredClient()
    search = _FloodSearchBackend()

    completed = _service(repository, client, search_backend=search).execute(
        run.id,
        raise_on_error=True,
    )

    # The flood data collapses into a single candidate cluster, so the gate
    # legitimately settles partial; the H2 assertions are the search stop and
    # the pool cap, not the gate outcome.
    assert completed.status == "partial"
    assert completed.stop_reason == "evidence_saturated"
    assert search.calls == 1
    cursor = ResearchRuntimeCursor.from_dict(
        completed.research_context[CLAIM_ENGINE_RUNTIME_CONTEXT_KEY]
    )
    assert len(cursor.candidates) == 20
    assert len(cursor.completed_query_ids) == 1


def test_one_physical_read_serves_multiple_claims(tmp_path: Any) -> None:
    """B5-H3: deduplicate reads, not claim-evidence bindings.

    Claim A and claim B queries both discover shared.example/source; the
    candidate's provenance merges (query_ids from both claims) and the source
    must be read once while evidence is extracted for both claims.
    """
    repository = _TrackingRepository(RuntimeDatabase(tmp_path / "active_multiclaim.sqlite"))
    run = repository.create(
        WebLookupRun(
            id="run_active_multiclaim_read",
            query="What is the verified current release date?",
            stage="planned",
            status="pending",
            research_context=_active_context(),
            max_items=5,
        )
    )
    client = _StructuredClient(claims_count=2)
    search = _ProvenanceSearchBackend()

    completed = _service(repository, client, search_backend=search).execute(
        run.id,
        raise_on_error=True,
    )

    cursor = ResearchRuntimeCursor.from_dict(
        completed.research_context[CLAIM_ENGINE_RUNTIME_CONTEXT_KEY]
    )
    queries_by_claim: dict[str, set[str]] = {}
    for query in cursor.planned_queries:
        queries_by_claim.setdefault(query.claim_id, set()).add(query.id)
    assert len(queries_by_claim) == 2

    shared = next(
        item for item in cursor.candidates if item.url == "https://shared.example/source"
    )
    # Provenance merge: the shared candidate carries query ids from both claims.
    assert all(
        queries_by_claim[claim_id] & set(shared.query_ids)
        for claim_id in queries_by_claim
    )

    # Exactly one physical read for the shared source.
    shared_reads = [
        outcome for outcome in cursor.read_outcomes if outcome.candidate_id == shared.id
    ]
    assert len(shared_reads) == 1
    assert shared_reads[0].status == "success"
    shared_evidence_id = shared_reads[0].evidence_id
    assert shared_evidence_id

    # Extraction targets: (shared, claimA) and (shared, claimB), bound once each.
    plan = completed.research_context[ACTIVE_RESEARCH_READ_PLAN_KEY]
    shared_targets = [
        item for item in plan["extraction_targets"] if item["candidate_id"] == shared.id
    ]
    assert len(shared_targets) == 2
    assert {item["claim_id"] for item in shared_targets} == set(queries_by_claim)
    shared_physical = [
        item for item in plan["physical_reads"] if item["candidate_id"] == shared.id
    ]
    assert len(shared_physical) == 1

    # One server-owned evidence identity, linked from both claims.
    persisted = repository.get(run.id)
    assert persisted is not None
    state = _dispatch_state(persisted)
    assert state is not None
    links = [
        link for link in state.evidence_links if link.evidence_id == shared_evidence_id
    ]
    assert {link.claim_id for link in links} == set(queries_by_claim)

    record = next(
        item
        for item in completed.selected_sources
        if item["candidate_id"] == shared.id
    )
    assert set((record.get("extractions") or {})) == set(queries_by_claim)

    # H7: each claim row keeps its own anchor on the shared evidence.
    brief_rows = completed.research_context[ACTIVE_RESEARCH_BRIEF_KEY][
        "eligible_evidence"
    ]
    rows_by_claim = {
        row["claim_id"]: row
        for row in brief_rows
        if row["evidence_id"] == shared_evidence_id
    }
    assert len(rows_by_claim) == 2
    state = _dispatch_state(repository.get(run.id))
    assert state is not None
    anchors = {}
    for claim in state.claims:
        row = rows_by_claim[claim.id]
        if "official project" in claim.text:
            assert row["locator"] == "2026-08-01"
            assert row["anchored_spans"] == ["2026-08-01"]
            anchors[claim.id] = (row["locator"], tuple(row["anchored_spans"]))
        else:
            assert row["locator"] == "release date"
            assert row["anchored_spans"] == ["release date"]
            anchors[claim.id] = (row["locator"], tuple(row["anchored_spans"]))
    assert len(set(anchors.values())) == 2


def test_active_cancel_during_claim_planning_settles_durably(tmp_path: Any) -> None:
    repository = WebLookupRepository(RuntimeDatabase(tmp_path / "cancel-model.sqlite"))
    run = repository.create(
        WebLookupRun(
            id="run_cancel_model",
            query="Research this",
            stage="planned",
            status="pending",
            research_context=_active_context(),
        )
    )
    client = _StructuredClient(on_call=lambda _index: repository.request_cancel(run.id))

    cancelled = _service(repository, client).execute(run.id, raise_on_error=True)

    _assert_cancelled(cancelled)


def test_active_cancel_during_search_settles_durably(tmp_path: Any) -> None:
    repository = WebLookupRepository(RuntimeDatabase(tmp_path / "cancel-search.sqlite"))
    run = repository.create(
        WebLookupRun(
            id="run_cancel_search",
            query="Research this",
            stage="planned",
            status="pending",
            research_context=_active_context(),
        )
    )

    class CancellingSearch(_SearchBackend):
        def search_exact(self, query: str, *, max_results: int = 5) -> dict[str, Any]:
            repository.request_cancel(run.id)
            return super().search_exact(query, max_results=max_results)

    cancelled = _service(
        repository,
        _StructuredClient(),
        search_backend=CancellingSearch(),
    ).execute(run.id, raise_on_error=True)

    _assert_cancelled(cancelled)


def test_active_cancel_during_read_settles_durably(tmp_path: Any) -> None:
    repository = WebLookupRepository(RuntimeDatabase(tmp_path / "cancel-read.sqlite"))
    run = repository.create(
        WebLookupRun(
            id="run_cancel_read",
            query="Research this",
            stage="planned",
            status="pending",
            research_context=_active_context(),
        )
    )
    reader = _ReadGateway(on_read=lambda: repository.request_cancel(run.id))

    cancelled = _service(
        repository,
        _StructuredClient(),
        read_gateway=reader,
    ).execute(run.id, raise_on_error=True)

    _assert_cancelled(cancelled)


def test_active_cancel_during_extraction_settles_durably(tmp_path: Any) -> None:
    repository = WebLookupRepository(RuntimeDatabase(tmp_path / "cancel-extract.sqlite"))
    run = repository.create(
        WebLookupRun(
            id="run_cancel_extract",
            query="Research this",
            stage="planned",
            status="pending",
            research_context=_active_context(),
        )
    )
    client = _StructuredClient(
        on_call=lambda index: repository.request_cancel(run.id) if index == 3 else None
    )

    cancelled = _service(repository, client).execute(run.id, raise_on_error=True)

    _assert_cancelled(cancelled)


def _assert_cancelled(run: WebLookupRun) -> None:
    assert run.status == "cancelled"
    assert run.stage == "cancelled"
    assert run.stop_reason == "user_cancelled"
    runtime = run.research_context["claim_engine_runtime"]
    assert runtime["inflight_model_call"] is None
    assert runtime["inflight_external_call"] is None


@pytest.mark.parametrize(
    ("blocked_stage", "declared_timeout_seconds"),
    [("model", 20.0), ("provider", 8.0), ("reader", 10.0)],
)
def test_slow_active_stage_cancel_settles_within_call_timeout_plus_one(
    tmp_path: Any,
    blocked_stage: str,
    declared_timeout_seconds: float,
) -> None:
    repository = WebLookupRepository(
        RuntimeDatabase(tmp_path / f"slow-{blocked_stage}.sqlite")
    )
    run = repository.create(
        WebLookupRun(
            id=f"run_slow_{blocked_stage}",
            query="Research this",
            stage="planned",
            status="pending",
            research_context=_active_context(),
        )
    )
    entered = Event()
    release = Event()

    def block() -> None:
        entered.set()
        assert release.wait(timeout=2.0)

    client = _StructuredClient(
        on_call=(lambda index: block() if blocked_stage == "model" and index == 1 else None)
    )

    class BlockingSearch(_SearchBackend):
        def search_exact(self, query: str, *, max_results: int = 5) -> dict[str, Any]:
            if blocked_stage == "provider":
                block()
            return super().search_exact(query, max_results=max_results)

    reader = _ReadGateway(on_read=block if blocked_stage == "reader" else None)
    service = _service(
        repository,
        client,
        search_backend=BlockingSearch(),
        read_gateway=reader,
    )
    results: list[WebLookupRun] = []
    worker = Thread(
        target=lambda: results.append(service.execute(run.id, raise_on_error=True)),
        daemon=True,
    )
    worker.start()
    assert entered.wait(timeout=3.0)

    registered_at = perf_counter()
    repository.request_cancel(run.id)
    assert not release.wait(timeout=0.12)
    release.set()
    worker.join(timeout=3.0)
    settle_seconds = perf_counter() - registered_at

    assert not worker.is_alive()
    assert len(results) == 1
    _assert_cancelled(results[0])
    assert settle_seconds <= declared_timeout_seconds + 1.0
    print(
        f"B5_SLOW_CANCEL stage={blocked_stage} "
        f"settle_seconds={settle_seconds:.3f} "
        f"bound_seconds={declared_timeout_seconds + 1.0:.1f}"
    )

def test_read_plan_cluster_diversity_spans_reusable_and_fresh() -> None:
    """B5-H8: fresh selections must skip clusters the claim already covers.

    Wave 1 binds the reusable shared candidate (cluster X) to claim_B; wave 2
    must skip the fresh same-cluster candidate Q without wasting the slot, and
    still take R (cluster Y).
    """
    from src.application.active_research_runtime import _fair_read_plan
    from src.web.research.candidate_assessment import CandidateSemanticAssessment
    from src.web.research.candidate_pool import CandidatePoolItem
    from src.web.research.candidate_ranking import RankedCandidate
    from src.web.research.contracts import (
        EvidenceRequirement,
        ResearchClaim,
        ResearchQuestion,
    )

    question = ResearchQuestion(id="q1", question_surface="question")
    question_tuple = (question,)

    def claim(claim_id: str) -> ResearchClaim:
        return ResearchClaim(
            id=claim_id,
            question_id="q1",
            text="claim",
            kind="factual",
            priority="critical",
            state="pending",
            evidence_requirement=EvidenceRequirement(),
        )

    def ranked(candidate_id: str, cluster_id: str, rank: int) -> RankedCandidate:
        candidate = CandidatePoolItem(
            id=candidate_id,
            canonical_url=f"https://x.example/{candidate_id}",
            url=f"https://x.example/{candidate_id}",
            title=candidate_id,
            snippet="",
            source="",
            published_at="",
            query_ids=("q1",),
            intents=(),
            providers=("searxng",),
            first_seen_rank=rank,
        )
        assessment = CandidateSemanticAssessment(
            candidate_id=candidate_id,
            relevance="answer_relevant",
            relevance_confidence=0.9,
            source_role="primary",
            source_role_confidence=0.9,
            cluster_id=cluster_id,
            expected_gain_signals=("new_primary",),
            freshness_score=0.5,
            estimated_read_cost=1.0,
        )
        return RankedCandidate(
            candidate=candidate,
            assessment=assessment,
            rank=rank,
            eligibility="eligible",
            reason_codes=(),
            new_cluster=False,
            expected_information_gain=1,
        )

    state = build_research_state(
        mode="active",
        questions=question_tuple,
        claims=(claim("claim_A"), claim("claim_B")),
        evidence=(),
        evidence_links=(),
        source_clusters=(),
        gaps=(),
        conflict_gaps=(),
        budget=ResearchBudget(
            max_candidates=20,
            max_reads=8,
            soft_timeout_seconds=45,
            hard_timeout_seconds=60,
            max_total_chars=16000,
        ),
        reference_date="2026-08-28",
        known_evidence_ids=(),
    )
    rankings = {
        "claim_A": (ranked("P", "cluster_X", 1),),
        "claim_B": (
            ranked("P", "cluster_X", 1),
            ranked("Q", "cluster_X", 2),
            ranked("R", "cluster_Y", 3),
        ),
    }

    physical, targets = _fair_read_plan(state, rankings)

    b_pairs = {
        (item["candidate_id"], item["cluster_id"])
        for item in targets
        if item["claim_id"] == "claim_B"
    }
    assert ("P", "cluster_X") in b_pairs
    # H8: Q shares cluster X with the already-bound P, so it must be skipped
    # while R (cluster Y) still fills the slot.
    assert ("Q", "cluster_X") not in b_pairs
    assert ("R", "cluster_Y") in b_pairs
    assert "Q" not in {item["candidate_id"] for item in physical}


def _load_smoke_module() -> Any:
    import importlib.util

    path = Path(__file__).resolve().parents[1] / "tools" / "run_research_active_smoke.py"
    spec = importlib.util.spec_from_file_location("run_research_active_smoke", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_smoke_searxng_success_requires_ok_results() -> None:
    """B5-H6: attempted is not success; only a successful result-bearing
    searxng outcome proves the real-SearXNG smoke ran against SearXNG."""
    module = _load_smoke_module()

    success = [
        {
            "provider_audit": {
                "provider_outcomes": [
                    {"provider": "searxng", "status": "ok", "result_count": 3}
                ]
            }
        }
    ]
    assert module._searxng_success(success) is True

    failed_but_attempted = [
        {
            "provider_audit": {
                "provider_outcomes": [
                    {"provider": "searxng", "status": "failed", "result_count": 0},
                    {"provider": "bing_rss", "status": "ok", "result_count": 5},
                ]
            }
        }
    ]
    assert module._searxng_success(failed_but_attempted) is False

    ok_but_empty = [
        {
            "provider_audit": {
                "provider_outcomes": [
                    {"provider": "searxng", "status": "ok", "result_count": 0}
                ]
            }
        }
    ]
    assert module._searxng_success(ok_but_empty) is False

def test_reusable_candidates_obey_scheduler_eligibility() -> None:
    """B5-H9: reusable candidates obey the same eligibility predicate as fresh.

    Claim B ranks the already-read shared candidate X as lead_only without any
    provenance-grade gain signal: it must not be bound to claim B even though
    its physical read exists, while a legitimate fresh Y is still selected and
    a lead_only candidate carrying a gain signal (Z) is not rejected.
    """
    from src.application.active_research_runtime import _fair_read_plan
    from src.web.research.candidate_assessment import CandidateSemanticAssessment
    from src.web.research.candidate_pool import CandidatePoolItem
    from src.web.research.candidate_ranking import RankedCandidate
    from src.web.research.contracts import (
        EvidenceRequirement,
        ResearchClaim,
        ResearchQuestion,
    )

    question = ResearchQuestion(id="q1", question_surface="question")

    def claim(claim_id: str) -> ResearchClaim:
        return ResearchClaim(
            id=claim_id,
            question_id="q1",
            text="claim",
            kind="factual",
            priority="critical",
            state="pending",
            evidence_requirement=EvidenceRequirement(),
        )

    def ranked(
        candidate_id: str,
        cluster_id: str,
        rank: int,
        *,
        eligibility: str = "eligible",
        signals: tuple[str, ...] = ("new_primary",),
    ) -> RankedCandidate:
        candidate = CandidatePoolItem(
            id=candidate_id,
            canonical_url=f"https://x.example/{candidate_id}",
            url=f"https://x.example/{candidate_id}",
            title=candidate_id,
            snippet="",
            source="",
            published_at="",
            query_ids=("q1",),
            intents=(),
            providers=("searxng",),
            first_seen_rank=rank,
        )
        assessment = CandidateSemanticAssessment(
            candidate_id=candidate_id,
            relevance="answer_relevant",
            relevance_confidence=0.9,
            source_role="primary",
            source_role_confidence=0.9,
            cluster_id=cluster_id,
            expected_gain_signals=signals,
            freshness_score=0.5,
            estimated_read_cost=1.0,
        )
        return RankedCandidate(
            candidate=candidate,
            assessment=assessment,
            rank=rank,
            eligibility=eligibility,
            reason_codes=(),
            new_cluster=False,
            expected_information_gain=1,
        )

    state = build_research_state(
        mode="active",
        questions=(question,),
        claims=(claim("claim_A"), claim("claim_B")),
        evidence=(),
        evidence_links=(),
        source_clusters=(),
        gaps=(),
        conflict_gaps=(),
        budget=ResearchBudget(
            max_candidates=20,
            max_reads=8,
            soft_timeout_seconds=45,
            hard_timeout_seconds=60,
            max_total_chars=16000,
        ),
        reference_date="2026-08-28",
        known_evidence_ids=(),
    )
    rankings = {
        "claim_A": (ranked("X", "cluster_X", 1),),
        "claim_B": (
            ranked("X", "cluster_X", 1, eligibility="lead_only", signals=()),
            ranked("Y", "cluster_Y", 2),
            ranked("Z", "cluster_Z", 3, eligibility="lead_only", signals=("new_primary",)),
        ),
    }

    physical, targets = _fair_read_plan(state, rankings)

    b_pairs = {
        (item["candidate_id"], item["cluster_id"])
        for item in targets
        if item["claim_id"] == "claim_B"
    }
    # H9: X is lead_only without gain signals, so it must not be bound to
    # claim B even though it was already physically read for claim A.
    assert ("X", "cluster_X") not in b_pairs
    # The legitimate fresh candidate fills the wave; lead_only with a gain
    # signal (Z) stays schedulable in the next wave.
    assert ("Y", "cluster_Y") in b_pairs
    assert ("Z", "cluster_Z") in b_pairs
    assert "X" not in {item["candidate_id"] for item in physical if item["claim_id"] == "claim_B"}


@pytest.mark.parametrize(
    ("eligibility", "signals"),
    [
        ("rejected", ()),
        ("lead_only", ()),
    ],
)
def test_restored_read_binding_rechecks_per_claim_eligibility(
    eligibility: str,
    signals: tuple[str, ...],
) -> None:
    from src.web.research.candidate_assessment import CandidateSemanticAssessment
    from src.web.research.candidate_pool import CandidatePoolItem
    from src.web.research.candidate_ranking import RankedCandidate

    candidate = CandidatePoolItem(
        id="shared",
        canonical_url="https://x.example/shared",
        url="https://x.example/shared",
        title="shared",
        snippet="",
        source="",
        published_at="",
        query_ids=("q1",),
        intents=(),
        providers=("searxng",),
        first_seen_rank=1,
    )

    def ranked(
        *,
        role: str,
        cluster: str,
        item_eligibility: str,
        item_signals: tuple[str, ...],
    ) -> RankedCandidate:
        return RankedCandidate(
            candidate=candidate,
            assessment=CandidateSemanticAssessment(
                candidate_id=candidate.id,
                relevance="answer_relevant",
                relevance_confidence=0.9,
                source_role=role,
                source_role_confidence=0.9,
                cluster_id=cluster,
                expected_gain_signals=item_signals,
                freshness_score=0.5,
                estimated_read_cost=1.0,
            ),
            rank=1,
            eligibility=item_eligibility,
            reason_codes=(),
            new_cluster=False,
            expected_information_gain=1,
        )

    restored = _restore_completed_read_targets(
        [],
        completed_read_ids={candidate.id},
        rankings={
            "claim_A": (
                ranked(
                    role="primary",
                    cluster="cluster_A",
                    item_eligibility="eligible",
                    item_signals=("new_primary",),
                ),
            ),
            "claim_B": (
                ranked(
                    role="community",
                    cluster="cluster_B",
                    item_eligibility=eligibility,
                    item_signals=signals,
                ),
            ),
        },
    )

    assert restored == [
        {
            "candidate_id": "shared",
            "claim_id": "claim_A",
            "cluster_id": "cluster_A",
            "source_role": "primary",
        }
    ]


def test_major_claim_saturates_after_two_no_gain_waves(tmp_path: Any) -> None:
    """Frozen rule: non-critical claims saturate after exactly two no-gain
    waves - the optional third batch is a critical/conflict privilege only."""
    question = ResearchQuestion(id="question_1", question_surface="Compare releases")
    requirement = EvidenceRequirement(
        source_roles=("primary", "independent_secondary"),
        min_independent_sources=2,
        requires_primary_source=True,
    )
    claim = ResearchClaim(
        id="claim_major",
        question_id=question.id,
        text="Alpha framework current release",
        kind="factual",
        priority="major",
        state="searching",
        evidence_requirement=requirement,
    )
    gap = EvidenceGap(
        id="gap_major",
        claim_id=claim.id,
        gap_type="missing_evidence",
        desired_source_role="primary",
        priority="major",
        state="open",
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
        budget=ResearchBudget(
            max_candidates=20,
            max_reads=8,
            soft_timeout_seconds=45,
            hard_timeout_seconds=60,
            max_total_chars=16000,
        ),
        reference_date="2026-08-28",
        known_evidence_ids=(),
    )
    context = attach_claim_engine_state(_active_context(), state, known_evidence_ids=())
    repository = _TrackingRepository(RuntimeDatabase(tmp_path / "active-major.sqlite"))
    run = repository.create(
        WebLookupRun(
            id="run_active_major_saturation",
            query="Alpha framework current release",
            stage="planned",
            status="pending",
            research_context=context,
            max_items=5,
        )
    )
    search = _EmptySearchBackend()
    client = _StructuredClient()

    completed = _service(repository, client, search_backend=search).execute(
        run.id,
        raise_on_error=True,
    )

    assert completed.status == "partial"
    assert completed.stop_reason == "evidence_saturated"
    cursor = ResearchRuntimeCursor.from_dict(
        completed.research_context[CLAIM_ENGINE_RUNTIME_CONTEXT_KEY]
    )
    assert cursor.wave_index == 2
    assert cursor.no_gain_batches_by_claim == {"claim_major": 2}
    assert cursor.no_gain_batches_by_gap == {"gap_major": 2}
    assert len(cursor.gain_history) == 2


def test_deferred_context_gap_does_not_block_critical_saturation(tmp_path: Any) -> None:
    question = ResearchQuestion(id="question_1", question_surface="Compare releases")
    requirement = EvidenceRequirement(
        source_roles=("primary", "independent_secondary"),
        min_independent_sources=2,
        requires_primary_source=True,
    )
    critical = ResearchClaim(
        id="claim_critical",
        question_id=question.id,
        text="Alpha framework current release",
        kind="factual",
        priority="critical",
        state="searching",
        evidence_requirement=requirement,
    )
    context_claim = ResearchClaim(
        id="claim_context",
        question_id=question.id,
        text="Historical background",
        kind="factual",
        priority="context",
        state="searching",
        evidence_requirement=requirement,
    )
    gaps = (
        EvidenceGap(
            id="gap_critical",
            claim_id=critical.id,
            gap_type="missing_evidence",
            desired_source_role="primary",
            priority="critical",
            state="open",
        ),
        EvidenceGap(
            id="gap_context",
            claim_id=context_claim.id,
            gap_type="missing_context",
            desired_source_role="independent_secondary",
            priority="context",
            state="open",
        ),
    )
    state = build_research_state(
        mode="active",
        questions=(question,),
        claims=(critical, context_claim),
        evidence=(),
        evidence_links=(),
        source_clusters=(),
        gaps=gaps,
        conflict_gaps=(),
        budget=ResearchBudget(
            max_candidates=20,
            max_reads=8,
            soft_timeout_seconds=45,
            hard_timeout_seconds=60,
            max_total_chars=16000,
        ),
        reference_date="2026-08-30",
        known_evidence_ids=(),
    )
    context = attach_claim_engine_state(_active_context(), state, known_evidence_ids=())
    repository = _TrackingRepository(RuntimeDatabase(tmp_path / "active-context-gap.sqlite"))
    run = repository.create(
        WebLookupRun(
            id="run_active_context_gap_saturation",
            query="Alpha framework current release",
            stage="planned",
            status="pending",
            research_context=context,
            max_items=5,
        )
    )
    search = _EmptySearchBackend()

    completed = _service(
        repository,
        _StructuredClient(),
        search_backend=search,
    ).execute(run.id, raise_on_error=True)

    assert completed.status == "partial"
    assert completed.stop_reason == "evidence_saturated"
    cursor = ResearchRuntimeCursor.from_dict(
        completed.research_context[CLAIM_ENGINE_RUNTIME_CONTEXT_KEY]
    )
    assert cursor.wave_index == 3
    assert cursor.no_gain_batches_by_claim == {"claim_critical": 3}
    assert cursor.no_gain_batches_by_gap == {"gap_critical": 3}
    assert cursor.active_gap_ids == ("gap_critical",)
    final_state = _dispatch_state(completed)
    assert final_state is not None
    deferred = next(gap for gap in final_state.gaps if gap.id == "gap_context")
    assert deferred.state == "open"


def test_wave_limit_exhausted_is_not_fake_saturation(tmp_path: Any) -> None:
    """P1: hitting the MAX_RESEARCH_WAVES ceiling must persist the honest
    wave_limit_exhausted reason, never evidence_saturated or
    evidence_budget_exhausted (regression for the truth bug).

    The claim is critical (saturation threshold 3), so one no-gain wave leaves
    it unsaturated; monkeypatching MAX_RESEARCH_WAVES=1 forces the ceiling to
    terminate while the claim genuinely has no_gain_batches == 1.
    """
    import src.application.active_research_runtime as art_mod

    question = ResearchQuestion(id="question_1", question_surface="Compare releases")
    requirement = EvidenceRequirement(
        source_roles=("primary", "independent_secondary"),
        min_independent_sources=2,
        requires_primary_source=True,
    )
    claim = ResearchClaim(
        id="claim_wave_limit",
        question_id=question.id,
        text="Alpha framework current release",
        kind="factual",
        priority="critical",
        state="searching",
        evidence_requirement=requirement,
    )
    gap = EvidenceGap(
        id="gap_wave_limit",
        claim_id=claim.id,
        gap_type="missing_evidence",
        desired_source_role="primary",
        priority="critical",
        state="open",
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
        budget=ResearchBudget(
            max_candidates=20,
            max_reads=8,
            soft_timeout_seconds=45,
            hard_timeout_seconds=60,
            max_total_chars=16000,
        ),
        reference_date="2026-08-28",
        known_evidence_ids=(),
    )
    context = attach_claim_engine_state(_active_context(), state, known_evidence_ids=())
    repository = _TrackingRepository(RuntimeDatabase(tmp_path / "active-wavelimit.sqlite"))
    run = repository.create(
        WebLookupRun(
            id="run_active_wave_limit",
            query="Alpha framework current release",
            stage="planned",
            status="pending",
            research_context=context,
            max_items=5,
        )
    )
    search = _EmptySearchBackend()
    client = _StructuredClient()

    original_limit = art_mod.MAX_RESEARCH_WAVES
    art_mod.MAX_RESEARCH_WAVES = 1
    try:
        completed = _service(repository, client, search_backend=search).execute(
            run.id,
            raise_on_error=True,
        )
    finally:
        art_mod.MAX_RESEARCH_WAVES = original_limit

    assert completed.status == "partial"
    assert completed.stop_reason == "wave_limit_exhausted"
    assert completed.stop_reason != "evidence_saturated"
    assert completed.stop_reason != "evidence_budget_exhausted"
    assert completed.answer_confidence == "none"  # empty evidence
    cursor = ResearchRuntimeCursor.from_dict(
        completed.research_context[CLAIM_ENGINE_RUNTIME_CONTEXT_KEY]
    )
    assert cursor.wave_index == 1
    assert cursor.no_gain_batches_by_claim == {"claim_wave_limit": 1}
    from src.web.research.evidence_gain import SaturationState, saturated_claim_ids

    assert "claim_wave_limit" not in saturated_claim_ids(
        SaturationState(no_gain_batches_by_claim=dict(cursor.no_gain_batches_by_claim))
    )

def test_resume_restores_missing_claim_binding_after_extraction_crash(
    tmp_path: Any,
) -> None:
    """P1-C batch 2: a shared source read once for two claims, with claim A's
    extraction completed and claim B's crashed, must restore the (candidate,
    claim B) binding on resume - never drop it because the candidate's
    physical read already completed."""
    repository = _TrackingRepository(RuntimeDatabase(tmp_path / "active-multiclaim-crash.sqlite"))
    run = repository.create(
        WebLookupRun(
            id="run_active_multiclaim_crash",
            query="What is the verified current release date?",
            stage="planned",
            status="pending",
            research_context=_active_context(),
            max_items=5,
        )
    )

    class _CrashOnSecondExtraction:
        def __init__(self, inner: Any) -> None:
            self._inner = inner
            self.calls = 0

        def extract(self, **kwargs: Any) -> Any:
            self.calls += 1
            result = self._inner.extract(**kwargs)
            if self.calls == 2:
                raise RuntimeError("simulated extraction crash")
            return result

    from src.web.research.model_gateway import ResearchModelGateway as _RMG
    from src.web.research.active_semantics import RuntimeEvidenceExtractor as _REE

    crashing_model = _RMG(client=_StructuredClient(claims_count=2), model_name="test-model", timeout_seconds=20)
    crashing_extractor = _CrashOnSecondExtraction(_REE(crashing_model))

    def crashing_runtime_factory(
        repo: WebLookupRepository,
        gateway: ActiveResearchGateway,
    ) -> ActiveResearchRuntimeExecutor:
        return ActiveResearchRuntimeExecutor(
            repo,
            gateway,
            model_gateway=crashing_model,
            evidence_extractor=crashing_extractor,
        )

    service = ClaimEngineDispatchWebLookupService(
        repository,
        active_gateway_factory=lambda: ActiveResearchGateway(
            search_backend=_ProvenanceSearchBackend(),
            read_gateway=_ReadGateway(),
        ),
        active_runtime_factory=crashing_runtime_factory,
    )

    with pytest.raises(RuntimeError, match="simulated extraction crash"):
        service.execute(run.id, raise_on_error=True)

    resumed_client = _StructuredClient(claims_count=2)
    resumed = _service(repository, resumed_client, search_backend=_ProvenanceSearchBackend()).execute(
        run.id, raise_on_error=True
    )

    assert resumed.status in {"completed", "partial"}
    state = _dispatch_state(repository.get(run.id))
    assert state is not None
    linked_claims = {link.claim_id for link in state.evidence_links}
    assert len(linked_claims) == 2
    shared_record = next(
        item
        for item in resumed.selected_sources
        if len((item.get("extractions") or {})) >= 2
    )
    assert set((shared_record.get("extractions") or {})) == linked_claims

    # Logical call identity must not drift across the crash/resume boundary:
    # the crashed extraction re-runs under the SAME logical_call_id with
    # attempt 2 (the wrapper crash lands in the executor exception fallback,
    # so the durable failure is the exception type rather than
    # interrupted_unknown; a process-level crash produces the inflight ->
    # interrupted_unknown path instead). Physical call ids stay unique.
    cursor = ResearchRuntimeCursor.from_dict(
        resumed.research_context[CLAIM_ENGINE_RUNTIME_CONTEXT_KEY]
    )
    extraction_calls = [
        call
        for call in cursor.model_calls
        if "research_evidence_extract" in call.logical_call_id
    ]
    attempts_by_logical: dict[str, list[int]] = {}
    for call in extraction_calls:
        attempts_by_logical.setdefault(call.logical_call_id, []).append(call.attempt)
    retried = [
        (logical, attempts)
        for logical, attempts in attempts_by_logical.items()
        if attempts == [1, 2]
    ]
    assert retried, f"expected an extraction retried as attempt 2: {attempts_by_logical}"
    assert len({call.call_id for call in cursor.model_calls}) == len(
        cursor.model_calls
    )

def test_assessment_identity_stable_across_crash_resume(tmp_path: Any) -> None:
    """P1-C batch 2: an assessment that crashes after the provider call but
    before the semantic result is durable must resume under the SAME logical
    call identity with attempt 2 (candidate fingerprint canonical)."""
    repository = _TrackingRepository(RuntimeDatabase(tmp_path / "active-assess-crash.sqlite"))
    run = repository.create(
        WebLookupRun(
            id="run_active_assess_crash",
            query="What is the verified current release date?",
            stage="planned",
            status="pending",
            research_context=_active_context(),
            max_items=5,
        )
    )

    class _CrashOnFirstAssessment:
        def __init__(self, inner: Any) -> None:
            self._inner = inner
            self.calls = 0

        def assess(self, **kwargs: Any) -> Any:
            self.calls += 1
            result = self._inner.assess(**kwargs)
            if self.calls == 1:
                raise RuntimeError("simulated assessment crash")
            return result

    from src.web.research.model_gateway import ResearchModelGateway as _RMG2
    from src.web.research.active_semantics import RuntimeCandidateAssessor as _RCA

    crashing_model = _RMG2(
        client=_StructuredClient(), model_name="test-model", timeout_seconds=20
    )
    crashing_assessor = _CrashOnFirstAssessment(_RCA(crashing_model))

    def crashing_runtime_factory(
        repo: WebLookupRepository,
        gateway: ActiveResearchGateway,
    ) -> ActiveResearchRuntimeExecutor:
        return ActiveResearchRuntimeExecutor(
            repo,
            gateway,
            model_gateway=crashing_model,
            candidate_assessor=crashing_assessor,
        )

    service = ClaimEngineDispatchWebLookupService(
        repository,
        active_gateway_factory=lambda: ActiveResearchGateway(
            search_backend=_SearchBackend(),
            read_gateway=_ReadGateway(),
        ),
        active_runtime_factory=crashing_runtime_factory,
    )

    with pytest.raises(RuntimeError, match="simulated assessment crash"):
        service.execute(run.id, raise_on_error=True)

    resumed = _service(repository, _StructuredClient()).execute(
        run.id,
        raise_on_error=True,
    )
    assert resumed.status in {"completed", "partial"}

    cursor = ResearchRuntimeCursor.from_dict(
        resumed.research_context[CLAIM_ENGINE_RUNTIME_CONTEXT_KEY]
    )
    assessment_calls = [
        call
        for call in cursor.model_calls
        if "research_candidate_assessment" in call.logical_call_id
    ]
    attempts_by_logical: dict[str, list[int]] = {}
    for call in assessment_calls:
        attempts_by_logical.setdefault(call.logical_call_id, []).append(call.attempt)
    retried = [
        attempts
        for attempts in attempts_by_logical.values()
        if attempts == [1, 2]
    ]
    assert retried, f"expected assessment retried as attempt 2: {attempts_by_logical}"
    assert len({call.call_id for call in cursor.model_calls}) == len(
        cursor.model_calls
    )

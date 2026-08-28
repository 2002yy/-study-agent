from __future__ import annotations

from json import loads
from types import SimpleNamespace
from collections.abc import Callable
from threading import Event, Thread
from time import perf_counter
from typing import Any

import pytest

from src.application.active_research_runtime import (
    ACTIVE_RESEARCH_BRIEF_KEY,
    ACTIVE_RESEARCH_METRICS_KEY,
    ACTIVE_RESEARCH_READ_PLAN_KEY,
    ActiveResearchRuntimeExecutor,
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
from src.web.research.contracts import ResearchBudget, build_research_state
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
                "locator": "Verified fact",
                "anchored_spans": ["Verified fact"],
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
    def search_exact(
        self,
        query: str,
        *,
        max_results: int = 5,
    ) -> dict[str, Any]:
        del query, max_results
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
    assert partial.stop_reason == "evidence_gap_open"
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
    assert resumed.stop_reason == "evidence_gap_open"
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
    assert planning_audits[0].attempt == 1
    assert len({item.call_id for item in cursor.model_calls}) == len(cursor.model_calls)


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
    assert completed.stop_reason == "evidence_budget_exhausted"
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

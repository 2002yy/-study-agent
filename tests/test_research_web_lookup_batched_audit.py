from __future__ import annotations

from typing import Any, cast

from src.application.research_web_lookup_dispatch import _AuditedRepositoryProxy
from src.domain.runtime_entities import WebLookupRun
from src.repositories.web_lookup_repository import WebLookupRepository
from src.web.research.active_adapter import ActiveResearchGateway


class _EmptyBackend:
    def __init__(self) -> None:
        self.calls = 0

    def search_exact(self, query: str, *, max_results: int = 5) -> dict[str, Any]:
        del query, max_results
        self.calls += 1
        return {
            "status": "empty",
            "reason": "providers_returned_no_results",
            "results": [],
            "providers_attempted": ["searxng"],
            "provider_errors": [],
            "provider_audits": [
                {
                    "provider": "searxng",
                    "attempt": 1,
                    "status": "empty",
                    "reason": "no_results",
                    "result_count": 0,
                    "elapsed_seconds": 0.01,
                    "query_sha256": str(self.calls) * 64,
                    "query_chars": self.calls,
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
            "searched_at": f"2026-08-27T00:00:0{self.calls}+00:00",
        }


class _RecordingRepository:
    def __init__(self) -> None:
        self.attempts: list[dict[str, Any]] = []

    def checkpoint(self, run_id: str, **kwargs: Any) -> WebLookupRun:
        self.attempts = [dict(item) for item in kwargs["query_attempts"]]
        return WebLookupRun(id=run_id)


def test_two_searches_before_one_checkpoint_keep_both_provider_audits() -> None:
    active = ActiveResearchGateway(search_backend=_EmptyBackend())
    repository = _RecordingRepository()
    proxy = _AuditedRepositoryProxy(
        cast(WebLookupRepository, repository),
        active,
        initial_attempt_count=1,
    )

    assert active.search("first", max_items=5) == []
    assert active.search("second", max_items=5) == []

    proxy.checkpoint(
        "run1",
        operation_id="op1",
        research_context={},
        query_attempts=[
            {"query": "existing", "status": "empty"},
            {"query": "first", "status": "empty"},
            {"query": "second", "status": "empty"},
        ],
        selected_sources=[],
        rejected_sources=[],
        items=[],
        warnings=[],
    )

    assert "provider_audit" not in repository.attempts[0]
    first = repository.attempts[1]["provider_audit"]
    second = repository.attempts[2]["provider_audit"]
    assert first["schema_version"] == "research-provider-audit-v1"
    assert second["schema_version"] == "research-provider-audit-v1"
    assert first["searched_at"] == "2026-08-27T00:00:01+00:00"
    assert second["searched_at"] == "2026-08-27T00:00:02+00:00"
    assert first["provider_audits"][0]["query_chars"] == 1
    assert second["provider_audits"][0]["query_chars"] == 2
    assert "query" not in first
    assert "results" not in first

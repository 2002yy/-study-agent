from __future__ import annotations

from src.application.web_lookup_service import WebLookupService
from src.infrastructure.sqlite.database import RuntimeDatabase
from src.repositories.web_lookup_repository import WebLookupRepository


class FakeResearchGateway:
    def __init__(self) -> None:
        self.search_calls: list[str] = []
        self.read_calls: list[str] = []

    def search(self, query: str, *, max_items: int = 10) -> list[dict]:
        self.search_calls.append(query)
        return [
            {
                "title": f"{query} official result",
                "url": "https://example.com/source",
                "link": "https://example.com/source",
                "source": "example.com",
                "snippet": f"Primary material about {query}",
                "search_excerpt": f"Primary material about {query}",
            }
        ][:max_items]

    def read(self, url: str, *, max_chars: int = 6000) -> dict:
        self.read_calls.append(url)
        return {
            "ok": True,
            "kind": "web_page",
            "url": url,
            "method": "fake_reader",
            "content": "verified source text"[:max_chars],
        }

    def warnings(self) -> list[dict[str, str]]:
        return []


def test_retry_clears_forward_compatible_terminal_reason_before_checkpoint(tmp_path):
    database = RuntimeDatabase(tmp_path / "runtime.db")
    repository = WebLookupRepository(database)
    gateway = FakeResearchGateway()
    service = WebLookupService(repository, gateway)
    planned = service.create("forward compatible retry", max_items=3)
    future_reason = "future_provider_specific_stop"

    with database.connect() as connection:
        connection.execute(
            """
            UPDATE web_lookup_runs
            SET stage = 'failed', status = 'failed',
                provider_status = 'provider_failed', stop_reason = ?,
                error = 'legacy provider detail', completed_at = updated_at
            WHERE id = ?
            """,
            (future_reason, planned.id),
        )

    readable = repository.get(planned.id)
    assert readable is not None
    assert readable.status == "failed"
    assert readable.stop_reason == future_reason

    retried = service.retry(planned.id)
    restored = repository.get(planned.id)

    assert retried.status == "completed"
    assert retried.stop_reason != future_reason
    assert retried.error == ""
    assert gateway.search_calls
    assert restored is not None
    assert restored.stop_reason == retried.stop_reason

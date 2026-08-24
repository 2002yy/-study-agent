"""G4 session paging and server-side search tests."""

from __future__ import annotations

from src.domain.runtime_entities import ChatTurn
from src.infrastructure.sqlite.database import RuntimeDatabase
from src.repositories.runtime_repository import RuntimeRepository
from src.application.session_service import SessionService


def _seed(repository: RuntimeRepository, thread_id: str, *, question: str = "") -> None:
    repository.ensure_chat_thread(thread_id)
    if question:
        repository.add_chat_turn(
            ChatTurn(
                id=f"turn_{thread_id}",
                thread_id=thread_id,
                user_message=question,
                assistant_message="answer",
                status="completed",
            )
        )


def test_paging_returns_older_sessions_beyond_first_window(tmp_path):
    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "runtime.db"))
    for index in range(7):
        _seed(repository, f"chat_g4_{index}")

    first_page = repository.list_chat_threads(limit=3, offset=0)
    second_page = repository.list_chat_threads(limit=3, offset=3)

    assert len(first_page) == 3
    assert len(second_page) == 3
    first_ids = {t.id for t in first_page}
    second_ids = {t.id for t in second_page}
    assert not first_ids & second_ids, "pages must not overlap"

    total = repository.count_chat_threads()
    assert total == 7
    assert len(repository.list_chat_threads(limit=100, offset=6)) == 1


def test_search_matches_manual_title_and_learning_state(tmp_path):
    from src.repositories.session_navigation_repository import (
        SessionNavigationRepository,
    )

    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "runtime.db"))
    navigation = SessionNavigationRepository(repository.database)
    _seed(repository, "chat_old_1", question="transformer 注意力机制")
    _seed(repository, "chat_old_2")
    navigation.set_manual_title("chat_old_2", "线性代数补课")

    # Manual title search reaches sessions outside any newest window.
    by_title = repository.list_chat_threads(limit=5, query="线性代数")
    assert [t.id for t in by_title] == ["chat_old_2"]
    # learning_state / turn content is NOT searched by design (title + id +
    # learning_state JSON); id search works.
    by_id = repository.list_chat_threads(limit=5, query="chat_old_1")
    assert [t.id for t in by_id] == ["chat_old_1"]

    assert repository.count_chat_threads(query="线性代数") == 1
    assert repository.count_chat_threads() == 2


def test_service_list_sessions_page_returns_rows_and_total(tmp_path):
    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "runtime.db"))
    for index in range(5):
        _seed(repository, f"chat_svc_{index}")
    service = SessionService(
        repository,
        current_dir=tmp_path / "current",
        archive_dir=tmp_path / "archive",
    )

    rows, total = service.list_sessions_page(limit=2)
    assert total == 5
    assert len(rows) == 2

    rows_q, total_q = service.list_sessions_page(limit=10, query="chat_svc")
    assert total_q == 5
    assert len(rows_q) == 5


def test_sessions_route_accepts_offset_and_query(tmp_path):
    from fastapi.testclient import TestClient

    from src.api.app import app as fastapi_app
    from src.application.runtime_repository import get_session_service

    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "route.db"))
    for index in range(4):
        _seed(repository, f"chat_route_{index}")
    service = SessionService(
        repository,
        current_dir=tmp_path / "current",
        archive_dir=tmp_path / "archive",
    )
    fastapi_app.dependency_overrides[get_session_service] = lambda: service
    try:
        client = TestClient(fastapi_app)
        page_one = client.get("/sessions?limit=2&offset=0").json()
        page_two = client.get("/sessions?limit=2&offset=2").json()

        assert page_one["total"] == 4 and len(page_one["sessions"]) == 2
        assert page_two["total"] == 4 and len(page_two["sessions"]) == 2
        ids_one = {row.get("session_id") for row in page_one["sessions"]}
        ids_two = {row.get("session_id") for row in page_two["sessions"]}
        assert not ids_one & ids_two

        filtered = client.get("/sessions", params={"q": "chat_route_1"}).json()
        assert filtered["total"] == 1
        assert len(filtered["sessions"]) == 1
    finally:
        fastapi_app.dependency_overrides.pop(get_session_service, None)

"""Real-stack server variant for durable ResearchRun cancellation gates."""

from __future__ import annotations

from dataclasses import replace
import time
from typing import Any

from tools.real_stack_test_server import app, _real_stack_chat_service
from src.application.policy_chat_service import ExternalDataPolicyChatService
from src.application.runtime_repository import (
    get_chat_service,
    get_web_lookup_repository,
    get_web_lookup_service,
)
from src.application.web_lookup_service import WebLookupService
from src.tools.web_agent import WebToolTrace

RESEARCH_PREFIX = "请联网研究："


class SlowDeterministicResearchGateway:
    """Pause external boundaries so the browser can cancel a running run."""

    def search(self, query: str, *, max_items: int = 10) -> list[dict[str, Any]]:
        time.sleep(2.0)
        return [
            {
                "title": query,
                "url": "https://docs.python.org/3/tutorial/classes.html",
                "source": "Python documentation",
                "snippet": f"Deterministic research evidence for {query}",
            }
        ][:max_items]

    def read(self, url: str, *, max_chars: int = 6000) -> dict[str, Any]:
        time.sleep(0.08)
        content = (
            "Dependency injection keeps object construction outside the code that uses "
            "the dependency, so tests can replace the implementation explicitly."
        )
        return {
            "ok": True,
            "url": url,
            "content": content[:max_chars],
        }

    def warnings(self) -> list[dict[str, str]]:
        return []


def _real_stack_web_lookup_service() -> WebLookupService:
    return WebLookupService(
        get_web_lookup_repository(),
        SlowDeterministicResearchGateway(),
    )


def _resolve_deterministic_research(
    user_input: str,
    *,
    owner_thread_id: str | None = None,
    owner_turn_id: str | None = None,
    **_kwargs: Any,
) -> WebToolTrace:
    """Replace only explicit research planning and preserve other chat fixtures."""

    if not user_input.strip().startswith(RESEARCH_PREFIX):
        return WebToolTrace(enabled=False)

    service = _real_stack_web_lookup_service()
    run = service.create(
        user_input,
        owner_thread_id=owner_thread_id,
        owner_turn_id=owner_turn_id,
        run_kind="chat_tool_loop",
    )
    completed = service.execute(run.id, raise_on_error=False)
    calls: tuple[dict[str, Any], ...] = ()
    if completed.status == "completed" and completed.provider_status == "found":
        calls = (
            {
                "name": "web_search",
                "arguments": {"query": user_input},
                "result": {
                    "status": completed.status,
                    "items": completed.items,
                    "source_block": completed.source_block,
                },
            },
        )
    return WebToolTrace(
        calls=calls,
        error=completed.error,
        run_id=run.id,
    )


def _real_stack_research_chat_service() -> ExternalDataPolicyChatService:
    base = _real_stack_chat_service()
    return ExternalDataPolicyChatService(
        base.repository,
        replace(
            base.dependencies,
            resolve_web_tools=_resolve_deterministic_research,
        ),
    )


app.dependency_overrides[get_web_lookup_service] = _real_stack_web_lookup_service
app.dependency_overrides[get_chat_service] = _real_stack_research_chat_service

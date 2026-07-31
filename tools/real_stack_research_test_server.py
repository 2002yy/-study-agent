"""Real-stack server variant for durable ResearchRun cancellation gates."""

from __future__ import annotations

import time
from typing import Any

from tools.real_stack_test_server import app
from src.application.runtime_repository import (
    get_web_lookup_repository,
    get_web_lookup_service,
)
from src.application.web_lookup_service import WebLookupService


class SlowDeterministicResearchGateway:
    """Pause external boundaries so the browser can cancel a running run."""

    def search(self, query: str, *, max_items: int = 10) -> list[dict[str, Any]]:
        time.sleep(0.45)
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


app.dependency_overrides[get_web_lookup_service] = _real_stack_web_lookup_service

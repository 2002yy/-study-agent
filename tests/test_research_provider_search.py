from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import src.web.tool_gateway as tool_gateway
from src.web.research.provider_search import PROVIDER_ORDER, ResearchProviderSearch
from src.web.tool_gateway import GeneralWebGateway


class _Clock:
    def __init__(self) -> None:
        self.value = 10.0

    def __call__(self) -> float:
        self.value += 0.1
        return self.value


def _item(url: str, title: str, snippet: str = "") -> dict[str, str]:
    return {"url": url, "title": title, "snippet": snippet, "source": "fixture"}


def test_legacy_gateway_still_stops_after_first_nonempty_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tool_gateway, "searxng_enabled", lambda: True)
    monkeypatch.setattr(
        tool_gateway,
        "search_searxng",
        lambda *args, **kwargs: [
            {"title": "first", "link": "https://example.test/first"}
        ],
    )
    monkeypatch.setenv("WEB_ENABLE_BING_RSS", "1")
    monkeypatch.setenv("WEB_ENABLE_DUCKDUCKGO", "1")

    def must_not_run(*args: Any, **kwargs: Any) -> tuple[list[dict[str, str]], str]:
        raise AssertionError("legacy fallback ran after a non-empty provider")

    monkeypatch.setattr(
        GeneralWebGateway, "_search_bing_rss", staticmethod(must_not_run)
    )
    monkeypatch.setattr(
        GeneralWebGateway, "_search_duckduckgo", staticmethod(must_not_run)
    )

    payload = GeneralWebGateway().search_exact("query")
    assert payload["status"] == "ok"
    assert payload["providers_attempted"] == ["searxng"]


def test_research_search_runs_all_providers_and_merges_duplicate_provenance() -> None:
    calls: list[str] = []

    def call(provider: str, query: str, limit: int, timeout: float):
        calls.append(provider)
        if provider == "searxng":
            return [
                _item("https://example.test/shared?utm_source=x", "shared"),
                _item("https://example.test/searx", "searx"),
            ], ""
        if provider == "bing_rss":
            return [
                _item(
                    "https://example.test/shared",
                    "shared",
                    "richer duplicate snippet",
                )
            ], ""
        return [_item("https://example.test/ddg", "ddg")], ""

    payload = ResearchProviderSearch(
        provider_call=call,
        provider_enabled=lambda provider: True,
        monotonic=_Clock(),
        provider_timeout_seconds=4.0,
    ).search_exact("query", max_results=5)

    assert calls == list(PROVIDER_ORDER)
    assert payload["status"] == "ok"
    assert payload["providers_attempted"] == list(PROVIDER_ORDER)
    assert len(payload["provider_audits"]) == 3
    shared = next(
        item for item in payload["results"] if item["url"] == "https://example.test/shared"
    )
    assert shared["providers"] == ["searxng", "bing_rss"]
    assert shared["snippet"] == "richer duplicate snippet"


def test_transient_failure_retries_once_then_recovers() -> None:
    calls = 0

    def call(provider: str, query: str, limit: int, timeout: float):
        nonlocal calls
        calls += 1
        if calls == 1:
            return [], "bing_rss:TimeoutError:temporary"
        return [_item("https://example.test/recovered", "recovered")], ""

    payload = ResearchProviderSearch(
        provider_call=call,
        provider_enabled=lambda provider: provider == "bing_rss",
        monotonic=_Clock(),
    ).search_exact("query")

    assert calls == 2
    assert payload["status"] == "ok"
    assert [item["status"] for item in payload["provider_audits"]] == [
        "failed",
        "ok",
    ]
    assert payload["provider_audits"][0]["reason"] == "timeout"
    assert payload["provider_outcomes"][0]["attempts"] == 2


def test_empty_is_not_failure_and_is_not_retried() -> None:
    calls = 0

    def call(provider: str, query: str, limit: int, timeout: float):
        nonlocal calls
        calls += 1
        return [], "duckduckgo_html:empty_response"

    payload = ResearchProviderSearch(
        provider_call=call,
        provider_enabled=lambda provider: provider == "duckduckgo_html",
        monotonic=_Clock(),
    ).search_exact("query")

    assert calls == 1
    assert payload["status"] == "empty"
    assert payload["provider_errors"] == []


def test_mixed_failure_and_empty_is_partial_not_empty() -> None:
    def call(provider: str, query: str, limit: int, timeout: float):
        if provider == "bing_rss":
            return [], "bing_rss:http_status:403"
        return [], "duckduckgo_html:empty_response"

    payload = ResearchProviderSearch(
        provider_call=call,
        provider_enabled=lambda provider: provider in {"bing_rss", "duckduckgo_html"},
        monotonic=_Clock(),
    ).search_exact("query")

    assert payload["status"] == "partial"
    assert payload["provider_outcomes"][0]["status"] == "failed"
    assert payload["provider_outcomes"][0]["reason"] == "http_status:403"
    assert payload["provider_outcomes"][1]["status"] == "empty"


def test_all_failures_are_unavailable_without_retry_for_403() -> None:
    calls: list[str] = []

    def call(provider: str, query: str, limit: int, timeout: float):
        calls.append(provider)
        return [], f"{provider}:http_status:403"

    payload = ResearchProviderSearch(
        provider_call=call,
        provider_enabled=lambda provider: True,
        monotonic=_Clock(),
    ).search_exact("query")

    assert calls == list(PROVIDER_ORDER)
    assert payload["status"] == "unavailable"
    assert all(item["attempts"] == 1 for item in payload["provider_outcomes"])


def test_attempt_audit_is_bounded_and_excludes_result_text() -> None:
    marker = "PAGE-CONTENT-MARKER"

    def call(provider: str, query: str, limit: int, timeout: float):
        return [_item("https://example.test/page", "result", marker)], ""

    payload = ResearchProviderSearch(
        provider_call=call,
        provider_enabled=lambda provider: provider == "searxng",
        monotonic=_Clock(),
    ).search_exact("research query")

    audit_text = str(payload["provider_audits"])
    assert marker not in audit_text
    assert "research query" not in audit_text
    audit = payload["provider_audits"][0]
    assert audit["query_chars"] == len("research query")
    assert len(audit["query_sha256"]) == 64


def test_raw_provider_error_and_exception_messages_are_not_persisted() -> None:
    marker = "PRIVATE-QUERY-OR-URL-MARKER"
    calls = 0

    def call(provider: str, query: str, limit: int, timeout: float):
        nonlocal calls
        calls += 1
        if calls == 1:
            return [], f"bing_rss:TimeoutError:{marker}"
        raise TimeoutError(marker)

    payload = ResearchProviderSearch(
        provider_call=call,
        provider_enabled=lambda provider: provider == "bing_rss",
        monotonic=_Clock(),
    ).search_exact("query")

    assert calls == 2
    durable_text = str(
        {
            "provider_errors": payload["provider_errors"],
            "provider_audits": payload["provider_audits"],
            "provider_outcomes": payload["provider_outcomes"],
        }
    )
    assert marker not in durable_text
    assert payload["status"] == "unavailable"
    assert payload["provider_errors"] == ["bing_rss:timeout"]
    assert all(item["reason"] == "timeout" for item in payload["provider_audits"])


def test_b1_module_does_not_import_eval_code() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "web"
        / "research"
        / "provider_search.py"
    )
    assert "src.evals" not in path.read_text(encoding="utf-8")

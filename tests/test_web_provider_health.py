from __future__ import annotations

from src.web.provider_health import inspect_web_search_providers


def _provider(payload: dict[str, object], name: str) -> dict[str, object]:
    providers = payload["providers"]
    assert isinstance(providers, list)
    return next(item for item in providers if item["name"] == name)


def test_provider_health_reports_ready_searxng_without_exposing_credentials(monkeypatch):
    monkeypatch.setattr("src.web.provider_health.searxng_enabled", lambda: True)
    monkeypatch.setattr(
        "src.web.provider_health.searxng_base_url",
        lambda: "http://user:secret@127.0.0.1:8080/private",  # pragma: allowlist secret
    )
    monkeypatch.setattr(
        "src.web.provider_health.build_searxng_search_url",
        lambda *args, **kwargs: "http://127.0.0.1:8080/search?q=health",
    )
    monkeypatch.setattr(
        "src.web.provider_health.search_searxng",
        lambda *args, **kwargs: [{"title": "Study Agent", "link": "https://example.com"}],
    )
    monkeypatch.setattr(
        "src.web.provider_health._probe_searxng_service",
        lambda *args, **kwargs: (True, "healthz_ok"),
    )

    payload = inspect_web_search_providers()

    searxng = _provider(payload, "searxng")
    assert payload["status"] == "ready"
    assert searxng["reachable"] is True
    assert searxng["search_capable"] is True
    assert searxng["endpoint"] == "http://127.0.0.1:8080"
    assert "secret" not in str(payload)


def test_provider_health_reports_misconfigured_preferred_provider_and_fallbacks(monkeypatch):
    monkeypatch.setattr("src.web.provider_health.searxng_enabled", lambda: True)
    monkeypatch.setattr("src.web.provider_health.searxng_base_url", lambda: "")
    monkeypatch.setenv("WEB_ENABLE_BING_RSS", "true")
    monkeypatch.setenv("WEB_ENABLE_DUCKDUCKGO", "false")

    payload = inspect_web_search_providers()

    searxng = _provider(payload, "searxng")
    assert payload["status"] == "degraded"
    assert searxng["status"] == "misconfigured"
    assert searxng["reachable"] is None
    assert _provider(payload, "bing_rss")["status"] == "enabled"


def test_provider_health_structures_probe_failure_and_never_promotes_fallback(monkeypatch):
    monkeypatch.setattr("src.web.provider_health.searxng_enabled", lambda: True)
    monkeypatch.setattr(
        "src.web.provider_health.searxng_base_url", lambda: "http://127.0.0.1:8080"
    )
    monkeypatch.setattr(
        "src.web.provider_health.build_searxng_search_url",
        lambda *args, **kwargs: "http://127.0.0.1:8080/search?q=health",
    )
    monkeypatch.setattr("src.web.provider_health.search_searxng", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        "src.web.provider_health._probe_searxng_service",
        lambda *args, **kwargs: (False, "URLError: connection refused"),
    )
    monkeypatch.setattr(
        "src.web.provider_health.get_last_searxng_error",
        lambda: "URLError: connection refused",
    )

    payload = inspect_web_search_providers()

    searxng = _provider(payload, "searxng")
    assert payload["status"] == "degraded"
    assert searxng["status"] == "unavailable"
    assert searxng["reachable"] is False
    assert searxng["search_capable"] is False
    assert searxng["detail"] == "URLError: connection refused"
    assert _provider(payload, "bing_rss")["reachable"] is None


def test_provider_health_can_skip_network_probe(monkeypatch):
    monkeypatch.setattr("src.web.provider_health.searxng_enabled", lambda: True)
    monkeypatch.setattr(
        "src.web.provider_health.searxng_base_url", lambda: "http://127.0.0.1:8080"
    )
    monkeypatch.setattr(
        "src.web.provider_health.build_searxng_search_url",
        lambda *args, **kwargs: "http://127.0.0.1:8080/search?q=health",
    )

    payload = inspect_web_search_providers(probe=False)

    searxng = _provider(payload, "searxng")
    assert payload["probed"] is False
    assert searxng["status"] == "configured"
    assert searxng["reachable"] is None
    assert searxng["search_capable"] is None


def test_provider_health_does_not_raise_or_echo_malformed_endpoint(monkeypatch):
    monkeypatch.setattr("src.web.provider_health.searxng_enabled", lambda: True)
    monkeypatch.setattr(
        "src.web.provider_health.searxng_base_url",
        lambda: "http://user:secret@127.0.0.1:not-a-port/private",  # pragma: allowlist secret
    )
    monkeypatch.setattr(
        "src.web.provider_health.build_searxng_search_url", lambda *args, **kwargs: ""
    )

    payload = inspect_web_search_providers()

    searxng = _provider(payload, "searxng")
    assert searxng["status"] == "misconfigured"
    assert searxng["endpoint"] == ""
    assert "secret" not in str(payload)


def test_provider_health_distinguishes_reachable_service_from_failed_search(monkeypatch):
    monkeypatch.setattr("src.web.provider_health.searxng_enabled", lambda: True)
    monkeypatch.setattr(
        "src.web.provider_health.searxng_base_url", lambda: "http://127.0.0.1:8080"
    )
    monkeypatch.setattr(
        "src.web.provider_health.build_searxng_search_url",
        lambda *args, **kwargs: "http://127.0.0.1:8080/search?q=health",
    )
    monkeypatch.setattr(
        "src.web.provider_health._probe_searxng_service",
        lambda *args, **kwargs: (True, "healthz_ok"),
    )
    monkeypatch.setattr("src.web.provider_health.search_searxng", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        "src.web.provider_health.get_last_searxng_error", lambda: "TimeoutError: timed out"
    )

    payload = inspect_web_search_providers()

    searxng = _provider(payload, "searxng")
    assert payload["status"] == "degraded"
    assert searxng["status"] == "degraded"
    assert searxng["reachable"] is True
    assert searxng["search_capable"] is False

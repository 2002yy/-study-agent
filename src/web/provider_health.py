"""Read-only diagnostics for the configured web-search provider chain."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from src.news.search_sources.searxng_source import (
    build_searxng_search_url,
    get_last_searxng_error,
    search_searxng,
    searxng_base_url,
    searxng_enabled,
)


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _public_endpoint(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    try:
        parsed_port = parsed.port
    except ValueError:
        return ""
    port = f":{parsed_port}" if parsed_port else ""
    return f"{parsed.scheme}://{host}{port}"


def _probe_searxng_service(base_url: str, timeout_seconds: float) -> tuple[bool, str]:
    health_url = urljoin(base_url.rstrip("/") + "/", "healthz")
    try:
        with urlopen(
            Request(health_url, headers={"User-Agent": "StudyAgent/1.0"}),
            timeout=max(0.25, min(float(timeout_seconds), 2.0)),
        ) as response:
            status = int(getattr(response, "status", 200))
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    if status != 200:
        return False, f"healthz_http_{status}"
    return True, "healthz_ok"


def inspect_web_search_providers(
    *,
    probe: bool = True,
    timeout_seconds: float = 5.0,
) -> dict[str, object]:
    """Return bounded provider readiness without exposing credentials or queries."""

    searx_enabled = searxng_enabled()
    base_url = searxng_base_url()
    public_endpoint = _public_endpoint(base_url)
    search_url = (
        build_searxng_search_url(
            "Python documentation",
            base_url,
            max_results=1,
            categories=os.getenv("WEB_SEARXNG_CATEGORIES", "general"),
        )
        if searx_enabled and base_url
        else ""
    )
    searx_configured = bool(search_url)
    searx_reachable: bool | None = None
    searx_search_capable: bool | None = None
    if not searx_enabled:
        searx_status = "disabled"
        searx_detail = "provider_disabled"
    elif not searx_configured:
        searx_status = "misconfigured"
        searx_detail = "missing_or_unsafe_endpoint"
    elif not probe:
        searx_status = "configured"
        searx_detail = "probe_skipped"
    else:
        searx_reachable, service_detail = _probe_searxng_service(
            base_url, timeout_seconds
        )
        results = (
            search_searxng(
                "python",
                max_results=1,
                timeout=max(0.25, min(float(timeout_seconds), 5.0)),
                categories=os.getenv("WEB_SEARXNG_CATEGORIES", "general"),
            )
            if searx_reachable
            else []
        )
        if searx_reachable and results:
            searx_status = "ready"
            searx_search_capable = True
            searx_detail = "valid_results_returned"
        elif searx_reachable:
            searx_status = "degraded"
            searx_search_capable = False
            searx_detail = get_last_searxng_error() or "no_valid_results"
        else:
            searx_status = "unavailable"
            searx_search_capable = False
            searx_detail = service_detail

    bing_enabled = _env_flag("WEB_ENABLE_BING_RSS", True)
    duckduckgo_enabled = _env_flag("WEB_ENABLE_DUCKDUCKGO", True)
    fallback_enabled = bing_enabled or duckduckgo_enabled
    if searx_status == "ready":
        overall_status = "ready"
    elif fallback_enabled:
        overall_status = "degraded"
    else:
        overall_status = "unavailable"

    providers = [
        {
            "name": "searxng",
            "role": "preferred",
            "enabled": searx_enabled,
            "configured": searx_configured,
            "reachable": searx_reachable,
            "search_capable": searx_search_capable,
            "status": searx_status,
            "detail": searx_detail,
            "endpoint": public_endpoint,
        },
        {
            "name": "bing_rss",
            "role": "fallback",
            "enabled": bing_enabled,
            "configured": bing_enabled,
            "reachable": None,
            "search_capable": None,
            "status": "enabled" if bing_enabled else "disabled",
            "detail": "not_probed",
            "endpoint": "",
        },
        {
            "name": "duckduckgo_html",
            "role": "last_fallback",
            "enabled": duckduckgo_enabled,
            "configured": duckduckgo_enabled,
            "reachable": None,
            "search_capable": None,
            "status": "enabled" if duckduckgo_enabled else "disabled",
            "detail": "not_probed_challenge_prone",
            "endpoint": "",
        },
    ]
    return {
        "status": overall_status,
        "preferred_provider": "searxng",
        "probed": probe,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "providers": providers,
    }

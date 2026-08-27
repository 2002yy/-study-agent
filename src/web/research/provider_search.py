"""Research-only multi-provider search orchestration.

Legacy ``GeneralWebGateway.search_exact`` intentionally keeps its first-nonempty
provider semantics. Deep research needs a different policy: every enabled
provider is attempted, transient failures get at most one explicit retry, and
provider provenance is preserved without copying the underlying network
transports.

This module is not wired into ``WebLookupService`` yet. It is a bounded adapter
for the later active-runtime slice and imports no evaluation helpers.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import os
import time
from typing import Any, Literal, cast

from src.news.search_sources.searxng_source import (
    get_last_searxng_error,
    search_searxng,
    searxng_enabled,
)
from src.news.url_normalizer import canonicalize_url
from src.web.tool_gateway import GeneralWebGateway

ResearchSearchProvider = Literal["searxng", "bing_rss", "duckduckgo_html"]
ProviderAttemptStatus = Literal["ok", "empty", "failed"]
ProviderCall = Callable[
    [ResearchSearchProvider, str, int, float],
    tuple[list[Mapping[str, Any]], str],
]
ProviderEnabled = Callable[[ResearchSearchProvider], bool]

PROVIDER_ORDER: tuple[ResearchSearchProvider, ...] = (
    "searxng",
    "bing_rss",
    "duckduckgo_html",
)
DEFAULT_PROVIDER_TIMEOUT_SECONDS = 6.0
MAX_PROVIDER_TIMEOUT_SECONDS = 8.0
MAX_PROVIDER_ATTEMPTS = 2


@dataclass(frozen=True)
class ProviderAttemptAudit:
    provider: ResearchSearchProvider
    attempt: int
    status: ProviderAttemptStatus
    reason: str
    result_count: int
    elapsed_seconds: float
    query_sha256: str
    query_chars: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "attempt": self.attempt,
            "status": self.status,
            "reason": self.reason,
            "result_count": self.result_count,
            "elapsed_seconds": self.elapsed_seconds,
            "query_sha256": self.query_sha256,
            "query_chars": self.query_chars,
        }


@dataclass(frozen=True)
class ProviderFinalOutcome:
    provider: ResearchSearchProvider
    status: ProviderAttemptStatus
    reason: str
    attempts: int
    result_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "status": self.status,
            "reason": self.reason,
            "attempts": self.attempts,
            "result_count": self.result_count,
        }


class ResearchProviderSearch:
    """Attempt every enabled search provider under explicit retry policy."""

    def __init__(
        self,
        *,
        provider_call: ProviderCall | None = None,
        provider_enabled: ProviderEnabled | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        provider_timeout_seconds: float | None = None,
    ) -> None:
        self._provider_call = provider_call or _default_provider_call
        self._provider_enabled = provider_enabled or _default_provider_enabled
        self._monotonic = monotonic
        self._provider_timeout_seconds = _bounded_timeout(provider_timeout_seconds)

    def search_exact(
        self,
        query: str,
        *,
        max_results: int = 5,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Search one planned query across all enabled providers.

        The returned mapping intentionally resembles ``GeneralWebGateway`` so a
        later runtime slice can inject this method into CandidatePool without
        changing query planning. ``provider_audits`` is additional research
        telemetry and never contains result/page content or raw provider errors.
        """

        focused = " ".join(str(query or "").split())
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        current = current.astimezone(timezone.utc)
        limit = max(1, min(int(max_results), 12))
        if not focused:
            return _payload(
                status="invalid_query",
                reason="empty_query",
                query=focused,
                results=[],
                providers_attempted=(),
                provider_errors=(),
                provider_audits=(),
                provider_outcomes=(),
                searched_at=current.isoformat(),
            )

        enabled = tuple(
            provider for provider in PROVIDER_ORDER if self._provider_enabled(provider)
        )
        if not enabled:
            return _payload(
                status="unavailable",
                reason="no_search_provider_enabled",
                query=focused,
                results=[],
                providers_attempted=(),
                provider_errors=(),
                provider_audits=(),
                provider_outcomes=(),
                searched_at=current.isoformat(),
            )

        provider_results: dict[
            ResearchSearchProvider, tuple[Mapping[str, Any], ...]
        ] = {}
        audits: list[ProviderAttemptAudit] = []
        outcomes: list[ProviderFinalOutcome] = []
        provider_errors: list[str] = []
        query_digest = sha256(focused.encode("utf-8")).hexdigest()

        for provider in enabled:
            final_status: ProviderAttemptStatus = "failed"
            final_reason = "provider_error"
            final_results: tuple[Mapping[str, Any], ...] = ()
            attempts = 0
            for attempt in range(1, MAX_PROVIDER_ATTEMPTS + 1):
                attempts = attempt
                started = self._monotonic()
                try:
                    raw_results, error = self._provider_call(
                        provider,
                        focused,
                        limit,
                        self._provider_timeout_seconds,
                    )
                    normalized_results = tuple(
                        item for item in raw_results if isinstance(item, Mapping)
                    )
                    final_status, final_reason = _classify_provider_response(
                        normalized_results,
                        error,
                    )
                except Exception as exc:
                    normalized_results = ()
                    final_status = "failed"
                    final_reason = _exception_reason(exc)
                elapsed = max(0.0, self._monotonic() - started)
                audits.append(
                    ProviderAttemptAudit(
                        provider=provider,
                        attempt=attempt,
                        status=final_status,
                        reason=final_reason,
                        result_count=len(normalized_results),
                        elapsed_seconds=round(elapsed, 6),
                        query_sha256=query_digest,
                        query_chars=len(focused),
                    )
                )
                final_results = normalized_results
                if final_status != "failed" or not _is_transient_failure(
                    final_reason
                ):
                    break
            provider_results[provider] = final_results if final_status == "ok" else ()
            outcomes.append(
                ProviderFinalOutcome(
                    provider=provider,
                    status=final_status,
                    reason=final_reason,
                    attempts=attempts,
                    result_count=len(provider_results[provider]),
                )
            )
            if final_status == "failed":
                provider_errors.append(f"{provider}:{final_reason}")

        merged = _round_robin_merge(provider_results, enabled, limit=limit)
        status, reason = _overall_status(outcomes, has_results=bool(merged))
        return _payload(
            status=status,
            reason=reason,
            query=focused,
            results=merged,
            providers_attempted=enabled,
            provider_errors=tuple(provider_errors),
            provider_audits=tuple(audits),
            provider_outcomes=tuple(outcomes),
            searched_at=current.isoformat(),
        )


def _payload(
    *,
    status: str,
    reason: str,
    query: str,
    results: list[dict[str, Any]],
    providers_attempted: tuple[ResearchSearchProvider, ...],
    provider_errors: tuple[str, ...],
    provider_audits: tuple[ProviderAttemptAudit, ...],
    provider_outcomes: tuple[ProviderFinalOutcome, ...],
    searched_at: str,
) -> dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "query": query,
        "results": results,
        "providers_attempted": list(providers_attempted),
        "provider_errors": list(provider_errors),
        "provider_audits": [item.to_dict() for item in provider_audits],
        "provider_outcomes": [item.to_dict() for item in provider_outcomes],
        "searched_at": searched_at,
    }


def _default_provider_enabled(provider: ResearchSearchProvider) -> bool:
    if provider == "searxng":
        return searxng_enabled()
    if provider == "bing_rss":
        return _env_flag("WEB_ENABLE_BING_RSS", default=True)
    if provider == "duckduckgo_html":
        return _env_flag("WEB_ENABLE_DUCKDUCKGO", default=True)
    return False


def _default_provider_call(
    provider: ResearchSearchProvider,
    query: str,
    limit: int,
    timeout: float,
) -> tuple[list[Mapping[str, Any]], str]:
    if provider == "searxng":
        raw = search_searxng(
            query,
            max_results=limit,
            timeout=timeout,
            categories=os.getenv("WEB_SEARXNG_CATEGORIES", "general"),
        )
        results: list[Mapping[str, Any]] = [
            {
                "title": str(item.get("title") or ""),
                "url": str(item.get("link") or item.get("resolved_link") or ""),
                "snippet": str(
                    item.get("search_excerpt") or item.get("summary") or ""
                ),
                "source": str(item.get("source") or "SearXNG"),
                "published_at": str(item.get("published_at") or ""),
            }
            for item in raw[:limit]
            if item.get("title") and (item.get("link") or item.get("resolved_link"))
        ]
        error = "" if results else get_last_searxng_error()
        return results, error
    if provider == "bing_rss":
        bing_results, error = GeneralWebGateway._search_bing_rss(query, limit, timeout)
        return cast(list[Mapping[str, Any]], bing_results), error
    if provider == "duckduckgo_html":
        duckduckgo_results, error = GeneralWebGateway._search_duckduckgo(
            query, limit, timeout
        )
        return cast(list[Mapping[str, Any]], duckduckgo_results), error
    raise ValueError("unsupported research search provider")


def _classify_provider_response(
    results: tuple[Mapping[str, Any], ...],
    error: str,
) -> tuple[ProviderAttemptStatus, str]:
    if results:
        return "ok", "results_found"
    if not error or "empty_response" in error.casefold():
        return "empty", "no_results"
    return "failed", _sanitize_provider_error(error)


def _sanitize_provider_error(error: str) -> str:
    """Collapse raw provider errors into bounded, non-sensitive categories."""

    value = str(error or "").casefold()
    if "challenge" in value or "captcha" in value or "bot" in value:
        return "challenge"
    status = _http_status(value)
    if status:
        return f"http_status:{status}"
    if "timeout" in value or "timed out" in value:
        return "timeout"
    if "unresponsive_engines" in value:
        return "unresponsive_engines"
    if "unexpected content-type" in value or "unexpected_content_type" in value:
        return "unexpected_content_type"
    if "invalid_xml" in value or "parseerror" in value:
        return "invalid_xml"
    if "urlerror" in value or "name or service not known" in value:
        return "url_error"
    if any(
        marker in value
        for marker in (
            "connection",
            "connectionreset",
            "connection reset",
            "refused",
            "broken pipe",
        )
    ):
        return "connection_error"
    if "ssl" in value or "tls" in value:
        return "tls_error"
    if "json" in value and ("decode" in value or "invalid" in value):
        return "invalid_json"
    return "provider_error"


def _exception_reason(exc: Exception) -> str:
    """Classify an exception by type only; never persist its message."""

    name = type(exc).__name__.casefold()
    if isinstance(exc, TimeoutError) or "timeout" in name:
        return "timeout"
    if "connection" in name or "brokenpipe" in name:
        return "connection_error"
    if "urlerror" in name:
        return "url_error"
    if "ssl" in name or "tls" in name:
        return "tls_error"
    return "provider_error"


def _http_status(value: str) -> str:
    marker = "http_status:"
    index = value.find(marker)
    if index < 0:
        return ""
    tail = value[index + len(marker) :]
    digits = "".join(character for character in tail[:3] if character.isdigit())
    return digits if len(digits) == 3 else ""


def _overall_status(
    outcomes: list[ProviderFinalOutcome],
    *,
    has_results: bool,
) -> tuple[str, str]:
    failed = sum(item.status == "failed" for item in outcomes)
    if has_results:
        return (
            ("partial", "results_with_provider_failures")
            if failed
            else ("ok", "results_found")
        )
    if failed == len(outcomes):
        return "unavailable", "providers_failed"
    if failed:
        return "partial", "providers_partially_failed_without_results"
    return "empty", "providers_returned_no_results"


def _round_robin_merge(
    provider_results: dict[ResearchSearchProvider, tuple[Mapping[str, Any], ...]],
    enabled: tuple[ResearchSearchProvider, ...],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    positions: dict[str, int] = {}
    max_depth = max(
        (len(provider_results.get(provider, ())) for provider in enabled),
        default=0,
    )
    for rank in range(max_depth):
        for provider in enabled:
            items = provider_results.get(provider, ())
            if rank >= len(items):
                continue
            normalized = _normalize_result(items[rank], provider)
            if normalized is None:
                continue
            key = normalized["canonical_url"]
            existing_position = positions.get(key)
            if existing_position is not None:
                existing = merged[existing_position]
                existing["providers"] = list(
                    dict.fromkeys([*existing["providers"], provider])
                )
                if len(normalized["snippet"]) > len(existing["snippet"]):
                    existing["snippet"] = normalized["snippet"]
                continue
            if len(merged) >= limit:
                continue
            positions[key] = len(merged)
            merged.append(normalized)
    return merged


def _normalize_result(
    raw: Mapping[str, Any], provider: ResearchSearchProvider
) -> dict[str, Any] | None:
    url = canonicalize_url(str(raw.get("url") or raw.get("link") or ""))
    title = _bounded_text(raw.get("title") or raw.get("name"), 500)
    if not url or not title:
        return None
    return {
        "canonical_url": url,
        "url": url,
        "title": title,
        "snippet": _bounded_text(
            raw.get("snippet") or raw.get("search_excerpt") or raw.get("summary"),
            2000,
        ),
        "source": _bounded_text(raw.get("source"), 200),
        "published_at": _bounded_text(raw.get("published_at"), 100),
        "provider": provider,
        "providers": [provider],
    }


def _is_transient_failure(reason: str) -> bool:
    if reason in {"timeout", "url_error", "connection_error", "unresponsive_engines"}:
        return True
    if reason.startswith("http_status:"):
        return reason in {
            "http_status:429",
            "http_status:500",
            "http_status:502",
            "http_status:503",
            "http_status:504",
        }
    return False


def _bounded_timeout(value: float | None) -> float:
    if value is None:
        try:
            value = float(
                os.getenv(
                    "RESEARCH_SEARCH_PROVIDER_TIMEOUT_SECONDS",
                    str(DEFAULT_PROVIDER_TIMEOUT_SECONDS),
                )
            )
        except (TypeError, ValueError):
            value = DEFAULT_PROVIDER_TIMEOUT_SECONDS
    return max(1.0, min(float(value), MAX_PROVIDER_TIMEOUT_SECONDS))


def _env_flag(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _bounded_text(value: Any, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


__all__ = [
    "MAX_PROVIDER_ATTEMPTS",
    "PROVIDER_ORDER",
    "ProviderAttemptAudit",
    "ProviderFinalOutcome",
    "ResearchProviderSearch",
    "ResearchSearchProvider",
]

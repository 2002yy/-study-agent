"""Truthful projection of model web-tool calls into usable evidence."""

from __future__ import annotations

from copy import deepcopy
import ipaddress
from typing import Any
from urllib.parse import urlparse


def _public_url(value: object) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
    ):
        return ""
    host = (parsed.hostname or "").strip().casefold()
    if not host or host == "localhost" or host.endswith(".localhost"):
        return ""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return url
    if (
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        return ""
    return url


def _is_true(value: object) -> bool:
    return value is True or str(value).strip().casefold() == "true"


def trusted_tool_calls(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only calls that contain user-displayable source evidence."""

    trusted: list[dict[str, Any]] = []
    discovered_urls: set[str] = set()
    for raw_call in calls:
        if not isinstance(raw_call, dict):
            continue
        name = str(raw_call.get("name") or "")
        result = raw_call.get("result")
        if not isinstance(result, dict) or result.get("error"):
            continue
        call = deepcopy(raw_call)
        projected = call.get("result")
        if not isinstance(projected, dict):
            continue

        if name == "web_search":
            if str(result.get("status") or "") != "ok":
                continue
            valid_results = [
                dict(item)
                for item in result.get("results", [])
                if isinstance(item, dict)
                and str(item.get("title") or "").strip()
                and _public_url(item.get("url") or item.get("link"))
            ]
            if not valid_results:
                continue
            projected["results"] = valid_results
            discovered_urls.update(
                _public_url(item.get("url") or item.get("link")).casefold()
                for item in valid_results
            )
            trusted.append(call)
            continue

        if name == "web_read":
            content = result.get("content") or result.get("readme")
            arguments = raw_call.get("arguments")
            arguments = arguments if isinstance(arguments, dict) else {}
            url = _public_url(result.get("url") or arguments.get("url"))
            if not _is_true(result.get("ok")) or not url:
                continue
            if url.casefold() not in discovered_urls:
                continue
            if not isinstance(content, str) or not content.strip():
                continue
            projected["url"] = url
            trusted.append(call)
            continue

        if name.startswith("github_") and _is_true(result.get("ok")):
            arguments = raw_call.get("arguments")
            arguments = arguments if isinstance(arguments, dict) else {}
            source_url = _public_url(
                result.get("html_url")
                or result.get("url")
                or result.get("repository")
                or arguments.get("repo_url")
            )
            valid_results = [
                dict(item)
                for item in result.get("results", [])
                if isinstance(item, dict)
                and _public_url(item.get("url") or item.get("html_url"))
            ]
            if not source_url and not valid_results:
                continue
            if valid_results:
                projected["results"] = valid_results
            trusted.append(call)

    return trusted


def tool_call_errors(calls: list[dict[str, Any]]) -> list[str]:
    """Collect bounded provider/tool failures for durable diagnostics."""

    errors: list[str] = []
    for call in calls:
        if not isinstance(call, dict):
            continue
        name = str(call.get("name") or "web_tool")
        result = call.get("result")
        if not isinstance(result, dict):
            errors.append(f"{name}:invalid_result")
            continue
        if result.get("error"):
            errors.append(f"{name}:{result['error']}")
        for error in result.get("provider_errors", []):
            if str(error).strip():
                errors.append(f"{name}:{error}")
        if str(result.get("status") or "") == "unavailable":
            errors.append(f"{name}:{result.get('reason') or 'provider_unavailable'}")
    return list(dict.fromkeys(errors))[:20]


def diagnostic_tool_calls(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep failure diagnostics without persisting retrieved page content."""

    diagnostics: list[dict[str, Any]] = []
    for call in calls[:20]:
        if not isinstance(call, dict):
            continue
        result = call.get("result")
        result = result if isinstance(result, dict) else {}
        arguments = call.get("arguments")
        arguments = arguments if isinstance(arguments, dict) else {}
        provider_errors = result.get("provider_errors")
        provider_errors = provider_errors if isinstance(provider_errors, list) else []
        diagnostics.append(
            {
                "name": str(call.get("name") or "web_tool"),
                "arguments": dict(arguments),
                "status": str(result.get("status") or ""),
                "reason": str(result.get("reason") or ""),
                "error": str(result.get("error") or "")[:1000],
                "provider_errors": [
                    str(value)[:1000]
                    for value in provider_errors[:10]
                ],
                "result_count": len(result.get("results", []))
                if isinstance(result.get("results"), list)
                else 0,
            }
        )
    return diagnostics


def tool_source_items(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project trusted web search/read calls into durable source items."""

    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for call in trusted_tool_calls(calls):
        name = str(call.get("name") or "")
        result = call.get("result")
        if not isinstance(result, dict):
            continue
        candidates: list[dict[str, Any]] = []
        if name == "web_search":
            candidates = [dict(item) for item in result.get("results", [])]
        elif name == "web_read":
            url = _public_url(result.get("url"))
            candidates = [
                {
                    "title": urlparse(url).netloc,
                    "url": url,
                    "snippet": str(result.get("content") or result.get("readme") or "")[:500],
                    "source": str(result.get("method") or "web_read"),
                }
            ]
        elif name.startswith("github_"):
            arguments = call.get("arguments")
            arguments = arguments if isinstance(arguments, dict) else {}
            url = _public_url(
                result.get("html_url")
                or result.get("url")
                or arguments.get("repo_url")
            )
            if url:
                candidates = [
                    {
                        "title": str(
                            result.get("title")
                            or result.get("repository")
                            or arguments.get("repo_url")
                            or name
                        ),
                        "url": url,
                        "snippet": str(result.get("summary") or result.get("reason") or "")[:500],
                        "source": "GitHub",
                    }
                ]
        for item in candidates:
            url = _public_url(item.get("url") or item.get("link"))
            title = str(item.get("title") or "").strip()
            if not url or not title or url.casefold() in seen:
                continue
            seen.add(url.casefold())
            items.append({**item, "url": url, "link": url})
    return items

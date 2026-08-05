"""Single owner for Study Agent CORS policy parsing and response handling."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urlsplit

from fastapi import Request, Response
from fastapi.responses import JSONResponse

DEVELOPMENT_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:4173",
    "http://localhost:4173",
)
TEST_ORIGINS = ("http://testserver",)
PRODUCTION_ORIGINS: tuple[str, ...] = ()

ALLOWED_METHODS = ("GET", "POST", "PATCH", "DELETE", "OPTIONS")
ALLOWED_HEADERS = ("Authorization", "Content-Type", "X-Study-Agent-Token")

_ENVIRONMENT_ALIASES = {
    "dev": "development",
    "development": "development",
    "local": "development",
    "test": "test",
    "testing": "test",
    "ci": "test",
    "prod": "production",
    "production": "production",
}
_DEFAULT_ORIGINS = {
    "development": DEVELOPMENT_ORIGINS,
    "test": TEST_ORIGINS,
    "production": PRODUCTION_ORIGINS,
}
_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


class CorsConfigurationError(ValueError):
    """Raised when the CORS environment contains an unsafe or invalid policy."""


@dataclass(frozen=True)
class CorsPolicy:
    environment: str
    origins: tuple[str, ...]
    allow_credentials: bool
    allowed_methods: tuple[str, ...] = ALLOWED_METHODS
    allowed_headers: tuple[str, ...] = ALLOWED_HEADERS


def _parse_environment(raw: str | None) -> str:
    value = (raw or "development").strip().lower()
    try:
        return _ENVIRONMENT_ALIASES[value]
    except KeyError as exc:
        expected = ", ".join(sorted({"development", "test", "production"}))
        raise CorsConfigurationError(
            f"Invalid STUDY_AGENT_ENV={value!r}; expected one of: {expected}"
        ) from exc


def _parse_bool(raw: str | None, *, default: bool) -> bool:
    if raw is None or not raw.strip():
        return default
    value = raw.strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    raise CorsConfigurationError(
        "STUDY_AGENT_CORS_ALLOW_CREDENTIALS must be one of "
        "true/false, 1/0, yes/no, or on/off"
    )


def _normalize_origin(raw: str) -> str:
    value = raw.strip()
    if value == "*":
        return value

    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise CorsConfigurationError(
            f"Invalid CORS origin {value!r}; expected an absolute http(s) origin"
        )
    if parsed.username or parsed.password:
        raise CorsConfigurationError(f"CORS origin must not contain credentials: {value!r}")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise CorsConfigurationError(
            f"CORS origin must not contain a path, query, or fragment: {value!r}"
        )

    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def _deduplicate_origins(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        if not raw.strip():
            continue
        origin = _normalize_origin(raw)
        if origin in seen:
            continue
        seen.add(origin)
        result.append(origin)
    return tuple(result)


def resolve_cors_policy(environ: Mapping[str, str] | None = None) -> CorsPolicy:
    """Resolve one normalized policy from environment variables.

    An absent ``STUDY_AGENT_CORS_ORIGINS`` uses environment-specific defaults.
    A present but blank value explicitly disables CORS. Production has no implicit
    origins. Wildcard origins are allowed only when credentials are disabled.
    """

    source = os.environ if environ is None else environ
    environment = _parse_environment(source.get("STUDY_AGENT_ENV"))
    raw_origins = source.get("STUDY_AGENT_CORS_ORIGINS")
    if raw_origins is None:
        origin_values = list(_DEFAULT_ORIGINS[environment])
    else:
        origin_values = raw_origins.split(",")

    origins = _deduplicate_origins(origin_values)
    allow_credentials = _parse_bool(
        source.get("STUDY_AGENT_CORS_ALLOW_CREDENTIALS"),
        default=True,
    )

    if "*" in origins:
        if len(origins) != 1:
            raise CorsConfigurationError(
                "Wildcard CORS origin must be the only configured origin"
            )
        if allow_credentials:
            raise CorsConfigurationError(
                "Wildcard CORS origin cannot be combined with credentials"
            )

    return CorsPolicy(
        environment=environment,
        origins=origins,
        allow_credentials=allow_credentials,
    )


def _normalized_request_origin(origin: str) -> str | None:
    try:
        return _normalize_origin(origin)
    except CorsConfigurationError:
        return None


def is_cors_origin_allowed(origin: str, policy: CorsPolicy) -> bool:
    if not origin:
        return False
    if policy.origins == ("*",):
        return True
    normalized = _normalized_request_origin(origin)
    return normalized is not None and normalized in policy.origins


def is_cors_preflight(request: Request) -> bool:
    return bool(
        request.method == "OPTIONS"
        and request.headers.get("access-control-request-method")
    )


def _append_vary(response: Response, value: str) -> None:
    existing = [item.strip() for item in response.headers.get("Vary", "").split(",") if item.strip()]
    if value.lower() not in {item.lower() for item in existing}:
        existing.append(value)
    if existing:
        response.headers["Vary"] = ", ".join(existing)


def add_cors_headers(response: Response, origin: str, policy: CorsPolicy) -> None:
    if not is_cors_origin_allowed(origin, policy):
        return

    wildcard = policy.origins == ("*",)
    response.headers["Access-Control-Allow-Origin"] = "*" if wildcard else origin
    response.headers["Access-Control-Allow-Methods"] = ",".join(policy.allowed_methods)
    response.headers["Access-Control-Allow-Headers"] = ",".join(policy.allowed_headers)
    if policy.allow_credentials:
        response.headers["Access-Control-Allow-Credentials"] = "true"
    if not wildcard:
        _append_vary(response, "Origin")


def _requested_headers_allowed(request: Request, policy: CorsPolicy) -> bool:
    raw = request.headers.get("access-control-request-headers", "")
    if not raw.strip():
        return True
    allowed = {header.lower() for header in policy.allowed_headers}
    requested = {header.strip().lower() for header in raw.split(",") if header.strip()}
    return requested.issubset(allowed)


def build_cors_preflight_response(request: Request, policy: CorsPolicy) -> Response:
    origin = request.headers.get("origin", "")
    if not is_cors_origin_allowed(origin, policy):
        return JSONResponse({"detail": "CORS origin not allowed"}, status_code=403)

    requested_method = request.headers.get("access-control-request-method", "").upper()
    if requested_method not in policy.allowed_methods:
        return JSONResponse({"detail": "CORS method not allowed"}, status_code=403)
    if not _requested_headers_allowed(request, policy):
        return JSONResponse({"detail": "CORS headers not allowed"}, status_code=403)

    response = Response(status_code=204)
    add_cors_headers(response, origin, policy)
    return response

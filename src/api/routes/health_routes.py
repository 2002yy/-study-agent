"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from src.api.models.common import HealthResponse, SearchProviderHealthResponse
from src.web.provider_health import inspect_web_search_providers

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    from src.rag.index import DEFAULT_RAG_INDEX_PATH

    return HealthResponse(
        status="ok",
        service="study-agent",
        rag_index_exists=DEFAULT_RAG_INDEX_PATH.exists(),
    )


@router.get("/health/providers", response_model=SearchProviderHealthResponse)
def provider_health(probe: bool = True) -> SearchProviderHealthResponse:
    """Diagnose search-provider configuration and bounded live reachability."""

    return SearchProviderHealthResponse.model_validate(
        inspect_web_search_providers(probe=probe, timeout_seconds=5.0)
    )

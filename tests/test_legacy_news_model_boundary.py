from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY_NEWS_MODELS = (
    "NewsSearchRequest",
    "NewsSearchResponse",
    "NewsStageSearchRequest",
    "NewsStageSearchResponse",
    "NewsEnrichRequest",
    "NewsEnrichResponse",
    "NewsDigestRequest",
    "NewsDigestResponse",
    "NewsDiscussRequest",
    "NewsDiscussResponse",
)
LIVE_NEWS_MODELS = (
    "NewsRunCreateRequest",
    "NewsRunSearchRequest",
    "NewsRunEnrichRequest",
    "NewsRunDigestRequest",
    "NewsRunDiscussRequest",
    "NewsRunResponse",
    "NewsRunListResponse",
    "NewsLookupRequest",
    "NewsLookupResponse",
    "ResearchRunCreateRequest",
    "WebLookupRunResponse",
    "WebLookupRunListResponse",
)


def _production_sources() -> list[Path]:
    roots = (ROOT / "src", ROOT / "frontend" / "src")
    suffixes = {".py", ".ts", ".tsx"}
    return [
        path
        for root in roots
        for path in root.rglob("*")
        if path.is_file() and path.suffix in suffixes and ".test." not in path.name
    ]


def test_retired_news_models_have_no_production_owner_or_compat_export() -> None:
    offenders: dict[str, list[str]] = {}
    for path in _production_sources():
        source = path.read_text(encoding="utf-8")
        matched = [name for name in LEGACY_NEWS_MODELS if name in source]
        if matched:
            offenders[path.relative_to(ROOT).as_posix()] = matched

    assert offenders == {}


def test_live_news_contracts_remain_owned_by_news_models() -> None:
    source = (ROOT / "src" / "api" / "models" / "news.py").read_text(
        encoding="utf-8"
    )
    for name in LIVE_NEWS_MODELS:
        assert f"class {name}(BaseModel):" in source


def test_durable_news_routes_keep_direct_model_owner_imports() -> None:
    route_source = (ROOT / "src" / "api" / "routes" / "news_routes.py").read_text(
        encoding="utf-8"
    )
    for name in (
        "NewsRunCreateRequest",
        "NewsRunSearchRequest",
        "NewsRunEnrichRequest",
        "NewsRunDigestRequest",
        "NewsRunDiscussRequest",
        "NewsRunResponse",
        "NewsRunListResponse",
    ):
        assert name in route_source

    assert "from src.api.models.news import" in route_source

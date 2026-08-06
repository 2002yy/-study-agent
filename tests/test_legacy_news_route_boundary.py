from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.api import app

ROOT = Path(__file__).resolve().parents[1]
LEGACY_NEWS_PATHS = (
    "/news/round",
    "/wechat/news-round",
    "/news/search",
    "/news/enrich",
    "/news/digest",
    "/news/discuss",
)


def test_legacy_news_tombstones_are_not_registered():
    registered_paths = {route.path for route in app.routes}

    assert set(LEGACY_NEWS_PATHS).isdisjoint(registered_paths)

    client = TestClient(app)
    for path in LEGACY_NEWS_PATHS:
        response = client.post(path, json={})
        assert response.status_code == 404


def test_production_frontend_does_not_call_legacy_news_paths():
    source_root = ROOT / "frontend" / "src"
    production_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in source_root.rglob("*")
        if path.suffix in {".ts", ".tsx"}
        and ".test." not in path.name
        and "__tests__" not in path.parts
    )

    for path in LEGACY_NEWS_PATHS:
        assert path not in production_source


def test_news_route_owner_cannot_restore_legacy_path_literals():
    route_source = (ROOT / "src" / "api" / "routes" / "news_routes.py").read_text(
        encoding="utf-8"
    )

    for path in LEGACY_NEWS_PATHS:
        assert path not in route_source

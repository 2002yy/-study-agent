from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = ROOT / "frontend" / "src"
RETIRED_FRONTEND_FILES = (
    FRONTEND_ROOT / "features" / "news-workspace" / "NewsWorkspace.tsx",
    FRONTEND_ROOT / "features" / "news-workspace" / "newsController.ts",
)
NEWS_CLIENT_COMMANDS = (
    "createNewsRun",
    "searchNewsRun",
    "getNewsRun",
    "enrichNewsRun",
    "digestNewsRun",
    "discussNewsRun",
)


def _production_frontend_sources() -> list[Path]:
    return [
        path
        for path in FRONTEND_ROOT.rglob("*")
        if path.is_file()
        and path.suffix in {".ts", ".tsx"}
        and ".test." not in path.name
    ]


def test_retired_news_workspace_and_controller_stay_deleted() -> None:
    assert all(not path.exists() for path in RETIRED_FRONTEND_FILES)


def test_news_run_client_has_no_product_frontend_owner() -> None:
    api_path = FRONTEND_ROOT / "api.ts"
    api_source = api_path.read_text(encoding="utf-8")
    for command in NEWS_CLIENT_COMMANDS:
        assert f"function {command}" in api_source
    assert "/news/runs" in api_source

    forbidden_tokens = (
        "NewsWorkspace",
        "useNewsController",
        "NewsController",
        *NEWS_CLIENT_COMMANDS,
        "/news/runs",
    )
    offenders: list[str] = []
    for path in _production_frontend_sources():
        if path == api_path:
            continue
        source = path.read_text(encoding="utf-8")
        if any(token in source for token in forbidden_tokens):
            offenders.append(path.relative_to(ROOT).as_posix())

    assert offenders == []


def test_news_routes_keep_only_durable_run_contracts() -> None:
    route_source = (ROOT / "src" / "api" / "routes" / "news_routes.py").read_text(
        encoding="utf-8"
    )
    for route in (
        '@router.post("/news/runs"',
        '@router.post("/news/runs/{run_id}/search"',
        '@router.get("/news/runs"',
        '@router.get("/news/runs/{run_id}"',
        '@router.post("/news/runs/{run_id}/enrich"',
        '@router.post("/news/runs/{run_id}/digest"',
        '@router.post("/news/runs/{run_id}/discuss"',
    ):
        assert route in route_source

    for retired_route in (
        '@router.post("/news/round"',
        '@router.post("/wechat/news-round"',
        '@router.post("/news/search"',
        '@router.post("/news/enrich"',
        '@router.post("/news/digest"',
        '@router.post("/news/discuss"',
    ):
        assert retired_route not in route_source

    assert "status_code=410" not in route_source
    assert "run_news_round(" not in route_source

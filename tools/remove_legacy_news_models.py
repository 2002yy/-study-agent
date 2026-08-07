from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY_MODELS = {
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
}


def remove_selected_classes(source: str) -> str:
    lines = source.splitlines(keepends=True)
    output: list[str] = []
    skipping = False
    for line in lines:
        if line.startswith("class "):
            name = line.removeprefix("class ").split("(", 1)[0].strip()
            skipping = name in LEGACY_MODELS
        if not skipping:
            output.append(line)
    return "".join(output)


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return source.replace(old, new, 1)


def main() -> None:
    news_path = ROOT / "src" / "api" / "models" / "news.py"
    news_source = news_path.read_text(encoding="utf-8")
    news_source = remove_selected_classes(news_source)
    news_path.write_text(news_source, encoding="utf-8")

    models_init = ROOT / "src" / "api" / "models" / "__init__.py"
    models_source = models_init.read_text(encoding="utf-8")
    start = models_source.index("from .news import (")
    end = models_source.index(")\nfrom .rag import (", start) + 2
    models_source = (
        models_source[:start]
        + "from .news import (\n    NewsLookupRequest,\n    NewsLookupResponse,\n)\n"
        + models_source[end:]
    )
    models_init.write_text(models_source, encoding="utf-8")

    api_init = ROOT / "src" / "api" / "__init__.py"
    api_source = api_init.read_text(encoding="utf-8")
    start = api_source.index("from .models.news import (")
    end = api_source.index(")\nfrom .models.rag import (", start) + 2
    api_source = (
        api_source[:start]
        + "from .models.news import (NewsLookupRequest, NewsLookupResponse)\n"
        + api_source[end:]
    )
    api_source = replace_once(
        api_source,
        "    news_result_payload,\n",
        "",
        "remove helper import",
    )
    api_source = replace_once(
        api_source,
        '_news_result_payload = __import__("src.application.helpers").application.helpers.news_result_payload\n',
        "",
        "remove helper alias",
    )
    api_init.write_text(api_source, encoding="utf-8")

    helpers_path = ROOT / "src" / "application" / "helpers.py"
    helpers_source = helpers_path.read_text(encoding="utf-8")
    start_marker = "# ── News helpers ───────────────────────────────────────────────────────\n"
    end_marker = "# ── Chat context helpers ───────────────────────────────────────────────\n"
    start = helpers_source.index(start_marker)
    end = helpers_source.index(end_marker, start)
    helpers_source = helpers_source[:start] + helpers_source[end:]
    helpers_path.write_text(helpers_source, encoding="utf-8")

    production_roots = (ROOT / "src", ROOT / "frontend" / "src")
    offenders: dict[str, list[str]] = {}
    for root in production_roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".ts", ".tsx"}:
                continue
            source = path.read_text(encoding="utf-8")
            matched = sorted(name for name in LEGACY_MODELS if name in source)
            if matched:
                offenders[path.relative_to(ROOT).as_posix()] = matched
    if offenders:
        raise RuntimeError(f"legacy News model references remain: {offenders}")


if __name__ == "__main__":
    main()

from __future__ import annotations

from src.web.module_aliases import (
    ModuleAlias,
    load_module_aliases,
    resolve_snapshot_import,
)


def test_load_module_aliases_parses_tsconfig_with_comments_and_trailing_commas():
    snapshot = {
        "files": [
            {
                "path": "frontend/tsconfig.json",
                "content": """
                {
                  // project paths
                  "compilerOptions": {
                    "baseUrl": "src",
                    "paths": {
                      "@app/*": ["app/*", "app2/*"],
                      "@lib": ["lib/index.ts"],
                    },
                  },
                }
                """,
            }
        ]
    }

    aliases = load_module_aliases(snapshot)

    assert len(aliases) == 2
    first, second = aliases
    assert first.pattern == "@app/*"
    assert first.targets == ("app/*", "app2/*")
    assert first.base_path == "frontend/src"
    assert first.config_path == "frontend/tsconfig.json"
    assert second.pattern == "@lib"
    assert second.targets == ("lib/index.ts",)


def test_load_module_aliases_ignores_non_config_and_invalid_files():
    snapshot = {
        "files": [
            {"path": "src/main.ts", "content": "{}"},
            {"path": "jsconfig.json", "content": "not json at all"},
            {"path": "frontend/jsconfig.json", "content": '{"compilerOptions": {}}'},
            {"path": "frontend/tsconfig.json", "content": '{"compilerOptions": {"paths": "x"}}'},
            {"path": "frontend/jsconfig.json", "content": '{"compilerOptions": {"paths": {"a/*": ["a/*"]}}}'},
            "not a dict",
        ]
    }

    aliases = load_module_aliases(snapshot)

    assert len(aliases) == 1
    assert aliases[0].pattern == "a/*"


def test_load_module_aliases_sorts_by_config_path_then_pattern():
    snapshot = {
        "files": [
            {
                "path": "z/tsconfig.json",
                "content": '{"compilerOptions": {"paths": {"z@/*": ["z/*"]}}}',
            },
            {
                "path": "a/tsconfig.json",
                "content": '{"compilerOptions": {"paths": {"a@/*": ["a/*"]}}}',
            },
        ]
    }

    aliases = load_module_aliases(snapshot)

    assert [alias.config_path for alias in aliases] == ["a/tsconfig.json", "z/tsconfig.json"]


def test_match_alias_exact_and_wildcard_semantics():
    from src.web.module_aliases import _match_alias

    assert _match_alias("@lib", "@lib") == ""
    assert _match_alias("@lib", "@other") is None
    assert _match_alias("@app/*", "@app/utils/format") == "utils/format"
    assert _match_alias("@app/*", "@app/utils/format/x") == "utils/format/x"
    assert _match_alias("*/core", "lib/core") == "lib"
    assert _match_alias("*/core", "lib/util") is None


def test_resolve_snapshot_import_prefers_relative_resolution():
    paths = {"src/a.ts", "src/b.ts"}
    aliases = (
        ModuleAlias("@app/*", ("src/*",), "", "tsconfig.json"),
    )

    assert resolve_snapshot_import("src/a.ts", "./b", paths, aliases) == "src/b.ts"


def test_resolve_snapshot_import_uses_wildcard_alias_with_extension_candidates():
    paths = {"src/utils/format.ts", "src/utils/format/index.ts"}
    aliases = (
        ModuleAlias("@app/*", ("src/*",), "", "tsconfig.json"),
    )

    assert resolve_snapshot_import("src/a.ts", "@app/utils/format", paths, aliases) == "src/utils/format.ts"


def test_resolve_snapshot_import_ambiguous_alias_target_returns_empty():
    paths = {"x/src/utils/format.ts", "other/src/utils/format.ts"}
    aliases = (
        ModuleAlias("@app/*", ("src/*",), "", "tsconfig.json"),
    )

    assert resolve_snapshot_import("src/a.ts", "@app/utils/format", paths, aliases) == ""


def test_resolve_snapshot_import_falls_back_to_dotted_module_path():
    paths = {"utils/format.ts", "src/main/java/com/example/Service.java"}
    aliases: tuple[ModuleAlias, ...] = ()

    assert resolve_snapshot_import("src/a.ts", "utils/format", paths, aliases) == "utils/format.ts"
    assert (
        resolve_snapshot_import("src/a.ts", "com.example.Service", paths, aliases)
        == "src/main/java/com/example/Service.java"
    )


def test_resolve_snapshot_import_returns_empty_for_unresolvable_module():
    paths = {"src/a.ts"}
    aliases: tuple[ModuleAlias, ...] = ()

    assert resolve_snapshot_import("src/a.ts", "missing/thing", paths, aliases) == ""

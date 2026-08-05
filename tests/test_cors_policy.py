from __future__ import annotations

from pathlib import Path

import pytest

from src.api.cors import CorsConfigurationError, resolve_cors_policy

ROOT = Path(__file__).resolve().parents[1]


def test_development_uses_local_origins_when_variable_is_absent():
    policy = resolve_cors_policy({"STUDY_AGENT_ENV": "development"})

    assert policy.environment == "development"
    assert policy.origins == (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    )
    assert policy.allow_credentials is True


def test_test_and_production_have_distinct_defaults():
    test_policy = resolve_cors_policy({"STUDY_AGENT_ENV": "test"})
    production_policy = resolve_cors_policy({"STUDY_AGENT_ENV": "production"})

    assert test_policy.origins == ("http://testserver",)
    assert production_policy.origins == ()


def test_present_but_blank_origins_explicitly_disable_cors():
    policy = resolve_cors_policy(
        {
            "STUDY_AGENT_ENV": "development",
            "STUDY_AGENT_CORS_ORIGINS": "  ,  ",
        }
    )

    assert policy.origins == ()


def test_duplicate_origins_are_normalized_once_in_stable_order():
    policy = resolve_cors_policy(
        {
            "STUDY_AGENT_CORS_ORIGINS": (
                "https://Study.Example/, https://study.example, http://localhost:5173"
            )
        }
    )

    assert policy.origins == (
        "https://study.example",
        "http://localhost:5173",
    )


def test_wildcard_requires_credentials_to_be_disabled():
    with pytest.raises(CorsConfigurationError, match="cannot be combined with credentials"):
        resolve_cors_policy({"STUDY_AGENT_CORS_ORIGINS": "*"})

    policy = resolve_cors_policy(
        {
            "STUDY_AGENT_CORS_ORIGINS": "*",
            "STUDY_AGENT_CORS_ALLOW_CREDENTIALS": "false",
        }
    )

    assert policy.origins == ("*",)
    assert policy.allow_credentials is False


def test_wildcard_cannot_be_mixed_with_named_origins():
    with pytest.raises(CorsConfigurationError, match="must be the only configured origin"):
        resolve_cors_policy(
            {
                "STUDY_AGENT_CORS_ORIGINS": "*,https://study.example",
                "STUDY_AGENT_CORS_ALLOW_CREDENTIALS": "false",
            }
        )


def test_invalid_environment_boolean_and_origin_fail_closed():
    with pytest.raises(CorsConfigurationError, match="Invalid STUDY_AGENT_ENV"):
        resolve_cors_policy({"STUDY_AGENT_ENV": "staging"})
    with pytest.raises(CorsConfigurationError, match="must be one of"):
        resolve_cors_policy({"STUDY_AGENT_CORS_ALLOW_CREDENTIALS": "maybe"})
    with pytest.raises(CorsConfigurationError, match="path, query, or fragment"):
        resolve_cors_policy({"STUDY_AGENT_CORS_ORIGINS": "https://study.example/api"})


def test_cors_implementation_has_one_source_owner():
    api_dir = ROOT / "src" / "api"
    app_source = (api_dir / "app.py").read_text(encoding="utf-8")
    cors_source = (api_dir / "cors.py").read_text(encoding="utf-8")
    other_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in api_dir.rglob("*.py")
        if path.name not in {"app.py", "cors.py"}
    )

    assert "CORSMiddleware" not in app_source
    assert "http://localhost:5173" not in app_source
    assert "Access-Control-Allow-Origin" not in app_source
    assert "resolve_cors_policy" in app_source
    assert "Access-Control-Allow-Origin" in cors_source
    assert "STUDY_AGENT_CORS_ORIGINS" not in other_sources
    assert "Access-Control-Allow-Origin" not in other_sources

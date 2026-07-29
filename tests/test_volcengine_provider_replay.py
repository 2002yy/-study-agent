from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.rag.volcengine_replay import (
    VOLCENGINE_ARK_BASE_URL,
    VolcengineArkReplayProvider,
)
from tools import run_rag_provider_replay


def _install_fake_openai(monkeypatch, captured: dict) -> None:
    class FakeCompletions:
        def create(self, **kwargs):
            captured["request"] = kwargs
            return SimpleNamespace(
                id="ark-response-1",
                choices=[
                    SimpleNamespace(
                        finish_reason="stop",
                        message=SimpleNamespace(
                            content=(
                                '{"refused":false,"answer":"ok",'
                                '"assertions":[{"text":"ok",'
                                '"cited_sources":["python_requests.md"]}]}'
                            )
                        ),
                    )
                ],
                usage=SimpleNamespace(
                    prompt_tokens=10,
                    completion_tokens=8,
                    total_tokens=18,
                ),
            )

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))


def test_volcengine_replay_uses_ark_alias_default_endpoint_and_exact_model(
    monkeypatch,
):
    captured: dict = {}
    _install_fake_openai(monkeypatch, captured)
    monkeypatch.delenv("VOLCENGINE_API_KEY", raising=False)
    monkeypatch.setenv("ARK_API_KEY", "ark-secret")

    provider = VolcengineArkReplayProvider(
        model_profile="pro",
        model_name="ep-20260729-study-agent",
        temperature=0.0,
        max_tokens=700,
        timeout=60.0,
    )
    completion = provider.complete([{"role": "user", "content": "test"}])

    assert provider.provider_profile == "volcengine"
    assert provider.model_name == "ep-20260729-study-agent"
    assert captured["client"]["api_key"] == "ark-secret"
    assert captured["client"]["base_url"] == VOLCENGINE_ARK_BASE_URL
    assert captured["request"]["model"] == "ep-20260729-study-agent"
    assert captured["request"]["response_format"] == {"type": "json_object"}
    assert completion.provider_profile == "volcengine"
    assert completion.usage.total_tokens == 18
    assert len(completion.endpoint_fingerprint) == 16


def test_volcengine_specific_key_wins_over_ark_alias(monkeypatch):
    captured: dict = {}
    _install_fake_openai(monkeypatch, captured)
    monkeypatch.setenv("VOLCENGINE_API_KEY", "volcengine-secret")
    monkeypatch.setenv("ARK_API_KEY", "ark-secret")

    VolcengineArkReplayProvider(model_name="ep-model")

    assert captured["client"]["api_key"] == "volcengine-secret"


def test_volcengine_replay_rejects_missing_key_and_multiline_identity(monkeypatch):
    captured: dict = {}
    _install_fake_openai(monkeypatch, captured)
    monkeypatch.delenv("VOLCENGINE_API_KEY", raising=False)
    monkeypatch.delenv("ARK_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="API_KEY"):
        VolcengineArkReplayProvider(model_name="ep-model")

    monkeypatch.setenv("ARK_API_KEY", "ark-secret")
    with pytest.raises(RuntimeError, match="single line"):
        VolcengineArkReplayProvider(model_name="ep-model\nother")


def test_runner_routes_only_volcengine_to_replay_specific_adapter(monkeypatch):
    captured: dict = {}

    class FakeVolcengine:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(
        run_rag_provider_replay,
        "VolcengineArkReplayProvider",
        FakeVolcengine,
    )
    args = argparse.Namespace(
        model_profile="pro",
        temperature=0.0,
        max_tokens=700,
        timeout=60.0,
        model_name="ep-model",
        base_url=VOLCENGINE_ARK_BASE_URL,
    )

    provider = run_rag_provider_replay._build_provider(args, "volcengine")

    assert isinstance(provider, FakeVolcengine)
    assert captured["model_name"] == "ep-model"
    assert captured["base_url"] == VOLCENGINE_ARK_BASE_URL


def test_manual_workflow_has_bounded_smoke_and_full_modes():
    workflow = Path(".github/workflows/rag-provider-replay.yml").read_text(
        encoding="utf-8"
    )

    assert "replay_scope:" in workflow
    assert "- smoke" in workflow
    assert "- full" in workflow
    assert "SMOKE_CASE_ID: clean_requests_session" in workflow
    assert 'scope_args=(--case-id "$SMOKE_CASE_ID")' in workflow
    assert "inputs.replay_scope == 'full'" in workflow
    assert "Full replay must execute all 10 gold cases." in workflow
    assert "Smoke replay must execute exactly one case." in workflow


def test_manual_workflow_supports_volcengine_without_exposing_plan_endpoint():
    workflow = Path(".github/workflows/rag-provider-replay.yml").read_text(
        encoding="utf-8"
    )

    assert "- volcengine" in workflow
    assert "secrets.VOLCENGINE_API_KEY" in workflow
    assert "secrets.ARK_API_KEY" in workflow
    assert VOLCENGINE_ARK_BASE_URL in workflow
    assert "/api/plan/v3" not in workflow
    assert "/api/coding/v3" not in workflow

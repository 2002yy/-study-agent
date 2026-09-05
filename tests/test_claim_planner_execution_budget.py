from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

import src.web.research.claim_planner as claim_planner_module
from src.web.research.claim_planner import (
    CLAIM_PLANNER_MAX_ATTEMPTS_PER_INVOCATION,
    CLAIM_PLANNER_MAX_TOKENS,
    RuntimeClaimPlanner,
)
from src.web.research.contracts import ResearchBudget
from src.web.research.model_gateway import ResearchModelGateway


class _StructuredClient:
    def __init__(self, content: str) -> None:
        self.chat = SimpleNamespace(completions=self)
        self.content = content
        self.calls: list[dict[str, Any]] = []

    def with_options(self, **kwargs: Any) -> _StructuredClient:
        assert kwargs == {"max_retries": 0}
        return self

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self.content),
                    finish_reason="stop",
                )
            ],
            usage=SimpleNamespace(
                prompt_tokens=20,
                completion_tokens=30,
                total_tokens=50,
            ),
        )


class _FailIfCalledClient(_StructuredClient):
    def create(self, **kwargs: Any) -> Any:
        raise AssertionError(f"shared client must not be called: {kwargs}")


def _budget() -> ResearchBudget:
    return ResearchBudget(
        max_candidates=20,
        max_reads=8,
        soft_timeout_seconds=45,
        hard_timeout_seconds=60,
        max_total_chars=16000,
    )


def _valid_plan(*, fenced: bool = False) -> str:
    payload = json.dumps(
        {
            "schema_version": "research-runtime-claim-plan-v1",
            "claims": [
                {
                    "surface": "Verify the current official release date",
                    "kind": "factual",
                    "priority": "critical",
                    "policy_profile": "current_fact",
                }
            ],
        }
    )
    if fenced:
        return f"```json\n{payload}\n```"
    return payload


def _plan(planner: RuntimeClaimPlanner, *, attempt_start: int = 1) -> Any:
    return planner.plan(
        run_id="run_claim_planner_budget",
        question="What is the verified current release date?",
        reference_date="2026-09-05",
        budget=_budget(),
        mode="active",
        timeout_seconds=20,
        attempt_start=attempt_start,
    )


def test_planner_has_small_output_budget_schema_and_does_not_mutate_shared_retry_budget() -> None:
    client = _StructuredClient(_valid_plan(fenced=True))
    shared = ResearchModelGateway(
        client=client,
        model_name="shared-model",
        timeout_seconds=20,
    )

    planner = RuntimeClaimPlanner(shared)
    result = _plan(planner)

    assert result.completed
    assert len(client.calls) == 1
    assert client.calls[0]["max_tokens"] == CLAIM_PLANNER_MAX_TOKENS == 320
    response_format = client.calls[0]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"]["additionalProperties"] is False
    assert planner.model_gateway.max_attempts == CLAIM_PLANNER_MAX_ATTEMPTS_PER_INVOCATION == 1
    assert shared.max_attempts == 2


def test_planner_parse_failure_is_unavailable_without_immediate_retry_or_fabricated_claim() -> None:
    client = _StructuredClient("not-json")
    shared = ResearchModelGateway(
        client=client,
        model_name="shared-model",
        timeout_seconds=20,
    )

    result = _plan(RuntimeClaimPlanner(shared))

    assert result.status == "unavailable"
    assert result.state is None
    assert len(result.audits) == 1
    assert result.audits[0].status == "attempt_failed"
    assert result.audits[0].error_type == "JSONDecodeError"
    assert len(client.calls) == 1


def test_planner_durable_recovery_attempt_two_spends_exactly_one_model_call() -> None:
    client = _StructuredClient(_valid_plan())
    planner = RuntimeClaimPlanner(
        ResearchModelGateway(
            client=client,
            model_name="shared-model",
            timeout_seconds=20,
        )
    )

    result = _plan(planner, attempt_start=2)

    assert result.completed
    assert len(result.audits) == 1
    assert result.audits[0].attempt == 2
    assert len(client.calls) == 1


def test_planner_attempt_beyond_shared_durable_budget_fails_closed_without_call() -> None:
    client = _StructuredClient(_valid_plan())
    planner = RuntimeClaimPlanner(
        ResearchModelGateway(
            client=client,
            model_name="shared-model",
            timeout_seconds=20,
        )
    )

    result = _plan(planner, attempt_start=3)

    assert result.status == "unavailable"
    assert result.reason == "claim_plan_attempts_exhausted"
    assert result.state is None
    assert result.audits == ()
    assert client.calls == []


def test_shared_lazy_client_is_resolved_only_when_planner_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lazy_client = _StructuredClient(_valid_plan())
    resolutions: list[str] = []

    def fake_get_client(*, provider_profile: str) -> _StructuredClient:
        resolutions.append(provider_profile)
        return lazy_client

    monkeypatch.setattr(claim_planner_module, "get_client", fake_get_client)
    shared = ResearchModelGateway(
        provider_profile="openai",
        client=None,
        model_name="shared-model",
        timeout_seconds=20,
    )

    planner = RuntimeClaimPlanner(shared)
    assert resolutions == []

    result = _plan(planner)

    assert result.completed
    assert resolutions == ["openai"]
    assert len(lazy_client.calls) == 1
    assert lazy_client.calls[0]["response_format"]["type"] == "json_schema"
    assert shared._client is None  # noqa: SLF001


def test_dedicated_planner_endpoint_routes_only_planner_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dedicated = _StructuredClient(_valid_plan())
    created: list[dict[str, Any]] = []

    def fake_openai(**kwargs: Any) -> _StructuredClient:
        created.append(kwargs)
        return dedicated

    monkeypatch.setenv("RESEARCH_CLAIM_PLANNER_BASE_URL", "http://127.0.0.1:8001/v1")
    monkeypatch.setenv("RESEARCH_CLAIM_PLANNER_MODEL_NAME", "fast-planner")
    monkeypatch.setenv("RESEARCH_CLAIM_PLANNER_API_KEY", "local")
    monkeypatch.setattr(claim_planner_module, "OpenAI", fake_openai)

    shared_client = _FailIfCalledClient(_valid_plan())
    shared = ResearchModelGateway(
        client=shared_client,
        model_name="shared-4b",
        timeout_seconds=20,
    )
    planner = RuntimeClaimPlanner(shared)

    result = _plan(planner)

    assert result.completed
    assert created == [
        {
            "api_key": "local",
            "base_url": "http://127.0.0.1:8001/v1",
            "max_retries": 0,
        }
    ]
    assert len(dedicated.calls) == 1
    assert dedicated.calls[0]["model"] == "fast-planner"
    assert dedicated.calls[0]["response_format"]["type"] == "json_schema"
    assert shared_client.calls == []
    assert shared.max_attempts == 2


def test_partial_dedicated_planner_configuration_fails_fast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RESEARCH_CLAIM_PLANNER_BASE_URL", "http://127.0.0.1:8001/v1")
    monkeypatch.delenv("RESEARCH_CLAIM_PLANNER_MODEL_NAME", raising=False)
    monkeypatch.delenv("RESEARCH_CLAIM_PLANNER_API_KEY", raising=False)

    shared = ResearchModelGateway(
        client=_StructuredClient(_valid_plan()),
        model_name="shared-model",
        timeout_seconds=20,
    )

    with pytest.raises(RuntimeError, match="dedicated claim planner requires"):
        RuntimeClaimPlanner(shared)

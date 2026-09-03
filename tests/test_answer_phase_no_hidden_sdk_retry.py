"""Hidden SDK-retry audit tests (RQ1-C pre-push P0-2).

The OpenAI-compatible SDK client is configured with ``max_retries`` from
provider settings (default 2, env ``LLM_MAX_RETRIES``), which would silently
turn one method call into multiple physical outbound requests.  The answer
stage (answer generation + answer claim binding) therefore calls
``chat/stream_chat/async_stream_chat`` with ``request_max_retries=0`` so that
one method call is exactly one physical outbound attempt and the
turn-level audit stays authoritative.  Other callers keep the SDK default.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any


from src import llm_client

_ANSWER = "ok"


def _response() -> Any:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=_ANSWER))]
    )


class _FakeChatCompletions:
    def __init__(self, record: dict[str, Any]) -> None:
        self.record = record

    def create(self, **kwargs: Any) -> Any:
        self.record["stream"] = kwargs.get("stream", False)
        return _response()


class _FakeChatClient:
    def __init__(self, record: dict[str, Any]) -> None:
        self.record = record
        self.chat = SimpleNamespace()
        self.chat.completions = _FakeChatCompletions(record)

    def with_options(self, **options: Any) -> "_FakeChatClient":
        self.record["with_options"] = dict(options)
        return self


def test_chat_retry_zero_forces_sdk_with_options_retry_zero(monkeypatch) -> None:
    record: dict[str, Any] = {}
    fake = _FakeChatClient(record)
    monkeypatch.setattr(llm_client, "get_client", lambda provider_profile=None: fake)
    monkeypatch.setattr(
        llm_client,
        "_build_request_kwargs",
        lambda **kwargs: {"messages": kwargs["messages"]},
    )
    result = llm_client.chat(
        [{"role": "user", "content": "q"}],
        task_name="answer_claim_binding",
        request_max_retries=0,
    )
    assert result == _ANSWER
    assert record["with_options"] == {"max_retries": 0}


def test_chat_without_retry_override_keeps_sdk_default(monkeypatch) -> None:
    record: dict[str, Any] = {}
    fake = _FakeChatClient(record)
    monkeypatch.setattr(llm_client, "get_client", lambda provider_profile=None: fake)
    monkeypatch.setattr(
        llm_client,
        "_build_request_kwargs",
        lambda **kwargs: {"messages": kwargs["messages"]},
    )
    llm_client.chat([{"role": "user", "content": "q"}], task_name="single_chat")
    assert "with_options" not in record


def test_stream_chat_retry_zero_forces_sdk_with_options(monkeypatch) -> None:
    record: dict[str, Any] = {}
    fake = _FakeChatClient(record)
    monkeypatch.setattr(llm_client, "get_client", lambda provider_profile=None: fake)
    monkeypatch.setattr(
        llm_client,
        "_build_request_kwargs",
        lambda **kwargs: {
            "messages": kwargs["messages"],
            "stream": kwargs.get("stream", False),
        },
    )

    def chunks(**kwargs: Any) -> Any:
        record["stream"] = kwargs.get("stream", False)
        yield SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content="tok"))]
        )

    completions = _FakeChatCompletions(record)
    completions.create = chunks
    fake.chat.completions = completions

    collected = list(
        llm_client.stream_chat(
            [{"role": "user", "content": "q"}], request_max_retries=0
        )
    )
    assert collected == ["tok"]
    assert record["with_options"] == {"max_retries": 0}
    assert record["stream"] is True


def test_provider_settings_document_sdk_retry_default() -> None:
    """Code evidence: the shared SDK client defaults to two retries, which is
    exactly why the answer stage must opt out per call."""
    import inspect

    source = inspect.getsource(llm_client.get_provider_settings)
    assert "LLM_MAX_RETRIES" in source
    assert "default=2" in source

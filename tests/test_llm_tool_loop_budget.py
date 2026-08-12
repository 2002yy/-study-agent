from __future__ import annotations

from types import SimpleNamespace

from src.llm_client import run_tool_loop


def test_tool_loop_can_disable_provider_retries(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class Completions:
        def create(self, **_kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[]))]
            )

    class Client:
        def __init__(self) -> None:
            self.chat = SimpleNamespace(completions=Completions())

        def with_options(self, *, max_retries: int):
            captured["max_retries"] = max_retries
            return self

    monkeypatch.setattr("src.llm_client.get_client", lambda **_kwargs: Client())

    result = run_tool_loop(
        [{"role": "user", "content": "bounded research"}],
        tools=[{"type": "function", "function": {"name": "web_search"}}],
        execute_tool=lambda _name, _arguments: {},
        request_max_retries=0,
    )

    assert result == []
    assert captured["max_retries"] == 0

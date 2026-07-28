from __future__ import annotations

from src.mode_manager import RuntimeModes
from src.task_contract import route_request_with_task_contract


def _route(*, user_input: str, selected_mode: str = "auto") -> dict:
    return route_request_with_task_contract(
        user_input=user_input,
        selected_role="auto",
        selected_mode=selected_mode,
        selected_model="auto",
        runtime_modes=RuntimeModes(performance_mode="fast"),
        previous_role=None,
        previous_mode=None,
        keep_current_role=False,
    )


def test_automatic_system_learning_enters_socratic_protocol():
    route = _route(user_input="带我系统学习二分查找复杂度")

    assert route["task_contract"]["task_intent"] == "learn"
    assert route["task_contract"]["learning_state_enabled"] is True
    assert route["mode"] == "苏格拉底"


def test_manual_direct_mode_still_wins_for_system_learning():
    route = _route(
        user_input="带我系统学习二分查找复杂度",
        selected_mode="普通",
    )

    assert route["task_contract"]["task_intent"] == "learn"
    assert route["mode"] == "普通"

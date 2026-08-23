"""G18 deep research: multi-round WebLookupRun pipeline tests.

Contract: docs/PROJECT_STATUS.md section 11 (decisions 1-16). Real
WebLookupRepository against a temporary SQLite database; gateway and planner
are scripted fakes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.web_lookup_service import WebLookupService
from src.infrastructure.sqlite.database import RuntimeDatabase
from src.repositories.web_lookup_repository import WebLookupRepository


class ScriptedGateway:
    """Deterministic gateway: search results keyed by substring, read keyed by url."""

    def __init__(self, search_map: dict[str, list[dict]], fail_reads: set[str] | None = None):
        self.search_map = {key.lower(): value for key, value in search_map.items()}
        self.fail_reads = fail_reads or set()
        self.search_calls: list[str] = []
        self.read_calls: list[str] = []

    def search(self, query: str, *, max_items: int = 10) -> list[dict]:
        self.search_calls.append(query)
        for key, results in self.search_map.items():
            if key in query.lower():
                # Echo the query into title/snippet so assess_sources marks
                # the result relevant (directness != unmatched).
                echoed = []
                for item in results[:max_items]:
                    record = dict(item)
                    record["title"] = f"{query} - {record.get('title', '')}"
                    record["snippet"] = f"{query}: {record.get('snippet', '')}"
                    echoed.append(record)
                return echoed
        return []

    def read(self, url: str, *, max_chars: int = 6000) -> dict:
        self.read_calls.append(url)
        if url in self.fail_reads:
            raise RuntimeError("deterministic read failure")
        return {
            "ok": True,
            "url": url,
            "content": f"Deterministic content for {url}. " * 3,
        }

    def warnings(self) -> list[dict[str, str]]:
        return []


class ScriptedPlanner:
    """plan() returns the initial decomposition; revise() drives round count."""

    def __init__(
        self,
        initial: list[str],
        revisions: list[dict] | None = None,
    ):
        self.initial = initial
        self.revisions = list(revisions or [])

    def plan(self, query: str, context) -> list[str]:
        return list(self.initial)

    def revise(self, memo: str, notes, remaining):
        if self.revisions:
            verdict = self.revisions.pop(0)
            return {
                "done": verdict.get("done", False),
                "additional": verdict.get("additional", []),
            }
        return {"done": True, "additional": []}


def _service(
    tmp_path: Path,
    gateway: ScriptedGateway,
    planner: ScriptedPlanner | None = None,
) -> WebLookupService:
    repository = WebLookupRepository(RuntimeDatabase(tmp_path / "runtime.db"))
    return WebLookupService(repository, gateway, planner=planner)


def _result(url: str, title: str) -> dict:
    return {
        "title": title,
        "url": url,
        "source": "Test source",
        "snippet": f"Evidence snippet from {title}",
    }


def test_deep_run_produces_notes_memo_and_rounds(tmp_path):
    gateway = ScriptedGateway(
        {
            "deep topic sub one": [_result("https://a.test/1", "Source One")],
            "deep topic sub two": [_result("https://b.test/2", "Source Two")],
            "additional deep topic": [_result("https://d.test/9", "Added Source")],
        }
    )
    planner = ScriptedPlanner(
        initial=["deep topic sub one", "deep topic sub two"],
        # Decision 9: after round 1 the planner finds a gap and inserts a
        # new sub-question; round 2 researches it and closes the run.
        revisions=[
            {"done": False, "additional": ["additional deep topic"]},
            {"done": True},
        ],
    )
    service = _service(tmp_path, gateway, planner)
    run = service.create("deep topic", research_mode="deep")
    assert run.research_context["research_mode"] == "deep"
    assert run.research_context["deep"]["steering"] == []

    completed = service.execute(run.id)
    assert completed.status == "completed"
    deep = completed.research_context["deep"]
    assert len(deep["plan"]) == 3
    added = [task for task in deep["plan"] if task["task_id"] == "a1_1"]
    assert added and added[0]["status"] == "done"
    assert all(task["status"] == "done" for task in deep["plan"])
    assert deep["round_index"] >= 2
    assert len(deep["notes"]) >= 2
    assert "Deterministic content" in deep["memo"]
    # Both sub-questions were searched at least once each.
    assert len(gateway.search_calls) >= 2
    assert any("deep topic sub one" in call for call in gateway.search_calls)
    assert any("deep topic sub two" in call for call in gateway.search_calls)
    assert any("additional deep topic" in call for call in gateway.search_calls)


def test_steering_before_execution_marks_influenced_by_steering(tmp_path):
    gateway = ScriptedGateway(
        {"focus area": [_result("https://c.test/3", "Steered Source - steered topic focus area")]}
    )
    planner = ScriptedPlanner(initial=["steered topic focus area"])
    service = _service(tmp_path, gateway, planner)
    run = service.create("steered topic", research_mode="deep")

    # Inject steering before execution: it must be consumed in round 1.
    steered = service.steer(run.id, content="重点看 X 方向")
    assert steered is not None
    deep = steered.research_context["deep"]
    assert deep["steering"][0]["incorporated_in_round"] is None

    completed = service.execute(run.id)
    assert completed.status == "completed"
    deep = completed.research_context["deep"]
    consumed = deep["steering"][0]
    assert consumed["incorporated_in_round"] == 1
    # Audit marker propagates to attempts and sources created in round 1.
    marked_attempts = [
        attempt
        for attempt in completed.query_attempts
        if attempt.get("influenced_by_steering")
    ]
    assert marked_attempts, "steered round attempts must carry the marker"


def test_steer_rejects_settled_run(tmp_path):
    gateway = ScriptedGateway({"idle": [_result("https://i.test/7", "Idle")]})
    service = _service(tmp_path, gateway)
    run = service.create("idle topic", research_mode="deep")
    completed = service.execute(run.id)
    assert completed.status == "completed"
    with pytest.raises(ValueError):
        service.steer(run.id, content="too late")


def test_retry_once_then_skip_on_empty_results(tmp_path):
    # Only "good question" has results; the other sub-question gets both its
    # queries empty → skipped with a gap note, run still completes.
    gateway = ScriptedGateway({"good": [_result("https://g.test/4", "Good Source")]})
    planner = ScriptedPlanner(initial=["good deep topic", "hopeless deep topic"])
    service = _service(tmp_path, gateway, planner)
    run = service.create("mixed topic", research_mode="deep")

    completed = service.execute(run.id)
    assert completed.status == "completed"
    deep = completed.research_context["deep"]
    statuses = {task["sub_question"]: task["status"] for task in deep["plan"]}
    assert statuses["good deep topic"] == "done"
    assert statuses["hopeless deep topic"] == "skipped"
    # Retry-once: two queries attempted for the hopeless sub-question.
    hopeless_queries = [
        call for call in gateway.search_calls if 'hopeless' in call.lower()
    ]
    assert len(hopeless_queries) == 2


def test_standard_mode_unchanged(tmp_path):
    gateway = ScriptedGateway({"standard": [_result("https://s.test/5", "Std")]})
    repository = WebLookupRepository(RuntimeDatabase(tmp_path / "runtime.db"))
    service = WebLookupService(repository, gateway)
    run = service.create("standard topic")
    assert run.research_context.get("research_mode", "standard") == "standard"
    assert "deep" not in run.research_context
    completed = service.execute(run.id)
    assert completed.status == "completed"
    # Standard path never produces deep structures.
    assert "deep" not in completed.research_context


def test_planning_stage_recorded_in_stage_history(tmp_path):
    gateway = ScriptedGateway({"topic": [_result("https://p.test/6", "Plan Source")]})
    planner = ScriptedPlanner(initial=["Topic question"])
    service = _service(tmp_path, gateway, planner)
    run = service.create("planned topic", research_mode="deep")
    completed = service.execute(run.id)
    # Final stage is completed; steps log records the planning entry.
    steps = completed.research_context["deep"]["steps"]
    kinds = [step["kind"] for step in steps]
    assert "planning" in kinds
    assert "round" in kinds

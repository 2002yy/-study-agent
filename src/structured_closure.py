"""Evidence-linked generator and candidate normalization for G2 closure input."""

from __future__ import annotations

import json
from typing import Any

from src.llm_client import ModelProfile, chat
from src.text_utils import strip_code_fences

STRUCTURED_CLOSURE_SCHEMA_VERSION = "learning-closure-candidates-v1"
_ALLOWED_TARGETS: dict[str, bool] = {
    "progress": True,
    "learner_profile": True,
    "current_focus": False,
    "project_context": True,
    "revision_notes": True,
    "session_archive": True,
}
_ALLOWED_CONFIDENCE = {"low", "medium", "high"}
_DURABLE_CLAIM_KINDS = {
    "mechanism",
    "boundary",
    "invariant",
    "decision_relevant_fact",
}
_DURABLE_SCOPES = {"project", "general"}
_NO_UPDATE_MARKERS = {
    "",
    "本轮无需更新",
    "（本轮无需更新）",
    "无更新",
}
_MEMORY_CHAR_LIMIT = 2400
_DURABLE_CLAIM_CHAR_LIMIT = 800
_DURABLE_NEXT_STEP_CHAR_LIMIT = 600

_SYSTEM_PROMPT = """你是学习系统的结构化整理生成器。
只允许根据输入 JSON 中的 committed_learning_state、committed_project_state、final_pedagogy_evaluation、evidence_ids、github_learning_sources、recent_dialogue 和 memory_context 生成候选。
不得把 excluded_uncommitted_turns、失败回合、planned state、用户仅口头声称“懂了”当作掌握证据。
confirmed_points 只能用于旧记忆整理，绝不能直接升级成 durable Claim；项目里程碑、交付物、测试结果和阻塞项只能来自 committed_project_state。
最终评估不是 accept 时，不得把其内容写成已掌握；project_validation_passed 不为 true 时，不得声称项目验证通过。
learner_profile 候选必须 learner_pending=true，不得诊断心理、健康或敏感属性。
每个普通记忆候选必须给出 allowed_source_refs 中的 source_refs；没有来源就不要生成该候选。

对于源码学习，可以额外输出最多一个 durable_learning_candidate，但必须同时满足：
1. summary_kind 必须是 learning_summary；
2. final_pedagogy_evaluation.learner_input 中存在一个具体、可核验的源码事实陈述，而不是“懂了/会了”之类自述；
3. github_learning_sources 中存在与该陈述直接相关的 commit-pinned source；
4. source_ref 必须原样选择 github_learning_sources 里的 source_ref；不要自己填写 repo/query/commit；
5. claim_text 只能提炼用户这次被评估的事实陈述，不能把助手新解释、confirmed_points 或模型推测冒充用户理解；
6. claim_kind 只能是 mechanism|boundary|invariant|decision_relevant_fact；证据是否足够由后端重新 convergence 决定，你不能宣称 confirmed/mastered。
不满足任一条件时 durable_learning_candidate 必须为 null。

严格输出一个 JSON 对象，不要 markdown：
{
  "schema_version": "learning-closure-candidates-v1",
  "summary_kind": "learning_summary 或 project_closure",
  "candidates": [
    {
      "target": "progress|learner_profile|current_focus|project_context|revision_notes|session_archive",
      "content": "简洁、可确认的候选内容",
      "confidence": "low|medium|high",
      "source_refs": ["allowed_source_refs 中的值"],
      "evaluation_refs": ["PedagogyEvalRun id，可为空"],
      "learner_pending": false
    }
  ],
  "durable_learning_candidate": {
    "source_ref": "github_learning_sources 中的 source_ref",
    "claim_text": "用户本轮明确表达、等待源码证据收敛的事实命题",
    "claim_kind": "mechanism|boundary|invariant|decision_relevant_fact",
    "scope": "project|general",
    "next_step": "若本轮不能闭合，下一步最小学习动作，可为空"
  }
}
没有可靠普通候选时 candidates 为空数组；没有可靠 durable 候选时 durable_learning_candidate 为 null。不要输出 role_updates。"""


def generate_structured_closure_candidates(
    structured_input: dict[str, Any],
    memory_bundle: dict[str, str],
    role: str,
    mode: str,
    model_profile: ModelProfile = "pro",
) -> dict[str, Any]:
    """Call the model with bounded structured evidence, never the full transcript."""

    payload = dict(structured_input)
    frozen_memory = structured_input.get("memory_context")
    memory_context = (
        bounded_memory_context(
            {str(key): str(value) for key, value in frozen_memory.items()}
        )
        if isinstance(frozen_memory, dict)
        else bounded_memory_context(memory_bundle)
    )
    allowed_refs = {
        str(item)
        for item in structured_input.get("allowed_source_refs", [])
        if str(item).strip()
    }
    allowed_refs.update(f"memory:{filename}" for filename in memory_context)
    payload["allowed_source_refs"] = sorted(allowed_refs)
    payload["memory_context"] = memory_context
    payload["voice_context"] = {"role": role, "mode": mode}
    raw = chat(
        [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False, sort_keys=True),
            },
        ],
        temperature=0.0,
        model_profile=model_profile,
        response_format="json_object",
        task_name="structured_learning_closure",
    )
    data = _parse_object(raw)
    return normalize_structured_closure_result(data, structured_input=payload)


def normalize_structured_closure_result(
    value: dict[str, Any],
    *,
    structured_input: dict[str, Any],
) -> dict[str, Any]:
    allowed_refs = {
        str(item)
        for item in structured_input.get("allowed_source_refs", [])
        if str(item).strip()
    }
    final_evaluation = structured_input.get("final_pedagogy_evaluation")
    final_evaluation_id = (
        str(final_evaluation.get("id"))
        if isinstance(final_evaluation, dict) and final_evaluation.get("id")
        else ""
    )
    final_decision = (
        str(final_evaluation.get("final_decision"))
        if isinstance(final_evaluation, dict)
        else ""
    )
    project_state = structured_input.get("committed_project_state")
    project_validation_passed = bool(
        isinstance(project_state, dict)
        and project_state.get("project_validation_passed") is True
    )
    candidates: list[dict[str, Any]] = []
    raw_candidates = value.get("candidates")
    if not isinstance(raw_candidates, list):
        raise ValueError("Structured closure result must contain candidates[]")
    seen_targets: set[str] = set()
    for raw in raw_candidates:
        if not isinstance(raw, dict):
            continue
        target = str(raw.get("target") or "").strip()
        content = str(raw.get("content") or "").strip()
        if target not in _ALLOWED_TARGETS or content in _NO_UPDATE_MARKERS:
            continue
        if target in seen_targets:
            continue
        source_refs = _valid_refs(raw.get("source_refs"), allowed_refs)
        if not source_refs or not _target_is_grounded(
            target,
            source_refs,
            final_evaluation_id=final_evaluation_id,
            final_decision=final_decision,
        ):
            continue
        evaluation_source_ref = (
            f"pedagogy_eval:{final_evaluation_id}"
            if final_evaluation_id
            else ""
        )
        evaluation_refs: list[str] = []
        if evaluation_source_ref and evaluation_source_ref in source_refs:
            evaluation_refs = _evaluation_refs(
                raw.get("evaluation_refs"),
                final_evaluation_id=final_evaluation_id,
            )
            if final_evaluation_id not in evaluation_refs:
                evaluation_refs.append(final_evaluation_id)
        confidence = str(raw.get("confidence") or "low").strip().lower()
        if confidence not in _ALLOWED_CONFIDENCE:
            confidence = "low"
        has_accepted_evaluation = (
            final_decision == "accept"
            and final_evaluation_id in evaluation_refs
        )
        if confidence == "high" and not _allows_high_confidence(
            target,
            source_refs,
            has_accepted_evaluation=has_accepted_evaluation,
            project_validation_passed=project_validation_passed,
        ):
            confidence = "medium"
        learner_pending = target == "learner_profile" or raw.get("learner_pending") is True
        candidates.append(
            {
                "target": target,
                "content": content,
                "confidence": confidence,
                "source_refs": source_refs,
                "evaluation_refs": sorted(evaluation_refs),
                "learner_pending": learner_pending,
            }
        )
        seen_targets.add(target)

    durable_candidate = _normalize_durable_learning_candidate(
        value.get("durable_learning_candidate"),
        structured_input=structured_input,
    )
    return {
        "schema_version": STRUCTURED_CLOSURE_SCHEMA_VERSION,
        "summary_kind": str(structured_input.get("summary_kind") or "learning_summary"),
        "input_schema_version": str(structured_input.get("schema_version") or ""),
        "candidates": candidates,
        "candidate_count": len(candidates),
        "durable_learning_candidate": durable_candidate,
    }


def structured_candidates_to_memory_updates(
    generated: dict[str, Any],
) -> list[dict[str, Any]]:
    """Freeze candidate provenance into the MemoryRun payload."""

    updates: list[dict[str, Any]] = []
    candidates = generated.get("candidates")
    if not isinstance(candidates, list):
        return updates
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        target = str(candidate.get("target") or "")
        content = str(candidate.get("content") or "").strip()
        if target not in _ALLOWED_TARGETS or not content:
            continue
        updates.append(
            {
                "target": target,
                "content": content,
                "append": _ALLOWED_TARGETS[target],
                "learner_pending": target == "learner_profile"
                or candidate.get("learner_pending") is True,
                "confidence": str(candidate.get("confidence") or "low"),
                "source_refs": list(candidate.get("source_refs") or []),
                "evaluation_refs": list(candidate.get("evaluation_refs") or []),
                "provenance_schema_version": STRUCTURED_CLOSURE_SCHEMA_VERSION,
            }
        )
    return updates


def _normalize_durable_learning_candidate(
    value: object,
    *,
    structured_input: dict[str, Any],
) -> dict[str, str] | None:
    if str(structured_input.get("summary_kind") or "") != "learning_summary":
        return None
    if not isinstance(value, dict):
        return None
    evaluation = structured_input.get("final_pedagogy_evaluation")
    if not isinstance(evaluation, dict):
        return None
    learner_input = _bounded_text(evaluation.get("learner_input"), _DURABLE_CLAIM_CHAR_LIMIT)
    deterministic = evaluation.get("deterministic_result")
    semantic = evaluation.get("semantic_result")
    is_claim = bool(isinstance(deterministic, dict) and deterministic.get("is_claim") is True)
    semantic_claims = (
        semantic.get("claims")
        if isinstance(semantic, dict) and isinstance(semantic.get("claims"), (list, tuple))
        else ()
    )
    if not learner_input or not (is_claim or semantic_claims):
        return None

    source_ref = str(value.get("source_ref") or "").strip()
    source_map = {
        str(item.get("source_ref") or ""): item
        for item in structured_input.get("github_learning_sources", [])
        if isinstance(item, dict) and str(item.get("source_ref") or "").strip()
    }
    if source_ref not in source_map:
        return None

    claim_text = _bounded_text(value.get("claim_text"), _DURABLE_CLAIM_CHAR_LIMIT)
    claim_kind = str(value.get("claim_kind") or "").strip()
    scope = str(value.get("scope") or "project").strip()
    if not claim_text or claim_kind not in _DURABLE_CLAIM_KINDS or scope not in _DURABLE_SCOPES:
        return None

    return {
        "source_ref": source_ref,
        "claim_text": claim_text,
        "claim_kind": claim_kind,
        "scope": scope,
        "next_step": _bounded_text(value.get("next_step"), _DURABLE_NEXT_STEP_CHAR_LIMIT),
        "evaluation_id": str(evaluation.get("id") or "").strip(),
        "evaluation_turn_id": str(evaluation.get("turn_id") or "").strip(),
    }


def _parse_object(raw: str) -> dict[str, Any]:
    cleaned = strip_code_fences(raw)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError("Structured closure model returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Structured closure model returned a non-object")
    return parsed


def bounded_memory_context(memory_bundle: dict[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for filename in (
        "progress.md",
        "learner_profile.md",
        "current_focus.md",
        "project_context.md",
    ):
        content = str(memory_bundle.get(filename) or "").strip()
        if not content or content.startswith("[文件不存在"):
            continue
        result[filename] = (
            content
            if len(content) <= _MEMORY_CHAR_LIMIT
            else content[: _MEMORY_CHAR_LIMIT - 1].rstrip() + "…"
        )
    return result


def _valid_refs(value: Any, allowed_refs: set[str]) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(
        {
            str(item)
            for item in value
            if str(item).strip() and str(item) in allowed_refs
        }
    )


def _evaluation_refs(value: Any, *, final_evaluation_id: str) -> list[str]:
    if not final_evaluation_id or not isinstance(value, list):
        return []
    return [final_evaluation_id] if final_evaluation_id in {str(item) for item in value} else []


def _target_is_grounded(
    target: str,
    source_refs: list[str],
    *,
    final_evaluation_id: str,
    final_decision: str,
) -> bool:
    refs = set(source_refs)
    accepted_eval_ref = bool(
        final_evaluation_id
        and final_decision == "accept"
        and f"pedagogy_eval:{final_evaluation_id}" in refs
    )
    if target == "progress":
        return accepted_eval_ref or bool(
            refs
            & {
                "learning_state.objective",
                "learning_state.confirmed_points",
                "learning_state.unresolved_gap",
                "learning_state.phase",
                "project_state.current_stage",
                "project_state.completed_deliverables",
                "project_state.failed_tests",
                "project_state.blockers",
                "project_state.milestones",
                "project_state.project_validation_passed",
                "memory:progress.md",
            }
        )
    if target == "current_focus":
        return accepted_eval_ref or bool(
            refs
            & {
                "learning_state.objective",
                "learning_state.unresolved_gap",
                "learning_state.phase",
                "project_state.objective",
                "project_state.current_stage",
                "project_state.next_action",
                "project_state.failed_tests",
                "project_state.blockers",
                "project_state.validation_required",
                "memory:current_focus.md",
                "memory:progress.md",
            }
        )
    if target == "project_context":
        return any(ref.startswith("project_state.") for ref in refs) or bool(
            refs & {"memory:project_context.md"}
        )
    return True


def _allows_high_confidence(
    target: str,
    source_refs: list[str],
    *,
    has_accepted_evaluation: bool,
    project_validation_passed: bool,
) -> bool:
    refs = set(source_refs)
    if has_accepted_evaluation:
        return True
    if target == "progress":
        if refs & {
            "learning_state.confirmed_points",
            "memory:progress.md",
            "project_state.completed_deliverables",
            "project_state.milestones",
        }:
            return True
        return bool(
            project_validation_passed
            and "project_state.project_validation_passed" in refs
        )
    if target == "project_context":
        return any(ref.startswith("project_state.") for ref in refs) or bool(
            refs & {"memory:project_context.md"}
        )
    return any(
        ref.startswith("learning_state.")
        or ref.startswith("project_state.")
        or ref.startswith("memory:")
        for ref in refs
    )


def _bounded_text(value: object, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip() + "…"

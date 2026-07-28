import type { LearningClosureRunResponse } from "./closureTypes";

export type ClosureCandidate = {
  target: string;
  content: string;
  confidence?: string;
  source_refs?: string[];
  evaluation_refs?: string[];
  learner_pending?: boolean;
};

export type ClosureReviewModel = {
  objective: string;
  confirmedPoints: string[];
  unresolvedGap: string;
  nextAction: string;
  saveItems: ClosureCandidate[];
  summaryKind: "learning" | "project";
};

const TARGET_LABELS: Record<string, string> = {
  current_focus: "下次继续入口",
  progress: "学习进展",
  summary: "长期摘要",
  learner_profile: "学习偏好观察",
  project_context: "项目背景",
  revision_notes: "待补强内容",
  session_archive: "本次学习归档",
};

export function memoryTargetLabel(target: string): string {
  return TARGET_LABELS[target] ?? "长期学习成果";
}

export function memoryActionLabel(action: string): string {
  const normalized = action.trim().toLowerCase();
  if (normalized.includes("replace")) return "替换";
  if (normalized.includes("append")) return "追加";
  if (normalized.includes("create")) return "新建";
  return "更新";
}

export function memoryConfidenceLabel(confidence?: string): string {
  return (
    {
      high: "高",
      medium: "中",
      low: "低",
    }[confidence ?? ""] ?? "未标注"
  );
}

export function closureCandidates(
  closureRun: LearningClosureRunResponse | null,
): ClosureCandidate[] {
  const raw = closureRun?.generated_result.candidates;
  if (!Array.isArray(raw)) return [];
  return raw.filter(
    (candidate): candidate is ClosureCandidate =>
      Boolean(
        candidate &&
          typeof candidate === "object" &&
          typeof (candidate as ClosureCandidate).target === "string" &&
          typeof (candidate as ClosureCandidate).content === "string" &&
          (candidate as ClosureCandidate).content.trim(),
      ),
  );
}

export function buildClosureReview(
  closureRun: LearningClosureRunResponse,
): ClosureReviewModel {
  const snapshot = asRecord(closureRun.committed_snapshot);
  const structuredInput = asRecord(snapshot.structured_input);
  const learningState = asRecord(structuredInput.committed_learning_state);
  const projectState = asRecord(structuredInput.committed_project_state);
  const candidates = closureCandidates(closureRun);

  const confirmedPoints = uniqueStrings([
    ...stringList(learningState.confirmed_points),
    ...stringList(projectState.completed_deliverables),
    ...stringList(projectState.milestones),
  ]);
  const projectGaps = uniqueStrings([
    ...stringList(projectState.blockers),
    ...stringList(projectState.failed_tests),
  ]);
  const nextCandidate =
    candidates.find((candidate) => candidate.target === "current_focus") ??
    candidates.find((candidate) => candidate.target === "revision_notes");

  return {
    objective:
      stringValue(learningState.objective) ||
      stringValue(projectState.objective) ||
      (closureRun.closure_eligibility === "project_summary" ? "本次项目推进" : "本次学习"),
    confirmedPoints,
    unresolvedGap:
      stringValue(learningState.unresolved_gap) ||
      projectGaps.join("；") ||
      "暂无已记录缺口",
    nextAction:
      stringValue(projectState.next_action) ||
      nextCandidate?.content.trim() ||
      "尚未形成明确的下一步",
    saveItems: candidates,
    summaryKind:
      closureRun.closure_eligibility === "project_summary" ? "project" : "learning",
  };
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter(Boolean);
}

function uniqueStrings(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))];
}

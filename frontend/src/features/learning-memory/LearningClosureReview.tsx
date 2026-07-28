import { Archive, CheckCircle2, Compass, MessageCircle, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";

import type { MemoryRunResponse } from "../../types";
import type { LearningClosureRunResponse } from "./closureTypes";

type ClosureCandidate = {
  target: string;
  content: string;
  learner_pending?: boolean;
};

export type ClosureReviewModel = {
  confirmed: string[];
  unresolved: string[];
  next: string[];
  impactLabels: string[];
};

const IMPACT_LABELS: Record<string, string> = {
  current_focus: "下一次继续学习的重点",
  progress: "已经确认的学习进展",
  summary: "长期学习摘要",
  learner_profile: "待你确认的学习偏好",
  project_context: "项目背景与长期约束",
  revision_notes: "仍需补强的内容",
  session_archive: "本次学习归档",
};

function candidatesFrom(run: LearningClosureRunResponse): ClosureCandidate[] {
  const raw = run.generated_result.candidates;
  if (!Array.isArray(raw)) return [];
  return raw.filter(
    (candidate): candidate is ClosureCandidate =>
      Boolean(
        candidate &&
          typeof candidate === "object" &&
          typeof candidate.target === "string" &&
          typeof candidate.content === "string" &&
          candidate.content.trim(),
      ),
  );
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

function unique(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean)));
}

export function buildClosureReviewModel(
  run: LearningClosureRunResponse,
  memoryRun: MemoryRunResponse | null,
): ClosureReviewModel {
  const candidates = candidatesFrom(run);
  const committedSnapshot = asRecord(run.committed_snapshot);
  const structuredInput = asRecord(committedSnapshot.structured_input);
  const committedLearning = asRecord(structuredInput.committed_learning_state);
  const committedProject = asRecord(structuredInput.committed_project_state);
  const hasCommittedState =
    Object.keys(committedLearning).length > 0 || Object.keys(committedProject).length > 0;

  const confirmed = hasCommittedState
    ? unique([
        ...stringList(committedLearning.confirmed_points),
        ...stringList(committedProject.completed_deliverables),
        ...stringList(committedProject.milestones),
      ])
    : unique(
        candidates
          .filter(
            (candidate) =>
              candidate.target !== "current_focus" &&
              candidate.target !== "revision_notes" &&
              candidate.target !== "learner_profile" &&
              !candidate.learner_pending,
          )
          .map((candidate) => candidate.content.trim()),
      );

  const unresolved = hasCommittedState
    ? unique([
        stringValue(committedLearning.unresolved_gap),
        ...stringList(committedProject.blockers),
        ...stringList(committedProject.failed_tests),
      ])
    : unique(
        candidates
          .filter(
            (candidate) =>
              candidate.target === "revision_notes" ||
              candidate.target === "learner_profile" ||
              candidate.learner_pending,
          )
          .map((candidate) => candidate.content.trim()),
      );

  const next = unique([
    stringValue(committedProject.next_action),
    ...candidates
      .filter((candidate) => candidate.target === "current_focus")
      .map((candidate) => candidate.content.trim()),
  ]);

  const impactLabels = Array.from(
    new Set(
      (memoryRun?.updates ?? []).map(
        (update) => IMPACT_LABELS[update.target] ?? "长期学习记录",
      ),
    ),
  );

  return { confirmed, unresolved, next, impactLabels };
}

function ReviewSection({
  icon,
  title,
  items,
  empty,
}: {
  icon: ReactNode;
  title: string;
  items: string[];
  empty: string;
}) {
  return (
    <section className="closure-review-section">
      <div className="closure-review-section-title">
        {icon}
        <h3>{title}</h3>
      </div>
      {items.length ? (
        <ul>
          {items.map((item, index) => (
            <li key={`${title}-${index}`}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="closure-review-empty">{empty}</p>
      )}
    </section>
  );
}

export function LearningClosureReview({
  run,
  memoryRun,
  isCommitting,
  onConfirm,
  onContinue,
}: {
  run: LearningClosureRunResponse;
  memoryRun: MemoryRunResponse | null;
  isCommitting: boolean;
  onConfirm: () => Promise<void> | void;
  onContinue: () => void;
}) {
  const review = buildClosureReviewModel(run, memoryRun);
  const canConfirm =
    run.status === "preview_ready" &&
    Boolean(memoryRun?.preview.writable) &&
    review.impactLabels.length > 0;

  return (
    <section
      aria-labelledby="closure-review-title"
      className="closure-review"
      data-testid="learning-closure-review"
    >
      <header className="closure-review-header">
        <div>
          <span className="closure-review-kicker">保存前确认</span>
          <h2 id="closure-review-title">回顾这次学习</h2>
          <p>确认内容与缺口来自已提交状态；建议下一步和保存范围来自冻结的整理候选。</p>
        </div>
        <ShieldCheck aria-hidden="true" size={22} />
      </header>

      <div className="closure-review-grid">
        <ReviewSection
          empty="本次没有足够证据形成新的确认结论。"
          icon={<CheckCircle2 aria-hidden="true" size={17} />}
          items={review.confirmed}
          title="本次确认"
        />
        <ReviewSection
          empty="本次没有新增的待确认缺口。"
          icon={<Archive aria-hidden="true" size={17} />}
          items={review.unresolved}
          title="还需继续"
        />
        <ReviewSection
          empty="继续当前会话时，可以自行决定下一步。"
          icon={<Compass aria-hidden="true" size={17} />}
          items={review.next}
          title="建议下一步"
        />
      </div>

      <div className="closure-save-impact">
        <strong>确认后将保存</strong>
        {review.impactLabels.length ? (
          <ul aria-label="保存影响">
            {review.impactLabels.map((label) => (
              <li key={label}>{label}</li>
            ))}
          </ul>
        ) : (
          <p>当前没有可写入的学习成果。</p>
        )}
      </div>

      <div className="closure-review-actions">
        <button disabled={!canConfirm || isCommitting} onClick={() => void onConfirm()} type="button">
          <CheckCircle2 size={16} />
          {isCommitting ? "保存中…" : "确认并保存学习成果"}
        </button>
        <button className="secondary" disabled={isCommitting} onClick={onContinue} type="button">
          <MessageCircle size={16} />
          暂不保存，继续学习
        </button>
      </div>
    </section>
  );
}

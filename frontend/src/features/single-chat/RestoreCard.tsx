import {
  BookOpen,
  FileUp,
  FolderKanban,
  Globe2,
  Play,
  RotateCcw,
  SearchCheck,
  Sparkles,
  SquareArrowOutUpRight,
  XCircle,
} from "lucide-react";

import type { StreamRecoveryState } from "../../app/workspaceReducer";
import type { SemanticSessionRow } from "../sessions/sessionNavigation";
import {
  sessionTitle,
  summaryLabel,
  taskLabel,
} from "../sessions/sessionNavigation";
import type { TaskIntent } from "../task/taskContract";
import { hasPartialRecoveryReply } from "./chatHistory";

const PRIMARY_ENTRY = {
  intent: "learn" as const,
  title: "系统学习",
  description: "建立目标，逐步讲解并验证理解",
  prompt: "我想系统学习：",
  icon: BookOpen,
};

const SECONDARY_ENTRY_POINTS: Array<{
  intent: TaskIntent;
  title: string;
  description: string;
  prompt: string;
  icon: typeof BookOpen;
}> = [
  {
    intent: "research",
    title: "联网研究",
    description: "显式要求检索、核对并整理公开来源",
    prompt: "请联网研究：",
    icon: Globe2,
  },
  {
    intent: "project_execution",
    title: "项目推进",
    description: "显式围绕项目目标、阻塞和验证继续执行",
    prompt: "我想推进这个项目：",
    icon: FolderKanban,
  },
];

export function RestoreCard({
  session,
  streamRecovery,
  onSelectEntry,
  onUpload,
  onContinueHere,
  onStartNewTopic,
  onContinueInterrupted,
  onRetryInterrupted,
  onAbandonInterrupted,
}: {
  session: SemanticSessionRow | null;
  streamRecovery: StreamRecoveryState | null;
  onSelectEntry: (intent: TaskIntent, prompt: string) => void;
  onUpload: () => void;
  onContinueHere: (prompt: string) => void;
  onStartNewTopic: () => void;
  onContinueInterrupted: () => void;
  onRetryInterrupted: () => void;
  onAbandonInterrupted: () => Promise<void> | void;
}) {
  if (streamRecovery) {
    const hasPartialReply = hasPartialRecoveryReply(streamRecovery.reply);
    return (
      <section
        className={`restore-card interrupted-restore-card ${hasPartialReply ? "has-partial-reply" : "failed-before-reply"}`}
        aria-label="中断任务恢复"
      >
        <div className="restore-card-heading">
          <div>
            <span className="restore-card-kicker">
              {hasPartialReply ? "未完成任务" : "失败任务"}
            </span>
            <h3>
              {hasPartialReply
                ? "上次回答在生成过程中中断"
                : "上次回答未能开始生成"}
            </h3>
          </div>
          <RotateCcw size={18} />
        </div>
        <p className="restore-card-preview">
          {hasPartialReply
            ? streamRecovery.reply
            : "没有收到可继续的部分回答，可以安全地重新生成原问题。"}
        </p>
        <div className="restore-card-actions">
          {hasPartialReply ? (
            <button className="primary-action compact" onClick={onContinueInterrupted} type="button">
              <Play size={14} />
              从断点继续
            </button>
          ) : null}
          <button className={hasPartialReply ? "ghost-action compact" : "primary-action compact"} onClick={onRetryInterrupted} type="button">
            <RotateCcw size={14} />
            重新生成
          </button>
          <button
            className="ghost-action compact danger"
            onClick={() => void onAbandonInterrupted()}
            type="button"
          >
            <XCircle size={14} />
            放弃恢复
          </button>
        </div>
      </section>
    );
  }

  if (!session?.has_completed_turns) {
    const PrimaryIcon = PRIMARY_ENTRY.icon;
    return (
      <section className="restore-card new-user-restore-card" aria-label="开始新任务">
        <div className="restore-card-heading">
          <div>
            <span className="restore-card-kicker">从这里开始</span>
            <h3>直接输入问题即可开始</h3>
          </div>
          <Sparkles size={18} />
        </div>
        <p className="restore-card-preview">
          系统会根据你的问题自动判断是直接回答、学习、研究还是项目推进，无需先选择模式。
        </p>
        <div className="restore-entry-grid primary-entry-grid">
          <button
            className="restore-entry"
            onClick={() => onSelectEntry(PRIMARY_ENTRY.intent, PRIMARY_ENTRY.prompt)}
            type="button"
          >
            <PrimaryIcon size={17} />
            <span>
              <strong>{PRIMARY_ENTRY.title}</strong>
              <small>{PRIMARY_ENTRY.description}</small>
            </span>
          </button>
          <button className="restore-entry" onClick={onUpload} type="button">
            <FileUp size={17} />
            <span>
              <strong>上传资料</strong>
              <small>先加入资料，再围绕自己的内容学习</small>
            </span>
          </button>
        </div>
        <details className="restore-entry-more">
          <summary>更多开始方式</summary>
          <p>通常直接输入即可；只有需要显式固定任务类型时再选择。</p>
          <div className="restore-entry-grid secondary-entry-grid">
            {SECONDARY_ENTRY_POINTS.map((entry) => {
              const Icon = entry.icon;
              return (
                <button
                  className="restore-entry"
                  key={entry.intent}
                  onClick={() => onSelectEntry(entry.intent, entry.prompt)}
                  type="button"
                >
                  <Icon size={17} />
                  <span>
                    <strong>{entry.title}</strong>
                    <small>{entry.description}</small>
                  </span>
                </button>
              );
            })}
          </div>
        </details>
      </section>
    );
  }

  const confirmed = session.confirmed_points ?? [];
  const sources = session.disclosed_sources ?? [];
  const isResearch = session.task_intent === "research";
  const continuePrompt = restorePrompt(session);

  return (
    <section className="restore-card returning-restore-card" aria-label="继续当前任务">
      <div className="restore-card-heading">
        <div>
          <span className="restore-card-kicker">
            {taskLabel(session.task_intent)} · {summaryLabel(session)}
          </span>
          <h3>{sessionTitle(session)}</h3>
        </div>
        <SearchCheck size={18} />
      </div>

      <div className="restore-facts">
        <div>
          <span>当前任务 / 目标</span>
          <strong>{session.objective || session.research_summary || session.preview || "继续当前任务"}</strong>
        </div>
        {isResearch ? (
          <div>
            <span>已披露来源</span>
            {sources.length ? (
              <ul>
                {sources.slice(0, 3).map((source) => (
                  <li key={`${source.source_id}-${source.citation}`}>{source.citation}</li>
                ))}
              </ul>
            ) : (
              <p>当前没有记录已披露来源。</p>
            )}
          </div>
        ) : (
          <div>
            <span>已确认点</span>
            {confirmed.length ? (
              <ul>
                {confirmed.slice(0, 3).map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
            ) : (
              <p>当前还没有已确认知识点。</p>
            )}
          </div>
        )}
        <div>
          <span>当前缺口</span>
          <strong>{session.unresolved_gap || "暂无已记录缺口"}</strong>
        </div>
        <div>
          <span>下一步</span>
          <strong>{session.next_action || defaultNextStep(session)}</strong>
        </div>
      </div>

      <div className="restore-card-actions">
        <button
          className="primary-action compact"
          onClick={() => onContinueHere(continuePrompt)}
          type="button"
        >
          <Play size={14} />
          继续这里
        </button>
        <button className="ghost-action compact" onClick={onStartNewTopic} type="button">
          <SquareArrowOutUpRight size={14} />
          开始新主题
        </button>
      </div>
    </section>
  );
}

function restorePrompt(session: SemanticSessionRow): string {
  if (session.next_action) return `继续当前任务，下一步是：${session.next_action}`;
  if (session.unresolved_gap) return `继续当前任务，先解决这个缺口：${session.unresolved_gap}`;
  if (session.task_intent === "research") return "继续当前研究，基于已确认来源检查还有哪些未解决问题。";
  if (session.task_intent === "project_execution") return "继续推进当前项目，并先确认现在最重要的下一步。";
  return "继续当前学习，请从我上次停下的位置接着进行。";
}

function defaultNextStep(session: SemanticSessionRow): string {
  if (session.unresolved_gap) return `先解决：${session.unresolved_gap}`;
  if (session.task_intent === "research") return "继续核对未解决问题与来源";
  if (session.task_intent === "project_execution") return "确认当前阻塞并执行下一步验证";
  return "继续当前阶段并完成下一次理解验证";
}

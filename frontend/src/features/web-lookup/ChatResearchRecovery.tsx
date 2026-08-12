import { Loader2, RotateCcw } from "lucide-react";
import type { ChatResearchProgress } from "../../types";
import type { ResearchLookupResponse } from "./researchApi";

const stageLabels: Record<string, string> = {
  planned: "等待开始",
  searching: "正在搜索",
  assessing: "正在筛选来源",
  reading: "正在读取来源",
  synthesizing: "正在整理证据",
  completed: "研究完成",
  failed: "研究失败",
  cancelled: "研究已停止",
};

function runDetail(run: ResearchLookupResponse): string {
  if (run.status === "partial") {
    return "部分结果不会自动用于下一轮聊天；你可以重试以补全研究";
  }
  if (run.status === "failed") {
    return `${run.error || "本次研究未完成"}；重试会从已保存的进度继续`;
  }
  if (run.status === "cancelled") {
    return "已停止本次研究；需要时可从已保存的进度重试";
  }
  return run.stop_reason || stageLabels[run.stage] || run.stage;
}

export function ChatResearchRecovery({
  run,
  progress = null,
  isBusy,
  canRetry,
  canResume,
  useInChat,
  onRetry,
  onResume,
}: {
  run: ResearchLookupResponse | null;
  progress?: ChatResearchProgress | null;
  isBusy: boolean;
  canRetry: boolean;
  canResume: boolean;
  useInChat: boolean;
  onRetry: () => void;
  onResume: () => void;
}) {
  if (progress && ["pending", "running"].includes(progress.status)) {
    return (
      <div className="memory-note" role="status">
        <Loader2 className="spin" size={16} />
        <div>
          <strong>{stageLabels[progress.stage] ?? "联网研究进行中"}</strong>
          <span>
            已记录 {progress.query_attempt_count} 次查询和 {progress.selected_source_count} 个来源。
          </span>
        </div>
      </div>
    );
  }
  const progressIsNewer = Boolean(
    progress &&
      !["pending", "running"].includes(progress.status) &&
      (!run || run.run_id !== progress.run_id || run.version < progress.version),
  );
  if (progress && progressIsNewer) {
    const failed = progress.status === "failed";
    return (
      <div className={`memory-note ${failed ? "warn" : ""}`} role="status">
        <div>
          <strong>{stageLabels[progress.stage] ?? "联网研究已结束"}</strong>
          <span>
            {failed
              ? `${progress.error || "联网搜索失败"}；本回答未使用联网来源。`
              : progress.stop_reason || "联网研究已结束"}
          </span>
        </div>
      </div>
    );
  }
  if (run?.research_context.run_kind !== "chat_tool_loop") return null;
  const recovered = run.status === "completed" && run.provider_status === "found";
  if (!canRetry && !canResume && !isBusy && !(recovered && useInChat)) return null;
  const detail = runDetail(run);
  const heading = run.status === "partial" ? "研究得到部分可用结果" : stageLabels[run.stage] ?? "联网研究可恢复";

  return (
    <div className={`memory-note ${recovered ? "" : "warn"}`} role="status">
      <div>
        <strong>{recovered ? "联网研究已恢复" : heading}</strong>
        <span>
          {recovered && useInChat
            ? "恢复结果已设为下一轮聊天资料。"
            : `${detail}；已保留 ${run.query_attempts.length} 次查询和 ${run.selected_sources.length} 个来源。`}
        </span>
      </div>
      {canResume ? (
        <button className="ghost-action compact" disabled={isBusy} onClick={onResume} type="button">
          {isBusy ? <Loader2 className="spin" size={14} /> : <RotateCcw size={14} />}
          继续研究
        </button>
      ) : null}
      {canRetry ? (
        <button className="ghost-action compact" disabled={isBusy} onClick={onRetry} type="button">
          {isBusy ? <Loader2 className="spin" size={14} /> : <RotateCcw size={14} />}
          重试研究
        </button>
      ) : null}
    </div>
  );
}

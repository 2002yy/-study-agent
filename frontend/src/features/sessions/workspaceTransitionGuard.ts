import { useCallback, useMemo, useRef, useState } from "react";

export type WorkspaceTransitionKind = "new" | "switch" | "archive";

export type WorkspaceTransitionState = {
  isSending: boolean;
  hasUserMessages: boolean;
  summaryStatus?: string;
  memoryBusy: boolean;
  memoryPreviewReady: boolean;
  researchStatus?: string;
  researchBusy: boolean;
  ragWriteBusy: boolean;
};

export type WorkspaceTransitionIssue = {
  id:
    | "archive"
    | "chat"
    | "memory_busy"
    | "memory_preview"
    | "research"
    | "rag_write"
    | "summary";
  label: string;
  effect: string;
};

export type WorkspaceTransitionNotice = {
  kind: WorkspaceTransitionKind;
  title: string;
  description: string;
  confirmLabel: string;
  issues: WorkspaceTransitionIssue[];
};

const TITLES: Record<WorkspaceTransitionKind, string> = {
  new: "开始新会话前处理未完成工作",
  switch: "切换会话前确认未完成工作",
  archive: "归档当前会话前确认未完成工作",
};

const CONFIRM_LABELS: Record<WorkspaceTransitionKind, string> = {
  new: "仍然开始新会话",
  switch: "仍然切换会话",
  archive: "仍然归档并新建",
};

export function buildWorkspaceTransitionNotice(
  kind: WorkspaceTransitionKind,
  state: WorkspaceTransitionState,
): WorkspaceTransitionNotice | null {
  const issues: WorkspaceTransitionIssue[] = [];
  if (state.isSending) {
    issues.push({
      id: "chat",
      label: "当前回答仍在生成",
      effect: "离开会停止本轮回答；已经生成的片段会保留为中断记录。",
    });
  }
  if (state.memoryBusy) {
    issues.push({
      id: "memory_busy",
      label: "学习整理正在生成或提交",
      effect: "当前请求不会被伪装为已取消；服务端仍记录真实终态，本页不再跟随进度。",
    });
  } else if (state.memoryPreviewReady) {
    issues.push({
      id: "memory_preview",
      label: "学习成果候选尚未确认",
      effect: "未确认内容不会写入长期记忆；离开后当前预览入口会被清除。",
    });
  }
  if (
    state.researchBusy ||
    ["pending", "running", "partial"].includes(state.researchStatus ?? "")
  ) {
    issues.push({
      id: "research",
      label: state.researchStatus === "partial" ? "联网研究只有部分结果" : "联网研究尚未结束",
      effect: "研究记录会保留，但不会自动带入目标会话，也不会自动成为聊天证据。",
    });
  }
  if (state.ragWriteBusy) {
    issues.push({
      id: "rag_write",
      label: "资料仍在上传或建立索引",
      effect: "当前写入没有服务端取消能力，会继续到真实终态，不能视为已经停止。",
    });
  }
  if (kind === "new" && state.hasUserMessages) {
    issues.push({
      id: "summary",
      label:
        state.summaryStatus === "summarized"
          ? "当前会话已整理但尚未归档"
          : "当前学习尚未整理",
      effect: "新建不会自动归档旧会话；旧会话仍保留在历史中。",
    });
  }
  if (kind === "archive") {
    issues.push({
      id: "archive",
      label: "当前会话将进入历史记录",
      effect: "归档会结束当前会话并新建空白会话；归档记录仍可从会话历史恢复。",
    });
  }
  if (!issues.length) return null;
  return {
    kind,
    title: TITLES[kind],
    description: "下面逐项说明离开后的真实处理方式。你可以留在当前会话继续处理，或明确接受这些结果后离开。",
    confirmLabel: CONFIRM_LABELS[kind],
    issues,
  };
}

type PendingTransition = {
  notice: WorkspaceTransitionNotice;
  execute: () => void | Promise<void>;
};

export function useWorkspaceTransitionGuard(state: WorkspaceTransitionState) {
  const [notice, setNotice] = useState<WorkspaceTransitionNotice | null>(null);
  const pendingRef = useRef<PendingTransition | null>(null);

  const request = useCallback(
    (kind: WorkspaceTransitionKind, execute: () => void | Promise<void>) => {
      const nextNotice = buildWorkspaceTransitionNotice(kind, state);
      if (!nextNotice) {
        void execute();
        return;
      }
      pendingRef.current = { notice: nextNotice, execute };
      setNotice(nextNotice);
    },
    [state],
  );

  const cancel = useCallback(() => {
    pendingRef.current = null;
    setNotice(null);
  }, []);

  const confirm = useCallback(() => {
    const pending = pendingRef.current;
    pendingRef.current = null;
    setNotice(null);
    if (pending) void pending.execute();
  }, []);

  return useMemo(
    () => ({ notice, request, cancel, confirm }),
    [notice, request, cancel, confirm],
  );
}

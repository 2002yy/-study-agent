import type { ChatMessage } from "../../types";

/**
 * G12 decision 12: fixed, text-first copy for every cancellation lifecycle
 * state. Rendered inside the turn bubble (not toast-only), announced via
 * role="status"/"alert", and legible without color on narrow viewports.
 */
const TURN_STATUS_COPY: Record<string, { text: string; tone: "pending" | "done" | "error" }> = {
  cancelling: {
    text: "正在提交停止请求…",
    tone: "pending",
  },
  "cancelling-registered": {
    text: "停止请求已登记，等待服务端确认…",
    tone: "pending",
  },
  "cancelling-slow": {
    text: "服务端仍在收尾，取消已登记；完成后此轮会自动结束。",
    tone: "pending",
  },
  cancelled: {
    text: "已停止：本轮未产生可见输出。",
    tone: "done",
  },
  interrupted: {
    text: "已停止生成，已有内容已保留。",
    tone: "done",
  },
  completed: {
    text: "本轮已在停止前正常完成。",
    tone: "done",
  },
};

export function turnStatusCopy(status?: string): string | null {
  if (!status) return null;
  return TURN_STATUS_COPY[status]?.text ?? null;
}

export function turnStatusTone(
  status?: string
): "pending" | "done" | "error" | null {
  if (!status) return null;
  return TURN_STATUS_COPY[status]?.tone ?? null;
}

export function hasTurnStatusNotice(message: ChatMessage): boolean {
  return (
    Boolean(message.turnStatus) && turnStatusCopy(message.turnStatus) !== null
  );
}

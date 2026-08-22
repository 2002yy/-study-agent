/**
 * G12 decision 12: fixed, text-first copy for the cancellation lifecycle.
 * The copy is written into ChatMessage.cancelNotice by the cooperative cancel
 * flow only — never for plain aborts/disconnects (decision 12: a browser
 * abort must not display "stopped") and never restored from history.
 */
const TURN_STATUS_COPY: Record<string, string> = {
  cancelling: "正在提交停止请求…",
  "cancelling-registered": "停止请求已登记，等待服务端确认…",
  "cancelling-slow": "服务端仍在收尾，取消已登记；完成后此轮会自动结束。",
  cancelled: "已停止：本轮未产生可见输出。",
  interrupted: "已停止生成，已有内容已保留。",
  completed: "本轮已在停止前正常完成。",
};

export function turnStatusCopy(status?: string): string | null {
  if (!status) return null;
  return TURN_STATUS_COPY[status] ?? null;
}

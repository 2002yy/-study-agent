import { ShieldCheck } from "lucide-react";
import { useState } from "react";

export const EXTERNAL_DATA_NOTICE_KEY = "study-agent:external-data-notice:v1";

export function ExternalDataFirstUseNotice({
  webPolicy,
  cloudContextPolicy,
  onOpenSettings,
}: {
  webPolicy: string;
  cloudContextPolicy: string;
  onOpenSettings: () => void;
}) {
  const [open, setOpen] = useState(
    () => window.localStorage.getItem(EXTERNAL_DATA_NOTICE_KEY) !== "acknowledged",
  );

  const acknowledge = () => {
    window.localStorage.setItem(EXTERNAL_DATA_NOTICE_KEY, "acknowledged");
    setOpen(false);
  };

  if (!open) return null;

  return (
      <aside
        aria-labelledby="external-data-first-use-title"
        className="external-data-first-use"
      >
        <ShieldCheck aria-hidden="true" size={22} />
        <div className="external-data-first-use-copy">
          <strong id="external-data-first-use-title">联网与模型上下文说明</strong>
          <p>
            当前联网策略：{webPolicy === "auto" ? "任务需要时自动联网" : webPolicy === "ask" ? "每次联网前询问" : "关闭联网"}；
            模型上下文：
            {cloudContextPolicy === "question_only"
              ? "仅当前问题"
              : cloudContextPolicy === "recent_chat"
                ? "当前问题与最近对话"
                : "当前问题、最近对话及相关本地资料片段"}。每轮“证据轨迹”会显示实际数据类型、搜索词与搜索源，不展示本地正文。
          </p>
        </div>
        <div className="external-data-first-use-actions">
          <button
            className="ghost-action"
            onClick={() => {
              acknowledge();
              onOpenSettings();
            }}
            type="button"
          >
            查看隐私设置
          </button>
          <button className="primary-action" onClick={acknowledge} type="button">
            我知道了
          </button>
        </div>
      </aside>
  );
}

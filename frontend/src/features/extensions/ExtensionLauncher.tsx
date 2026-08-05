import { Activity, MessageSquare, Wrench } from "lucide-react";

import type { ExtensionDrawerId } from "./extensionDrawerContract";

export function ExtensionLauncher({
  onOpen,
}: {
  onOpen: (drawer: ExtensionDrawerId, target: HTMLButtonElement) => void;
}) {
  return (
    <>
      <div className="workspace-menu-section-label" role="presentation">
        实验功能
      </div>
      <button
        onClick={(event) => onOpen("group", event.currentTarget)}
        role="menuitem"
        type="button"
      >
        <MessageSquare size={16} />
        <span>
          <strong>群聊讨论</strong>
          <small>让多位角色从不同角度讨论</small>
        </span>
      </button>
      <button
        onClick={(event) => onOpen("tools", event.currentTarget)}
        role="menuitem"
        type="button"
      >
        <Wrench size={16} />
        <span>
          <strong>受控工具</strong>
          <small>实验性的本地知识工具入口</small>
        </span>
      </button>
      <button
        onClick={(event) => onOpen("timeline", event.currentTarget)}
        role="menuitem"
        type="button"
      >
        <Activity size={16} />
        <span>
          <strong>开发者诊断</strong>
          <small>查看工作流阶段和失败原因</small>
        </span>
      </button>
    </>
  );
}

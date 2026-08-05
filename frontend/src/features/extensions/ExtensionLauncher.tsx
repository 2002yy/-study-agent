import { FlaskConical } from "lucide-react";

import type { DrawerId } from "../../types";
import { LAB_DRAWER } from "./extensionDrawerContract";

export function ExtensionLauncher({
  onOpen,
}: {
  onOpen: (drawer: DrawerId, target: HTMLButtonElement) => void;
}) {
  return (
    <>
      <div className="workspace-menu-section-label" role="presentation">
        实验功能
      </div>
      <button
        onClick={(event) => onOpen(LAB_DRAWER, event.currentTarget)}
        role="menuitem"
        type="button"
      >
        <FlaskConical size={16} />
        <span>
          <strong>实验室</strong>
          <small>群聊、受控工具与开发者诊断</small>
        </span>
      </button>
    </>
  );
}

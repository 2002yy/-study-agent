import { Activity, MessageSquare, Wrench } from "lucide-react";

import type { ExtensionCapabilityId } from "./extensionDrawerContract";

const CAPABILITIES: Array<{
  id: ExtensionCapabilityId;
  label: string;
  description: string;
  icon: typeof MessageSquare;
}> = [
  {
    id: "group",
    label: "群聊讨论",
    description: "让多位角色从不同角度讨论",
    icon: MessageSquare,
  },
  {
    id: "tools",
    label: "受控工具",
    description: "实验性的本地知识工具入口",
    icon: Wrench,
  },
  {
    id: "timeline",
    label: "开发者诊断",
    description: "查看工作流阶段和失败原因",
    icon: Activity,
  },
];

export function ExtensionLabPanel({
  onSelect,
}: {
  onSelect: (capability: ExtensionCapabilityId) => void;
}) {
  return (
    <section aria-labelledby="extension-lab-title" className="extension-lab-panel">
      <div className="panel-intro">
        <h3 id="extension-lab-title">选择一项实验能力</h3>
        <p>这些功能默认休眠，只有打开具体项目后才会加载数据。</p>
      </div>
      <div className="extension-lab-options">
        {CAPABILITIES.map(({ id, label, description, icon: Icon }) => (
          <button
            data-extension-capability={id}
            key={id}
            onClick={() => onSelect(id)}
            type="button"
          >
            <Icon size={18} />
            <span>
              <strong>{label}</strong>
              <small>{description}</small>
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

import { ArrowLeft } from "lucide-react";
import { useRef } from "react";

import { SlideOver } from "../components/SlideOver";
import { ExtensionLabPanel } from "../features/extensions/ExtensionLabPanel";
import type { ExtensionDrawerId } from "../features/extensions/extensionDrawerContract";
import { ToolPanel } from "../features/tools/ToolPanel";
import { WechatPanel } from "../features/wechat-workspace/WechatPanel";
import { TimelinePanel } from "../features/workflows/TimelinePanel";
import type { ExtensionViewModel } from "./useExtensionRuntime";

const CAPABILITY_TITLES: Record<ExtensionDrawerId, string> = {
  group: "群聊",
  tools: "工具",
  timeline: "开发者诊断",
};

export function ExtensionDrawers({
  view,
  onClose,
}: {
  view: ExtensionViewModel;
  onClose: () => void;
}) {
  const lastCapability = useRef<ExtensionDrawerId | null>(null);
  const groupController = view.group.controller;
  const toolController = view.tools.controller;
  const workflowController = view.timeline.controller;
  const capability = view.activeCapability;
  const open = view.activeSurface !== null;
  const title = capability ? CAPABILITY_TITLES[capability] : "实验室";

  const selectCapability = (next: ExtensionDrawerId) => {
    lastCapability.current = next;
    view.selectCapability(next);
  };

  const backToLab = () => {
    const previous = lastCapability.current;
    view.backToLab();
    window.requestAnimationFrame(() => {
      if (!previous) return;
      document
        .querySelector<HTMLButtonElement>(
          `[data-extension-capability="${previous}"]`,
        )
        ?.focus();
    });
  };

  return (
    <SlideOver open={open} title={title} onClose={onClose}>
      {view.activeSurface === "lab" && !capability ? (
        <ExtensionLabPanel onSelect={selectCapability} />
      ) : null}

      {view.activeSurface === "lab" && capability && !view.isLegacySurface ? (
        <button
          aria-label="返回实验室"
          className="ghost-action compact extension-lab-back"
          onClick={backToLab}
          type="button"
        >
          <ArrowLeft size={14} />
          返回实验室
        </button>
      ) : null}

      {capability === "group" ? (
        <WechatPanel
          wechat={view.group.wechat}
          webLookup={view.group.webLookup}
          useWebLookup={view.group.useWebLookup}
          setUseWebLookup={view.group.setUseWebLookup}
          wechatInput={groupController.input}
          setWechatInput={groupController.setInput}
          sessionId={view.group.sessionId}
          onOpening={groupController.opening}
          onReset={groupController.reset}
          onMarkRead={groupController.markRead}
          onSendWechat={groupController.send}
          onStopWechat={groupController.stop}
          isWechatBusy={groupController.isBusy}
          error={groupController.error}
        />
      ) : null}

      {capability === "tools" ? (
        <ToolPanel
          toolCount={view.tools.toolCount}
          run={toolController.run}
          error={toolController.error}
          previewTool={toolController.preview}
          callTool={toolController.call}
          isPreviewing={toolController.isPreviewing}
          isCalling={toolController.isCalling}
          canCall={toolController.canCall}
          callBlockedReason={toolController.callBlockedReason}
          invocationLabel={toolController.invocationLabel}
        />
      ) : null}

      {capability === "timeline" ? (
        <TimelinePanel
          runs={view.timeline.runs}
          selectedRun={workflowController.selectedRun}
          loadingRunId={workflowController.loadingRunId}
          onSelectRun={workflowController.selectRun}
        />
      ) : null}
    </SlideOver>
  );
}

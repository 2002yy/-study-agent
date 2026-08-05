import { SlideOver } from "../components/SlideOver";
import { ToolPanel } from "../features/tools/ToolPanel";
import { WechatPanel } from "../features/wechat-workspace/WechatPanel";
import { TimelinePanel } from "../features/workflows/TimelinePanel";
import type { ExtensionViewModel } from "./useExtensionRuntime";

export function ExtensionDrawers({
  view,
  onClose,
}: {
  view: ExtensionViewModel;
  onClose: () => void;
}) {
  const groupController = view.group.controller;
  const toolController = view.tools.controller;
  const workflowController = view.timeline.controller;

  return (
    <>
      <SlideOver
        open={view.activeDrawer === "group"}
        title="群聊"
        onClose={onClose}
      >
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
      </SlideOver>

      <SlideOver
        open={view.activeDrawer === "tools"}
        title="工具"
        onClose={onClose}
      >
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
      </SlideOver>

      <SlideOver
        open={view.activeDrawer === "timeline"}
        title="开发者诊断"
        onClose={onClose}
      >
        <TimelinePanel
          runs={view.timeline.runs}
          selectedRun={workflowController.selectedRun}
          loadingRunId={workflowController.loadingRunId}
          onSelectRun={workflowController.selectRun}
        />
      </SlideOver>
    </>
  );
}

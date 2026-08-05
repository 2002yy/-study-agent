import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const sourceOf = (relativePath: string) => {
  const path = fileURLToPath(new URL(relativePath, import.meta.url));
  return existsSync(path) ? readFileSync(path, "utf8") : "";
};

const runtimeSource = sourceOf("./WorkspaceRuntime.tsx");
const compositionSource = sourceOf("./useWorkspaceControllers.ts");
const recoverySource = sourceOf("./useWorkspaceRecovery.ts");
const extensionSource = sourceOf("./useExtensionRuntime.ts");
const extensionDrawerContractSource = sourceOf(
  "../features/extensions/extensionDrawerContract.ts",
);
const learningSource = sourceOf("./useLearningSessionRuntime.ts");
const evidenceSource = sourceOf("./useEvidenceRuntime.ts");

describe("ExtensionRuntime owner boundary", () => {
  it("is the only production owner of group, tool, and workflow controllers", () => {
    expect(runtimeSource).toContain("useExtensionRuntime({");
    for (const hook of [
      "useGroupChatController",
      "useToolController",
      "useWorkflowController",
    ]) {
      expect(extensionSource).toContain(`${hook}(`);
      expect(compositionSource).not.toContain(`${hook}(`);
      expect(runtimeSource).not.toContain(`${hook}(`);
      expect(learningSource).not.toContain(`${hook}(`);
      expect(evidenceSource).not.toContain(`${hook}(`);
    }
  });

  it("owns extension recovery ids without changing WorkspacePersistence fields", () => {
    expect(extensionSource).toContain("export type ExtensionRecoveryPort");
    expect(extensionSource).toContain("wechatThreadId:");
    expect(extensionSource).toContain("toolRunId:");
    expect(extensionSource).toContain('type: "SET_ACTIVE_GROUP_THREAD"');
    expect(extensionSource).toContain('type: "SET_ACTIVE_TOOL_RUN"');
    expect(recoverySource).toContain("extension: ExtensionRecoveryPort");
    expect(recoverySource).toContain("extension.restore(parsed)");
    expect(recoverySource).toContain("...extension.state");
    expect(recoverySource).not.toContain("ids: {");
    expect(recoverySource).not.toContain("setIds: {");
  });

  it("loads only the selected laboratory capability while memory remains outside", () => {
    expect(extensionDrawerContractSource).toContain(
      'export const EXTENSION_DRAWERS = ["group", "tools", "timeline"] as const;',
    );
    expect(extensionDrawerContractSource).toContain(
      'export type ExtensionSurfaceId = "lab" | ExtensionDrawerId;',
    );
    expect(extensionSource).toContain("EXTENSION_DRAWER_CONFIG");
    expect(extensionSource).toContain('group: { feature: "wechat"');
    expect(extensionSource).toContain('tools: { feature: "tools"');
    expect(extensionSource).toContain('timeline: { feature: "workflows"');
    expect(extensionSource).toContain("selectExtensionSurface(state.activeDrawer)");
    expect(extensionSource).toContain("if (!activeCapability) return;");
    expect(extensionSource).toContain("EXTENSION_DRAWER_CONFIG[activeCapability]");
    expect(extensionSource).not.toContain('feature: "memory"');
    expect(compositionSource).not.toContain('options.loadFeature("wechat"');
    expect(compositionSource).not.toContain('options.loadFeature("tools")');
    expect(compositionSource).not.toContain('options.loadFeature("workflows")');
    expect(compositionSource).toContain('options.loadFeature("memory")');
  });

  it("exposes narrow coordinator ports without owning cross-domain coordination", () => {
    expect(extensionSource).toContain("export type ExtensionCoordinatorPort");
    expect(extensionSource).toContain("cancelGroup:");
    expect(extensionSource).toContain("invalidateTool:");
    expect(extensionSource).toContain("clearToolRun:");
    expect(extensionSource).toContain("clearWorkflow:");
    expect(compositionSource).toContain("options.extension.coordinator");
    expect(compositionSource).toContain("new WorkspaceCoordinator(");
    expect(extensionSource).not.toContain("new WorkspaceCoordinator(");
  });

  it("exposes a panel-ready view without relaying it through composition", () => {
    expect(extensionSource).toContain("export type ExtensionViewModel");
    expect(extensionSource).toContain("const view: ExtensionViewModel");
    expect(extensionSource).toContain("activeSurface,");
    expect(extensionSource).toContain("activeCapability,");
    expect(runtimeSource).toContain("extensionView={extension.view}");
    for (const field of [
      "groupController",
      "toolController",
      "workflowController",
      "groupThreadId",
    ]) {
      expect(compositionSource).not.toContain(field);
    }
  });

  it("does not absorb Learning or Evidence owners", () => {
    for (const forbidden of [
      "useChatController(",
      "useMemoryController(",
      "useRagController(",
      "useUploadController(",
      "useWebLookupController(",
      "useSettingsController(",
      "useRoleController(",
    ]) {
      expect(extensionSource).not.toContain(forbidden);
    }
  });
});

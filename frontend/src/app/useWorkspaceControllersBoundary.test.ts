import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const runtimeSource = readFileSync(
  fileURLToPath(new URL("./WorkspaceRuntime.tsx", import.meta.url)),
  "utf8"
);
const compositionSource = readFileSync(
  fileURLToPath(new URL("./useWorkspaceControllers.ts", import.meta.url)),
  "utf8"
);
const evidenceSource = readFileSync(
  fileURLToPath(new URL("./useEvidenceRuntime.ts", import.meta.url)),
  "utf8"
);

const workspaceControllerHooks = [
  "useRoleController",
  "useWorkflowController",
  "useSettingsController",
  "useGroupChatController",
  "useMemoryController",
  "useChatController",
  "useToolController",
];
const evidenceControllerHooks = [
  "useWebLookupController",
  "useRagController",
  "useUploadController",
];

describe("workspace controller composition boundary", () => {
  it("keeps cross-domain controller construction outside WorkspaceRuntime", () => {
    for (const hook of workspaceControllerHooks) {
      expect(compositionSource).toContain(`${hook}(`);
      expect(runtimeSource).not.toContain(`${hook}(`);
      expect(runtimeSource).not.toMatch(new RegExp(`import .*${hook}`));
    }
  });

  it("makes EvidenceRuntime the only owner of research, RAG, and upload controllers", () => {
    expect(runtimeSource).toContain("useEvidenceRuntime({");
    for (const hook of evidenceControllerHooks) {
      expect(evidenceSource).toContain(`${hook}(`);
      expect(compositionSource).not.toContain(`${hook}(`);
      expect(runtimeSource).not.toContain(`${hook}(`);
    }
    for (const stateToken of [
      "useState<RagSettings>",
      "activeRagQueryRunId",
      "activeRagWriteRunId",
      "activeWebLookupRunId",
    ]) {
      expect(evidenceSource).toContain(stateToken);
      expect(runtimeSource).not.toContain(stateToken);
    }
  });

  it("loads the Sources drawer through EvidenceRuntime", () => {
    expect(evidenceSource).toContain('state.activeDrawer !== "sources"');
    expect(evidenceSource).toContain('options.loadFeature("rag")');
    expect(evidenceSource).toContain("uploadController.refreshDocuments()");
    expect(compositionSource).not.toContain('drawer === "sources"');
    expect(compositionSource).not.toContain("refreshDocuments()");
  });

  it("does not rebuild the retired NewsController in the main workspace", () => {
    expect(compositionSource).not.toContain("useNewsController");
    expect(compositionSource).not.toContain("newsController");
    expect(evidenceSource).not.toContain("useNewsController");
    expect(runtimeSource).not.toContain("useNewsController");
  });

  it("owns cross-feature artifact cleanup while chat cancellation stays scoped", () => {
    expect(compositionSource).toContain("new WorkspaceCoordinator(");
    expect(compositionSource).toContain("clearChatArtifacts:");
    expect(compositionSource).toContain('cancelChat: () => operationRegistry.invalidate("chat")');
    expect(compositionSource).not.toContain("onWorkspaceCancelled:");
    expect(compositionSource).not.toContain("operationRegistry.cancelAll()");
    expect(runtimeSource).not.toContain("new WorkspaceCoordinator(");
    expect(evidenceSource).not.toContain("new WorkspaceCoordinator(");
  });
});

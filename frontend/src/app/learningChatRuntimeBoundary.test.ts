import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const learningSource = readFileSync(
  fileURLToPath(new URL("./useLearningSessionRuntime.ts", import.meta.url)),
  "utf8",
);
const compositionSource = readFileSync(
  fileURLToPath(new URL("./useWorkspaceControllers.ts", import.meta.url)),
  "utf8",
);
const recoverySource = readFileSync(
  fileURLToPath(new URL("./useWorkspaceRecovery.ts", import.meta.url)),
  "utf8",
);
const runtimeSource = readFileSync(
  fileURLToPath(new URL("./WorkspaceRuntime.tsx", import.meta.url)),
  "utf8",
);

describe("learning chat runtime boundary", () => {
  it("makes LearningSessionRuntime the only chat controller owner", () => {
    expect(learningSource).toContain("useChatController({");
    expect(compositionSource).not.toContain("useChatController(");
    expect(runtimeSource).not.toContain("useChatController(");
  });

  it("bridges cross-domain artifact cleanup through a narrow bound port", () => {
    expect(learningSource).toContain("export type LearningArtifactPort");
    expect(learningSource).toContain("bindArtifactPort");
    expect(compositionSource).toContain("options.learning.bindArtifactPort({");
    expect(compositionSource).toContain("clearChatArtifacts:");
    expect(learningSource).not.toContain("new WorkspaceCoordinator(");
  });

  it("keeps chat persistence and restoration behind learning.recovery", () => {
    expect(recoverySource).not.toContain("chatController:");
    expect(recoverySource).not.toContain("hydrateSession(");
    expect(recoverySource).not.toContain("setMessages(");
    expect(recoverySource).not.toContain("setLastChat(");
    expect(learningSource).toContain("singleChatSessionId:");
    expect(learningSource).toContain("cachedMessages:");
    expect(learningSource).toContain("chatController.hydrateSession(");
    expect(learningSource).toContain("chatController.setLastChat(");
  });

  it("invalidates the durable ResumeContext read after explicit closure commit", () => {
    expect(learningSource).toContain("const refreshLearningState = useCallback");
    expect(learningSource).toContain("onMemoryChanged: refreshLearningState");
    expect(learningSource).toContain("setLearningResumeRefreshRevision");
    expect(learningSource).toContain("learningResumeRefreshRevision,");
  });
});

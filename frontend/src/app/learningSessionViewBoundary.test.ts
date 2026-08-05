import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const read = (path: string) =>
  readFileSync(fileURLToPath(new URL(path, import.meta.url)), "utf8");

const viewSource = read("./WorkspaceView.tsx");
const learningSource = read("./useLearningSessionRuntime.ts");

describe("learning session view owner boundary", () => {
  it("keeps learning-session selectors and actions in LearningSessionRuntime", () => {
    for (const token of [
      "selectActiveLearningSession(",
      "selectLearningSessionSummary(",
      "requestNewSession",
      "abandonRecovery",
      "visitedPhases: state.pedagogyPhases",
    ]) {
      expect(learningSource).toContain(token);
    }
  });

  it("keeps WorkspaceView declarative for session-derived state", () => {
    for (const retiredInlineOwner of [
      "snapshot.sessions.find(",
      "state.sessionSummary?.thread_id",
      "const requestNewSession =",
      "const abandonRecovery =",
      "abandonInterruptedTurn",
    ]) {
      expect(viewSource).not.toContain(retiredInlineOwner);
    }

    expect(viewSource).toContain("learningView.activeSession");
    expect(viewSource).toContain("learningView.sessionSummary");
    expect(viewSource).toContain("learningView.requestNewSession");
    expect(viewSource).toContain("learningView.abandonRecovery");
    expect(viewSource).toContain("learningView.visitedPhases");
  });
});

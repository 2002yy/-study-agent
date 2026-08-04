import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const read = (path: string) => readFileSync(new URL(path, import.meta.url), "utf8");

describe("frontend state consolidation boundary", () => {
  it("does not rebuild the retired NewsRun owner in the main workspace", () => {
    const runtime = read("./WorkspaceRuntime.tsx");
    const controllers = read("./useWorkspaceControllers.ts");
    const recovery = read("./useWorkspaceRecovery.ts");

    expect(runtime).not.toContain("activeNewsRunId");
    expect(runtime).not.toContain("SET_ACTIVE_NEWS_RUN");
    expect(controllers).not.toContain("useNewsController");
    expect(controllers).not.toContain("newsController");
    expect(recovery).not.toContain("newsRunId");
  });

  it("keeps only production session transitions in the reducer", () => {
    const reducer = read("./workspaceReducer.ts");

    expect(reducer).not.toContain("selectedPanel");
    expect(reducer).not.toContain("SELECT_PANEL");
    expect(reducer).not.toContain("START_NEW_CHAT_SESSION");
    expect(reducer).not.toContain("activeNewsRunId");
  });
});

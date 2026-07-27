import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const sidebarSource = readFileSync(
  fileURLToPath(new URL("./SessionSidebar.tsx", import.meta.url)),
  "utf8",
);
const panelSource = readFileSync(
  fileURLToPath(new URL("./SessionsPanel.tsx", import.meta.url)),
  "utf8",
);

describe("SessionNavigator owner boundary", () => {
  it("keeps legacy surfaces as adapters without local navigation state", () => {
    for (const source of [sidebarSource, panelSource]) {
      expect(source).toContain("SessionNavigator");
      expect(source).not.toContain("useState");
      expect(source).not.toContain("updateSessionTitle");
      expect(source).not.toContain("window.confirm");
    }
  });
});

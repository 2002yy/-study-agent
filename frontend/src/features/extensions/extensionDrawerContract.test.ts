import { describe, expect, it } from "vitest";

import {
  EXTENSION_DRAWERS,
  selectExtensionDrawer,
} from "./extensionDrawerContract";

describe("extension drawer contract", () => {
  it("recognizes only extension drawers", () => {
    expect(EXTENSION_DRAWERS).toEqual(["group", "tools", "timeline"]);
    expect(selectExtensionDrawer("group")).toBe("group");
    expect(selectExtensionDrawer("tools")).toBe("tools");
    expect(selectExtensionDrawer("timeline")).toBe("timeline");
  });

  it("keeps ordinary and missing drawers outside Extension loading", () => {
    expect(selectExtensionDrawer(null)).toBeNull();
    expect(selectExtensionDrawer(undefined)).toBeNull();
    expect(selectExtensionDrawer("sessions")).toBeNull();
    expect(selectExtensionDrawer("memory")).toBeNull();
    expect(selectExtensionDrawer("settings")).toBeNull();
    expect(selectExtensionDrawer("sources")).toBeNull();
  });
});

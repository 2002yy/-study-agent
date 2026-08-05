import type { DrawerId } from "../../types";

export const EXTENSION_DRAWERS = ["group", "tools", "timeline"] as const;

export type ExtensionDrawerId = (typeof EXTENSION_DRAWERS)[number];
export type ExtensionSurfaceId = "lab" | ExtensionDrawerId;

// DrawerId remains unchanged during the short compatibility window. New UI
// emits only this centralized laboratory adapter; legacy capability drawer
// ids remain readable for restored links and tests.
export const LAB_DRAWER = "lab" as DrawerId;

export function selectExtensionDrawer(
  drawer: DrawerId | null | undefined,
): ExtensionDrawerId | null {
  return EXTENSION_DRAWERS.includes(drawer as ExtensionDrawerId)
    ? (drawer as ExtensionDrawerId)
    : null;
}

export function selectExtensionSurface(
  drawer: DrawerId | null | undefined,
): ExtensionSurfaceId | null {
  if ((drawer as ExtensionSurfaceId | null | undefined) === "lab") return "lab";
  return selectExtensionDrawer(drawer);
}

export function resolveExtensionCapability(
  surface: ExtensionSurfaceId | null,
  selected: ExtensionDrawerId | null,
): ExtensionDrawerId | null {
  if (!surface) return null;
  return surface === "lab" ? selected : surface;
}

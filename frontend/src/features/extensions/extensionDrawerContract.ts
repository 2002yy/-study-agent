import type { DrawerId } from "../../types";

export const EXTENSION_CAPABILITIES = ["group", "tools", "timeline"] as const;

export type ExtensionCapabilityId = (typeof EXTENSION_CAPABILITIES)[number];
export type ExtensionSurfaceId = "lab";

export const LAB_DRAWER: DrawerId = "lab";

export function selectExtensionSurface(
  drawer: DrawerId | null | undefined,
): ExtensionSurfaceId | null {
  return drawer === LAB_DRAWER ? "lab" : null;
}

export function resolveExtensionCapability(
  surface: ExtensionSurfaceId | null,
  selected: ExtensionCapabilityId | null,
): ExtensionCapabilityId | null {
  return surface === "lab" ? selected : null;
}

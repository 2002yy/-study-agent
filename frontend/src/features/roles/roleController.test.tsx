// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { loadRole } from "../../api";
import { serverQueryCache } from "../../app/serverQueryCache";
import type { RoleResponse } from "../../types";
import { useRoleController } from "./roleController";

afterEach(cleanup);
beforeEach(() => {
  serverQueryCache.invalidate();
});

vi.mock("../../api", () => ({
  loadRole: vi.fn(),
}));

const mockLoadRole = vi.mocked(loadRole);

const detail: RoleResponse = {
  id: "keqing",
  label: "刻晴",
  prompt: "p",
  summary: "s",
  description: "d",
};

describe("useRoleController", () => {
  it("does not load for the auto role", async () => {
    const { result } = renderHook(() => useRoleController("auto"));

    await waitFor(() => {
      expect(result.current.detail).toBeNull();
    });
    expect(mockLoadRole).not.toHaveBeenCalled();
  });

  it("loads role detail through the api", async () => {
    mockLoadRole.mockResolvedValue(detail);

    const { result } = renderHook(() => useRoleController("keqing"));

    await waitFor(() => {
      expect(result.current.detail).toEqual(detail);
    });
    expect(mockLoadRole).toHaveBeenCalledWith("keqing");
  });

  it("falls back to a summary error payload on failure", async () => {
    mockLoadRole.mockRejectedValue(new Error("boom"));

    const { result } = renderHook(() => useRoleController("keqing"));

    await waitFor(() => {
      expect(result.current.detail?.summary).toBe("boom");
    });
    expect(result.current.detail?.id).toBe("keqing");
  });

  it("resets and reloads when the role changes", async () => {
    mockLoadRole.mockResolvedValue(detail);

    const { result, rerender } = renderHook(({ role }) => useRoleController(role), {
      initialProps: { role: "keqing" },
    });

    await waitFor(() => {
      expect(result.current.detail).toEqual(detail);
    });

    rerender({ role: "march7" });
    expect(result.current.detail).toBeNull();

    await waitFor(() => {
      expect(result.current.detail).toEqual(detail);
    });
    expect(mockLoadRole).toHaveBeenCalledWith("march7");
  });
});

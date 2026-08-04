// @vitest-environment jsdom
import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useResetResearchSelectionOnSessionChange } from "./useResetResearchSelectionOnSessionChange";

describe("useResetResearchSelectionOnSessionChange", () => {
  it("keeps the durable run visible but clears its one-shot chat selection on thread change", () => {
    const setUseInChat = vi.fn();
    const { rerender } = renderHook(
      ({ threadId }) =>
        useResetResearchSelectionOnSessionChange(threadId, setUseInChat),
      { initialProps: { threadId: "chat-a" as string | undefined } },
    );

    expect(setUseInChat).not.toHaveBeenCalled();

    rerender({ threadId: "chat-b" });
    expect(setUseInChat).toHaveBeenCalledTimes(1);
    expect(setUseInChat).toHaveBeenLastCalledWith(false);

    rerender({ threadId: "chat-b" });
    expect(setUseInChat).toHaveBeenCalledTimes(1);
  });
});

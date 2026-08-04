// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { operationRegistry } from "../../app/operationRegistry";
import { WorkspaceProvider } from "../../app/WorkspaceProvider";
import type { WechatStateResponse } from "../../types";
import { useGroupChatController } from "./groupChatController";

const apiMocks = vi.hoisted(() => ({
  createWechatOpening: vi.fn(),
  markWechatRead: vi.fn(),
  resetWechat: vi.fn(),
  sendWechatMessageStream: vi.fn(),
}));

vi.mock("../../api", () => apiMocks);

const initialWechat: WechatStateResponse = {
  group_thread_id: "group-test",
  state: { mode: "interactive_group" },
  content: "",
  unread: "",
  has_unread: false,
  started: false,
  message_count: 0,
  unread_count: 0,
  summary: "",
};

const controllerOptions = (setWechat: (wechat: WechatStateResponse) => void) => ({
  wechat: initialWechat,
  setWechat,
  chatSettings: {
    selectedRole: "auto",
    selectedMode: "auto",
    selectedModel: "flash",
    relationshipMode: "standard",
    contextMode: "fast",
  },
  ragSettings: {
    retrievalMode: "hybrid" as const,
    topK: 5,
    chatTopK: 3,
    minScore: 0,
  },
  ragEnabled: false,
});

describe("useGroupChatController", () => {
  beforeEach(() => {
    operationRegistry.cancelAll();
    vi.clearAllMocks();
  });

  it("clears the draft after resetting the group", async () => {
    const nextWechat = { ...initialWechat, group_thread_id: "group-next" };
    apiMocks.resetWechat.mockResolvedValue(nextWechat);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const setWechat = vi.fn<(wechat: WechatStateResponse) => void>();

    const { result } = renderHook(
      () => useGroupChatController(controllerOptions(setWechat)),
      {
        wrapper: ({ children }) => (
          <WorkspaceProvider initialState={{ activeGroupThreadId: "group-test" }}>
            {children}
          </WorkspaceProvider>
        ),
      },
    );

    act(() => result.current.setInput("old draft"));
    await act(async () => result.current.reset());

    expect(apiMocks.resetWechat).toHaveBeenCalledWith("group-test");
    expect(result.current.threadId).toBe("group-next");
    expect(result.current.input).toBe("");
    expect(setWechat).toHaveBeenCalledWith(nextWechat);
  });

  it("keeps the returned group visible after marking it read", async () => {
    const readWechat = {
      ...initialWechat,
      group_thread_id: "group-read",
      content: "group history",
    };
    apiMocks.markWechatRead.mockResolvedValue(readWechat);
    const setWechat = vi.fn<(wechat: WechatStateResponse) => void>();

    const { result } = renderHook(
      () => useGroupChatController(controllerOptions(setWechat)),
      { wrapper: WorkspaceProvider },
    );

    await act(async () => result.current.markRead());

    expect(result.current.threadId).toBe("group-read");
    expect(setWechat).toHaveBeenCalledWith(readWechat);
    expect(result.current.error).toBe("");
  });

  it("owns streaming send and settles a user stop without stale busy", async () => {
    apiMocks.sendWechatMessageStream.mockImplementation(
      async (_message, _options, handlers, requestOptions) =>
        new Promise((_resolve, reject) => {
          handlers.onSession({
            groupThreadId: "group-test",
            messageId: "group-message",
            operationId: "group-operation",
          });
          handlers.onToken("【纳西妲】\npartial");
          requestOptions.signal.addEventListener("abort", () => {
            reject(new DOMException("stopped", "AbortError"));
          });
        }),
    );
    const setWechat = vi.fn<(wechat: WechatStateResponse) => void>();

    const { result } = renderHook(
      () => useGroupChatController(controllerOptions(setWechat)),
      {
        wrapper: ({ children }) => (
          <WorkspaceProvider initialState={{ activeGroupThreadId: "group-test" }}>
            {children}
          </WorkspaceProvider>
        ),
      },
    );

    await act(async () => result.current.setInput("question"));

    let sendPromise: Promise<void> | undefined;
    await act(async () => {
      sendPromise = result.current.send({ preventDefault: vi.fn() } as never);
      await Promise.resolve();
    });
    expect(result.current.isBusy).toBe(true);

    await act(async () => {
      result.current.stop();
      await sendPromise;
    });

    expect(result.current.isBusy).toBe(false);
    expect(result.current.error).toContain("已停止生成");
    expect(apiMocks.sendWechatMessageStream).toHaveBeenCalledWith(
      "question",
      expect.objectContaining({ groupThreadId: "group-test" }),
      expect.any(Object),
      expect.any(Object),
    );
    expect(setWechat).toHaveBeenLastCalledWith(initialWechat);
    expect(operationRegistry.size).toBe(0);
  });
});

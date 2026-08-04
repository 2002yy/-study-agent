import { describe, expect, it } from "vitest";
import {
  buildContinuationHistory,
  buildRetryHistory,
  buildWorkspaceState,
  hasPartialRecoveryReply,
  sanitizeSingleChatMessages,
  seedMessages,
  tailInterruptedTurn,
  toChatHistoryPayload,
} from "./chatHistory";
import type { ChatMessage } from "../../types";

describe("sanitizeSingleChatMessages", () => {
  it("removes legacy wechat and news workspace messages from single chat history", () => {
    const saved: ChatMessage[] = [
      seedMessages[0],
      { role: "user", content: "讲一下 RAG", avatarRole: "user" },
      { role: "assistant", content: "RAG 是检索增强生成。", avatarRole: "nahida" },
      { role: "user", content: "[群聊] 大家怎么看？", avatarRole: "user" },
      { role: "assistant", content: "【三月七】我觉得可以先拆状态。", avatarRole: "auto" },
      { role: "user", content: "[联网检索] AI 新闻", avatarRole: "user" },
      { role: "assistant", content: "新闻摘要内容", avatarRole: "nahida" },
      { role: "user", content: "[联网搜索] AI 新闻", avatarRole: "user" },
      { role: "assistant", content: "已找到 3 条联网来源。", avatarRole: "nahida" }
    ];

    expect(sanitizeSingleChatMessages(saved)).toEqual([
      seedMessages[0],
      { role: "user", content: "讲一下 RAG", avatarRole: "user" },
      { role: "assistant", content: "RAG 是检索增强生成。", avatarRole: "nahida" }
    ]);
  });

  it("marks the UI welcome message as transient when restoring older localStorage", () => {
    const restored = sanitizeSingleChatMessages([
      {
        role: "assistant",
        avatarRole: "nahida",
        content: seedMessages[0].content
      },
      { role: "user", content: "真实问题", avatarRole: "user" }
    ]);

    expect(restored[0].transient).toBe(true);
    expect(toChatHistoryPayload(restored)).toEqual([{ role: "user", content: "真实问题", avatarRole: "user" }]);
  });

  it("excludes system and transient messages from the model history payload", () => {
    expect(
      toChatHistoryPayload([
        seedMessages[0],
        { role: "system", content: "内部指令" },
        { role: "user", content: "真实问题", avatarRole: "user" },
        { role: "assistant", content: "真实回答", avatarRole: "march7" }
      ])
    ).toEqual([
      { role: "user", content: "真实问题", avatarRole: "user" },
      { role: "assistant", content: "真实回答", avatarRole: "march7" }
    ]);
  });
});

describe("buildWorkspaceState", () => {
  it("migrates legacy sessionId into singleChatSessionId", () => {
    const state = buildWorkspaceState({ sessionId: "legacy-session" });

    expect(state.singleChatSessionId).toBe("legacy-session");
    expect(state.wechatThreadId).toBeUndefined();
  });

  it("keeps single chat and wechat ids isolated while discarding retired news state", () => {
    const state = buildWorkspaceState({
      sessionId: "legacy-session",
      singleChatSessionId: "single-session",
      wechatThreadId: "wechat-thread",
      newsRunId: "news-run",
    });

    expect(state.singleChatSessionId).toBe("single-session");
    expect(state.wechatThreadId).toBe("wechat-thread");
    expect("newsRunId" in state).toBe(false);
  });
});

describe("buildContinuationHistory", () => {
  it("continues an interrupted reply without appending a duplicate user message", () => {
    const history = buildContinuationHistory(
      [
        seedMessages[0],
        { role: "user", content: "继续解释 RAG", avatarRole: "user", transient: true },
        { role: "assistant", content: "生成中断", avatarRole: "auto", transient: true },
      ],
      { question: "继续解释 RAG", reply: "已有半段回答" }
    );

    expect(history.filter((message) => message.role === "user" && message.content === "继续解释 RAG")).toHaveLength(1);
    expect(toChatHistoryPayload(history)).toEqual([
      { role: "user", content: "继续解释 RAG", avatarRole: "user" },
      { role: "assistant", content: "已有半段回答", avatarRole: "auto" },
    ]);
  });
});

describe("tailInterruptedTurn", () => {
  it("does not revive an older interruption after a later retry completed", () => {
    const turns = [
      { turn_id: "old", status: "interrupted", assistant_message: "partial" },
      { turn_id: "retry", status: "completed", assistant_message: "done" },
    ];

    expect(tailInterruptedTurn(turns)).toBeUndefined();
  });

  it("restores the latest turn when that turn is interrupted", () => {
    const turns = [
      { turn_id: "old", status: "superseded", assistant_message: "old" },
      { turn_id: "retry", status: "interrupted", assistant_message: "partial" },
    ];

    expect(tailInterruptedTurn(turns)?.turn_id).toBe("retry");
    expect(hasPartialRecoveryReply(tailInterruptedTurn(turns)?.assistant_message)).toBe(true);
  });

  it("restores a latest zero-token failure as retry-only recovery", () => {
    const turns = [
      { turn_id: "old", status: "completed", assistant_message: "done" },
      { turn_id: "failed", status: "failed", assistant_message: "" },
    ];

    const recovery = tailInterruptedTurn(turns);
    expect(recovery?.turn_id).toBe("failed");
    expect(recovery?.status).toBe("failed");
    expect(recovery?.assistant_message).toBeTruthy();
    expect(hasPartialRecoveryReply(recovery?.assistant_message)).toBe(false);
  });

  it("does not revive a durably abandoned interruption", () => {
    const turns = [
      { turn_id: "old", status: "completed", assistant_message: "done" },
      { turn_id: "abandoned", status: "abandoned", assistant_message: "" },
    ];

    expect(tailInterruptedTurn(turns)).toBeUndefined();
  });
});

describe("buildRetryHistory", () => {
  it("removes a restored interrupted turn using structured turn metadata", () => {
    const messages: ChatMessage[] = [
      { role: "user", content: "older", turnId: "turn-old", turnStatus: "completed" },
      { role: "assistant", content: "older answer", turnId: "turn-old", turnStatus: "completed" },
      { role: "user", content: "question", turnId: "turn-retry", turnStatus: "interrupted" },
      { role: "assistant", content: "partial", turnId: "turn-retry", turnStatus: "interrupted" },
    ];

    expect(
      buildRetryHistory(messages, { question: "question", turnId: "turn-retry" })
    ).toEqual(messages.slice(0, 2));
  });
});

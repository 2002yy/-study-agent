import { describe, expect, it } from "vitest";

import {
  buildWorkspaceTransitionNotice,
  type WorkspaceTransitionState,
} from "./workspaceTransitionGuard";

const idle: WorkspaceTransitionState = {
  isSending: false,
  hasUserMessages: false,
  memoryBusy: false,
  memoryPreviewReady: false,
  researchBusy: false,
  ragWriteBusy: false,
};

describe("workspace transition guard", () => {
  it("does not block a clean session switch", () => {
    expect(buildWorkspaceTransitionNotice("switch", idle)).toBeNull();
  });

  it("reports each owner and its truthful leave effect", () => {
    const notice = buildWorkspaceTransitionNotice("new", {
      ...idle,
      isSending: true,
      hasUserMessages: true,
      summaryStatus: "needs_update",
      memoryPreviewReady: true,
      researchStatus: "partial",
      ragWriteBusy: true,
    });

    expect(notice?.issues.map((issue) => issue.id)).toEqual([
      "chat",
      "memory_preview",
      "research",
      "rag_write",
      "summary",
    ]);
    expect(notice?.issues.find((issue) => issue.id === "rag_write")?.effect).toContain(
      "没有服务端取消能力",
    );
    expect(notice?.issues.find((issue) => issue.id === "memory_preview")?.effect).toContain(
      "不会写入长期记忆",
    );
  });

  it("keeps summarized new sessions explicit without pretending to archive", () => {
    const notice = buildWorkspaceTransitionNotice("new", {
      ...idle,
      hasUserMessages: true,
      summaryStatus: "summarized",
    });
    expect(notice?.issues).toEqual([
      expect.objectContaining({ id: "summary", label: "当前会话已整理但尚未归档" }),
    ]);
    expect(notice?.issues[0].effect).toContain("不会自动归档");
  });

  it("always confirms the recoverable archive transition once", () => {
    const notice = buildWorkspaceTransitionNotice("archive", idle);
    expect(notice?.issues).toEqual([
      expect.objectContaining({ id: "archive", label: "当前会话将进入历史记录" }),
    ]);
  });
});

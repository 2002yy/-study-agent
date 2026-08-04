// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { WechatPanel } from "./WechatPanel";

describe("WechatPanel product boundary", () => {
  it("keeps group discussion but does not embed the legacy news workspace", () => {
    render(
      <WechatPanel
        wechat={null}
        webLookup={null}
        useWebLookup={false}
        setUseWebLookup={vi.fn()}
        wechatInput=""
        setWechatInput={vi.fn()}
        sessionId="group-1"
        onOpening={vi.fn()}
        onReset={vi.fn()}
        onMarkRead={vi.fn()}
        onSendWechat={vi.fn()}
        onStopWechat={vi.fn()}
        isWechatBusy={false}
        error=""
      />,
    );

    expect(screen.getByRole("heading", { name: "群聊与联网" })).toBeInTheDocument();
    expect(screen.getByPlaceholderText("加入群聊说一句...")).toBeInTheDocument();
    expect(screen.queryByText("联网检索")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "读取正文" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "生成摘要" })).not.toBeInTheDocument();
  });
});

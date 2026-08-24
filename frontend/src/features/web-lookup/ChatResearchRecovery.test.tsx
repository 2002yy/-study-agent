// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ChatResearchRecovery } from "./ChatResearchRecovery";
import type { ResearchLookupResponse } from "./researchApi";

function run(status: ResearchLookupResponse["status"]): ResearchLookupResponse {
  return {
    run_id: "research-chat-1",
    query_text: "latest framework release",
    news_items: [],
    source_block: "",
    warnings: [],
    status,
    stage: status === "cancelled" ? "cancelled" : "failed",
    research_context: { run_kind: "chat_tool_loop" },
    query_attempts: [{ status: "provider_failed" }],
    selected_sources: [],
    rejected_sources: [],
    provider_status: "provider_failed",
    stop_reason: status === "cancelled" ? "user_cancelled" : "chat_tool_loop_failed",
    answer_confidence: "",
    error: status === "failed" ? "provider timeout" : "",
    max_items: 8,
    version: 2,
    created_at: "2026-07-15T00:00:00Z",
    updated_at: "2026-07-15T00:00:01Z",
  };
}

describe("ChatResearchRecovery", () => {
  it("shows live progress from the chat preparation stream", () => {
    const { container } = render(
      <ChatResearchRecovery
        run={null}
        progress={{
          run_id: "research-chat-live",
          status: "running",
          stage: "reading",
          provider_status: "",
          stop_reason: "",
          error: "",
          query_attempt_count: 2,
          selected_source_count: 1,
          version: 3,
        }}
        isBusy={false}
        canRetry={false}
        canResume
        useInChat={false}
        onRetry={vi.fn()}
        onResume={vi.fn()}
      />,
    );

    expect(screen.getByRole("status")).toBeTruthy();
    expect(container.querySelector(".spin")).toBeTruthy();
    expect(container.textContent ?? "").toContain("2");
  });

  it("offers a formal retry for a failed chat-owned ResearchRun", () => {
    const onRetry = vi.fn();
    const { container } = render(
      <ChatResearchRecovery
        run={run("failed")}
        isBusy={false}
        canRetry
        canResume={false}
        useInChat={false}
        onRetry={onRetry}
        onResume={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button"));

    expect(container.textContent ?? "").toContain("provider timeout");
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("renders an SSE terminal failure even when durable refresh is stale", () => {
    const { container } = render(
      <ChatResearchRecovery
        run={null}
        progress={{
          run_id: "research-terminal",
          status: "failed",
          stage: "failed",
          provider_status: "provider_failed",
          stop_reason: "chat_tool_loop_failed",
          error: "duckduckgo_html:challenge",
          query_attempt_count: 1,
          selected_source_count: 0,
          version: 4,
        }}
        isBusy={false}
        canRetry={false}
        canResume={false}
        useInChat={false}
        onRetry={vi.fn()}
        onResume={vi.fn()}
      />,
    );

    expect(container.querySelector(".spin")).toBeNull();
    expect(container).toHaveTextContent("研究失败");
    expect(container).toHaveTextContent("本回答未使用联网来源");
  });

  it("keeps partial findings out of chat until the learner explicitly uses them", () => {
    const { container } = render(
      <ChatResearchRecovery
        run={{
          ...run("failed"),
          status: "partial",
          stage: "completed",
          selected_sources: [{ item: { title: "official docs" } }],
          error: "",
        }}
        isBusy={false}
        canRetry
        canResume={false}
        useInChat={false}
        onRetry={vi.fn()}
        onResume={vi.fn()}
      />,
    );

    expect(container).toHaveTextContent("不会自动用于下一轮聊天");
    expect(container).toHaveTextContent("1 个来源");
    expect(container).toHaveTextContent("研究得到部分可用结果");
  });

  it("does not expose standalone research as chat recovery", () => {
    const { container } = render(
      <ChatResearchRecovery
        run={{ ...run("failed"), research_context: { run_kind: "standalone" } }}
        isBusy={false}
        canRetry
        canResume={false}
        useInChat={false}
        onRetry={vi.fn()}
        onResume={vi.fn()}
      />,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("shows parent truth and all four follow-up evidence states", () => {
    const { container } = render(
      <ChatResearchRecovery
        run={{
          ...run("failed"),
          status: "completed",
          stage: "completed",
          parent_run_id: "research-parent",
          research_context: {
            run_kind: "follow_up",
            lineage: {
              parent_query: "Python annotations guide",
              evidence_counts: {
                inherited_candidate: 0,
                revalidated: 1,
                new: 2,
                invalid_or_rejected: 1,
              },
            },
          },
          lineage_summary: {
            search_count: 4,
            read_count: 3,
            child_count: 1,
          },
        }}
        isBusy={false}
        canRetry={false}
        canResume={false}
        useInChat
        onRetry={vi.fn()}
        onResume={vi.fn()}
      />,
    );

    expect(container).toHaveTextContent("已关联父研究");
    expect(container).toHaveTextContent("已重新验证 1");
    expect(container).toHaveTextContent("新来源 2");
    expect(container).toHaveTextContent("已失效/排除 1");
  });
});

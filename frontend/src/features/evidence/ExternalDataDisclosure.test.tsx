// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { ChatResponse } from "../../types";
import { ExternalDataDisclosure, summarizeExternalData } from "./ExternalDataDisclosure";

afterEach(() => cleanup());

const rag = {
  status: "found",
  query: "q",
  retrieval_mode: "hybrid",
  reason: "",
  context: "",
  sources: "",
  result_count: 0,
  results: [],
  debug: {},
  attempts: [],
  rewritten_query: "",
  external_data_policy: {
    web_policy: "auto",
    cloud_context_policy: "allow_local_evidence",
    task_source_policy: "local_and_web",
    web_allowed: true,
    local_retrieval_allowed: true,
    history_allowed: true,
    memory_allowed: true,
    local_evidence_to_model_allowed: true,
    reason: "allowed",
    web_search_performed: true,
    history_sent_to_model: true,
    history_message_count: 2,
    learning_state_sent_to_model: true,
    memory_context_sent_to_model: true,
    local_evidence_sent_to_model: true,
    local_evidence_chunk_count: 1,
  },
  web_tools: {
    enabled: true,
    used: true,
    calls: [
      {
        name: "web_search",
        arguments: { query: "Python 3.12 docs" },
        result: { providers_attempted: ["searxng"], results: [] },
      },
    ],
  },
} as ChatResponse["rag"];

describe("ExternalDataDisclosure", () => {
  it("summarizes policy, query, and provider without exposing local content", () => {
    const evidence = { rag };
    expect(summarizeExternalData(evidence)).toMatchObject({
      queries: ["Python 3.12 docs"],
      providers: ["SearXNG"],
    });
    render(<ExternalDataDisclosure evidence={evidence} />);
    expect(screen.getByLabelText("本轮外发数据说明")).toHaveTextContent(
      "搜索词：Python 3.12 docs",
    );
    expect(screen.getByText(/最近对话/)).toHaveTextContent("已向模型发送 2 条消息");
    expect(screen.getByText(/本地资料/)).toHaveTextContent("已向模型发送 1 个相关片段");
    expect(screen.getByText(/搜索源/)).toHaveTextContent("SearXNG");
  });

  it("renders nothing for legacy turns without a policy snapshot", () => {
    const { container } = render(
      <ExternalDataDisclosure evidence={{ rag: { ...rag, external_data_policy: undefined } }} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});

// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { EvidenceTrail } from "./EvidenceTrail";

afterEach(cleanup);

describe("EvidenceTrail", () => {
  it("keeps recovered ResearchRun provenance without exposing the id in the label", () => {
    const { container } = render(
      <EvidenceTrail
        evidence={{
          rag: {
            status: "found",
            query: "recovered",
            retrieval_mode: "hybrid",
            reason: "",
            context: "",
            sources: "",
            result_count: 0,
            results: [],
            debug: {},
            attempts: [],
            rewritten_query: "",
            web_context: {
              used: true,
              run_id: "research-recovered-1",
              source: "research_run",
            },
          },
        }}
      />,
    );

    expect(container).toHaveTextContent("恢复研究来源");
    expect(container).not.toHaveTextContent("research-recovered-1");

    fireEvent.click(screen.getByRole("button", { name: /证据轨迹/ }));

    expect(
      container.querySelector('[data-research-run-id="research-recovered-1"]'),
    ).toBeTruthy();
  });

  it("marks a restored nested RAG chunk when pedagogy evidence_ids reference its chunk id", () => {
    const { container } = render(
      <EvidenceTrail
        evidence={{
          pedagogy: {
            mode: "socratic",
            phase: "scaffold",
            move: "give_hint",
            disclosure_level: 1,
            evidence_ids: ["chunk-1"],
          },
          rag: {
            status: "found",
            query: "TaskContract",
            retrieval_mode: "hybrid",
            reason: "",
            context: "",
            sources: "",
            result_count: 1,
            results: [
              {
                chunk: {
                  chunk_id: "chunk-1",
                  title: "TaskContract",
                  source_path: "docs/task_contract.md",
                },
                score: 0.82,
              },
            ],
            debug: {},
            attempts: [],
            rewritten_query: "",
          },
        }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /证据轨迹/ }));

    expect(container).toHaveTextContent("统一证据（去重后 1 条）");
    expect(container).toHaveTextContent("TaskContract");
    expect(container).toHaveTextContent("引");
  });
});

import type { Page, Route } from "@playwright/test";

import {
  installApiFixture,
  type ApiFixtureState,
  type SessionDetail,
  type SessionRow,
} from "./api-fixture";

const STORAGE_KEY = "study-agent-react-session";

export const MATERIAL_FILE = "binary-search-notes.md";
export const MATERIAL_REPLY = "根据上传资料，二分查找会在有序区间中每轮排除一半候选。";
export const MATERIAL_SELECTED_TITLE = "binary-search-notes.md";
export const MATERIAL_CANDIDATE_TITLE = "unrelated-notes.md";
export const RESEARCH_RUN_ID = "research-browser-recovery";
export const RESEARCH_REPLY = "恢复的研究资料表明，官方文档建议先确认依赖注入边界。";
export const RESEARCH_SELECTED_TITLE = "FastAPI dependency injection guide";
export const RESEARCH_CANDIDATE_TITLE = "Unselected framework comparison";
export const SOURCE_SESSION_ID = "source-code-learning-session";
export const SOURCE_REPLY = "ChatService.send 负责组织一次聊天请求，并把学习状态与证据快照交给持久化层。";
export const SOURCE_SELECTED_TITLE = "src/application/chat_service.py · ChatService.send";
export const SOURCE_CANDIDATE_TITLE = "src/ui/legacy_sidebar.py";

const MATERIAL_SELECTED_ID = "local-material-selected";
const RESEARCH_SELECTED_ID = "research-selected";
const SOURCE_SELECTED_ID = "github-source-selected";

function now() {
  return "2026-07-27T10:00:00Z";
}

function emptyRag() {
  return {
    status: "waiting",
    query: "",
    retrieval_mode: "hybrid",
    reason: "",
    context: "",
    sources: "",
    result_count: 0,
    results: [],
    debug: {},
    attempts: [],
    rewritten_query: "",
  };
}

function learningState(objective: string, gap: string, nextAction: string) {
  return {
    protocol: "socratic",
    objective,
    phase: "verify",
    confirmed_points: ["已核对主要调用入口"],
    unresolved_gap: gap,
    hint_level: 0,
    turn_count: 2,
    payload: { next_action: nextAction },
  };
}

function pedagogy(evidenceId: string) {
  return {
    mode: "socratic",
    phase: "verify",
    move: "explain",
    disclosure_level: 1,
    evidence_ids: [evidenceId],
  };
}

function materialRag() {
  return {
    status: "found",
    query: "二分查找复杂度",
    retrieval_mode: "hybrid",
    reason: "",
    context: "binary search halves the remaining range",
    sources: MATERIAL_SELECTED_TITLE,
    result_count: 2,
    results: [],
    debug: {},
    attempts: [],
    rewritten_query: "二分查找复杂度",
    evidence_snapshot: {
      schema_version: "evidence-snapshot-v1",
      refs: [
        {
          id: MATERIAL_SELECTED_ID,
          type: "local",
          title: MATERIAL_SELECTED_TITLE,
          source: `uploads/${MATERIAL_FILE}`,
          url: "",
          domain: "",
          score: 0.96,
          lifecycle_status: "selected",
          selection_reason: "adopted_for_answer",
        },
        {
          id: "local-material-candidate",
          type: "local",
          title: MATERIAL_CANDIDATE_TITLE,
          source: "uploads/unrelated-notes.md",
          url: "",
          domain: "",
          score: 0.42,
          lifecycle_status: "candidate",
        },
      ],
    },
  };
}

function researchRag() {
  return {
    status: "found",
    query: "FastAPI dependency injection",
    retrieval_mode: "web_research",
    reason: "",
    context: "official dependency injection guidance",
    sources: RESEARCH_SELECTED_TITLE,
    result_count: 2,
    results: [],
    debug: {},
    attempts: [],
    rewritten_query: "FastAPI dependency injection official guide",
    web_context: {
      used: true,
      run_id: RESEARCH_RUN_ID,
      source: "research_run",
    },
    evidence_snapshot: {
      schema_version: "evidence-snapshot-v1",
      refs: [
        {
          id: RESEARCH_SELECTED_ID,
          type: "research",
          title: RESEARCH_SELECTED_TITLE,
          source: "research-run",
          url: "https://fastapi.tiangolo.com/tutorial/dependencies/",
          domain: "fastapi.tiangolo.com",
          score: 0.95,
          lifecycle_status: "selected",
          provider_status: "found",
          selection_reason: "selected_for_answer",
        },
        {
          id: "research-candidate",
          type: "web_search",
          title: RESEARCH_CANDIDATE_TITLE,
          source: "research-run",
          url: "https://example.com/framework-comparison",
          domain: "example.com",
          score: 0.51,
          lifecycle_status: "candidate",
          provider_status: "found",
        },
      ],
    },
  };
}

function sourceRag() {
  return {
    status: "found",
    query: "ChatService send learning state evidence",
    retrieval_mode: "github_source",
    reason: "",
    context: "ChatService.send coordinates chat state and persistence",
    sources: SOURCE_SELECTED_TITLE,
    result_count: 2,
    results: [],
    debug: {},
    attempts: [],
    rewritten_query: "ChatService.send",
    evidence_snapshot: {
      schema_version: "evidence-snapshot-v1",
      refs: [
        {
          id: SOURCE_SELECTED_ID,
          type: "research",
          title: SOURCE_SELECTED_TITLE,
          source: "2002yy/study-agent",
          url: "https://github.com/2002yy/study-agent/blob/main/src/application/chat_service.py",
          domain: "github.com",
          score: 0.98,
          lifecycle_status: "selected",
          provider_status: "found",
          selection_reason: "symbol_matches_learning_goal",
        },
        {
          id: "github-source-candidate",
          type: "research",
          title: SOURCE_CANDIDATE_TITLE,
          source: "2002yy/study-agent",
          url: "https://github.com/2002yy/study-agent/blob/main/src/ui/legacy_sidebar.py",
          domain: "github.com",
          score: 0.37,
          lifecycle_status: "candidate",
        },
      ],
    },
  };
}

function routeFor(objective: string, state: Record<string, unknown>) {
  return {
    role: "nahida",
    mode: "苏格拉底",
    model_profile: "flash",
    task_contract: {
      task_intent: "learn",
      source_policy: "evidence_required",
      closure_eligibility: "learning_summary",
      learning_state_enabled: true,
    },
    learning_state: state,
    objective,
  };
}

function sessionSettings() {
  return {
    selectedRole: "auto",
    selectedMode: "苏格拉底",
    selectedModel: "auto",
    relationshipMode: "standard",
    contextMode: "light",
    ragEnabled: true,
    ragSettings: {
      retrievalMode: "hybrid",
      topK: 5,
      chatTopK: 3,
      minScore: 0.01,
    },
    keepCurrentRole: false,
  };
}

function persistAnswer(
  state: ApiFixtureState,
  options: {
    sessionId: string;
    question: string;
    reply: string;
    rag: Record<string, unknown>;
    evidenceId: string;
    objective: string;
    gap: string;
    nextAction: string;
    turnId: string;
  },
) {
  const learning = learningState(options.objective, options.gap, options.nextAction);
  const route = routeFor(options.objective, learning);
  const previous = state.details.get(options.sessionId);
  const messages = [
    ...(previous?.messages ?? []),
    {
      role: "user",
      content: options.question,
      avatarRole: "user",
      turnId: options.turnId,
      turnStatus: "completed",
    },
    {
      role: "assistant",
      content: options.reply,
      avatarRole: "nahida",
      turnId: options.turnId,
      turnStatus: "completed",
    },
  ];
  const turns = [
    ...(previous?.turns ?? []),
    {
      turn_id: options.turnId,
      status: "completed",
      user_message: options.question,
      assistant_message: options.reply,
      parent_turn_id: null,
      route_snapshot: route,
      rag_snapshot: options.rag,
      pedagogy_snapshot: pedagogy(options.evidenceId),
    },
  ];
  const row: SessionRow = {
    session_id: options.sessionId,
    kind: "current",
    name: `${options.sessionId}.md`,
    path: "",
    size_bytes: 0,
    mtime_ns: Date.now(),
    title: options.objective,
    task_intent: "learn",
    objective: options.objective,
    confirmed_points: learning.confirmed_points,
    unresolved_gap: options.gap,
    next_action: options.nextAction,
    has_completed_turns: true,
  };
  const detail: SessionDetail = {
    session_id: options.sessionId,
    kind: "current",
    path: "",
    messages,
    turns,
    settings: previous?.settings ?? sessionSettings(),
    route,
    rag: options.rag,
    learning_state: learning,
    pedagogy: {
      ...pedagogy(options.evidenceId),
      committed_learning_state: learning,
    },
    latest_attempted_pedagogy: {},
    navigation: {
      phase: "verify",
      objective: options.objective,
      confirmed_points: learning.confirmed_points,
      unresolved_gap: options.gap,
      next_action: options.nextAction,
    },
    conversation_instruction: "",
  };
  state.sessions = [row, ...state.sessions.filter((item) => item.session_id !== row.session_id)];
  state.details.set(row.session_id, detail);
}

function sse(name: string, data: unknown) {
  return `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`;
}

async function fulfillSse(
  route: Route,
  options: {
    sessionId: string;
    turnId: string;
    reply: string;
    routeData: Record<string, unknown>;
    rag: Record<string, unknown>;
    evidenceId: string;
  },
) {
  const split = Math.ceil(options.reply.length / 2);
  const body = [
    sse("session", {
      session_id: options.sessionId,
      turn_id: options.turnId,
      operation_id: `operation-${options.turnId}`,
    }),
    sse("route", { route: options.routeData }),
    sse("rag", { rag: options.rag }),
    sse("token", { text: options.reply.slice(0, split) }),
    sse("token", { text: options.reply.slice(split) }),
    sse("done", {
      session_id: options.sessionId,
      turn_id: options.turnId,
      reply: options.reply,
      pedagogy: pedagogy(options.evidenceId),
    }),
  ].join("");
  await route.fulfill({
    status: 200,
    contentType: "text/event-stream",
    headers: { "Cache-Control": "no-cache" },
    body,
  });
}

function failedResearchRun() {
  return {
    id: RESEARCH_RUN_ID,
    query: "FastAPI dependency injection",
    stage: "failed",
    status: "failed",
    research_context: { run_kind: "chat_tool_loop" },
    query_attempts: [{ status: "provider_failed", query: "FastAPI dependency injection" }],
    selected_sources: [],
    rejected_sources: [],
    provider_status: "provider_failed",
    stop_reason: "provider_timeout",
    answer_confidence: "",
    items: [],
    source_block: "",
    warnings: [],
    error: "provider timeout",
    max_items: 8,
    version: 1,
    created_at: now(),
    updated_at: now(),
    completed_at: null,
  };
}

function completedResearchRun() {
  return {
    ...failedResearchRun(),
    stage: "completed",
    status: "completed",
    selected_sources: [
      {
        title: RESEARCH_SELECTED_TITLE,
        url: "https://fastapi.tiangolo.com/tutorial/dependencies/",
      },
    ],
    provider_status: "found",
    stop_reason: "completed",
    answer_confidence: "high",
    items: [
      {
        title: RESEARCH_SELECTED_TITLE,
        url: "https://fastapi.tiangolo.com/tutorial/dependencies/",
      },
    ],
    source_block: `${RESEARCH_SELECTED_TITLE}\nhttps://fastapi.tiangolo.com/tutorial/dependencies/`,
    error: "",
    version: 2,
    completed_at: now(),
  };
}

export function makeSourceCodeSession(): { row: SessionRow; detail: SessionDetail } {
  const base: ApiFixtureState = {
    sessions: [],
    details: new Map(),
    failNextChat: false,
    chatAttempts: 0,
    unexpectedApiPaths: [],
  };
  persistAnswer(base, {
    sessionId: SOURCE_SESSION_ID,
    question: "带我从源码理解 ChatService 的调用链",
    reply: SOURCE_REPLY,
    rag: sourceRag(),
    evidenceId: SOURCE_SELECTED_ID,
    objective: "通过 FastAPI 源码理解依赖注入调用链",
    gap: "还不能独立解释依赖解析到 ChatService.send 的路径",
    nextAction: "用自己的话解释一次依赖解析调用链",
    turnId: "turn-source-code-1",
  });
  return {
    row: base.sessions[0],
    detail: base.details.get(SOURCE_SESSION_ID) as SessionDetail,
  };
}

export async function installEvidenceApiFixture(
  page: Page,
  options: {
    sourceSession?: { row: SessionRow; detail: SessionDetail };
  } = {},
) {
  const base = await installApiFixture(page, {
    session: options.sourceSession,
  });
  let uploaded = false;
  let researchRun = failedResearchRun();
  const chatPayloads: Array<Record<string, unknown>> = [];

  await page.route("**/knowledge-base/documents", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        index_path: "browser-fixture",
        index_exists: true,
        index_version: uploaded ? 2 : 1,
        documents: uploaded
          ? [
              {
                document_id: "doc-material",
                revision_id: "rev-material-1",
                title: MATERIAL_SELECTED_TITLE,
                source_path: `uploads/${MATERIAL_FILE}`,
                file_type: "md",
                content_hash: "fixture-material",
                chunks: 2,
                metadata: {},
                evidence_status: "active",
              },
            ]
          : [],
        chunks: uploaded ? 2 : 0,
        retrievable_documents: uploaded ? 1 : 0,
        retrievable_chunks: uploaded ? 2 : 0,
      }),
    });
  });

  await page.route("**/rag-runs/upload", async (route) => {
    uploaded = true;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "rag-upload-browser",
        kind: "upload",
        status: "completed",
        request: { file_count: 1 },
        result: {
          documents: 1,
          chunks: 2,
          index_version: 2,
          stages: [
            { name: "parse", status: "completed" },
            { name: "index", status: "completed" },
          ],
        },
        error: "",
        index_version: 2,
        version: 1,
        created_at: now(),
        updated_at: now(),
        completed_at: now(),
      }),
    });
  });

  await page.route(`**/research-runs/${RESEARCH_RUN_ID}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(researchRun),
    });
  });

  await page.route(`**/research-runs/${RESEARCH_RUN_ID}/retry`, async (route) => {
    researchRun = completedResearchRun();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(researchRun),
    });
  });

  await page.route("**/chat/stream", async (route) => {
    const payload = route.request().postDataJSON() as Record<string, unknown>;
    const question = String(payload.user_input ?? "");
    const webRunId = String(payload.web_context_run_id ?? "");
    const isMaterial = question.includes("刚上传的资料");
    const isResearch = webRunId === RESEARCH_RUN_ID;
    if (!isMaterial && !isResearch) {
      await route.fallback();
      return;
    }

    base.chatAttempts += 1;
    chatPayloads.push(payload);
    const sessionId = String(payload.session_id ?? "") ||
      (isResearch ? "research-evidence-session" : "material-learning-session");
    const turnId = String(payload.turn_id ?? `turn-evidence-${base.chatAttempts}`);
    const rag = isResearch ? researchRag() : materialRag();
    const evidenceId = isResearch ? RESEARCH_SELECTED_ID : MATERIAL_SELECTED_ID;
    const reply = isResearch ? RESEARCH_REPLY : MATERIAL_REPLY;
    const objective = isResearch
      ? "基于恢复研究理解 FastAPI 依赖注入边界"
      : "基于上传资料理解二分查找复杂度";
    const gap = isResearch
      ? "还不能区分框架注入与业务依赖边界"
      : "还不能独立推导对数复杂度";
    const nextAction = isResearch
      ? "解释一次依赖解析边界"
      : "用自己的话解释为什么是对数级";
    const learning = learningState(objective, gap, nextAction);
    const routeData = routeFor(objective, learning);
    persistAnswer(base, {
      sessionId,
      question,
      reply,
      rag,
      evidenceId,
      objective,
      gap,
      nextAction,
      turnId,
    });
    await fulfillSse(route, {
      sessionId,
      turnId,
      reply,
      routeData,
      rag,
      evidenceId,
    });
  });

  return {
    base,
    chatPayloads,
    get uploaded() {
      return uploaded;
    },
    get researchRun() {
      return researchRun;
    },
  };
}

export async function seedEvidenceWorkspace(
  page: Page,
  options: { sessionId?: string; webLookupRunId?: string } = {},
) {
  await page.addInitScript(
    ({ key, workspace }) => {
      window.localStorage.setItem(
        key,
        JSON.stringify({
          schemaVersion: 3,
          savedAt: new Date().toISOString(),
          workspace,
        }),
      );
    },
    {
      key: STORAGE_KEY,
      workspace: {
        singleChatSessionId: options.sessionId,
        lastSessionId: options.sessionId,
        webLookupRunId: options.webLookupRunId,
        ragEnabled: true,
        chatSettings: {
          selectedRole: "auto",
          selectedMode: "苏格拉底",
          selectedModel: "auto",
          relationshipMode: "standard",
          contextMode: "light",
        },
        ragSettings: {
          retrievalMode: "hybrid",
          topK: 5,
          chatTopK: 3,
          minScore: 0.01,
        },
      },
    },
  );
}

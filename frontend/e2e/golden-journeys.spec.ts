import { existsSync, readFileSync, writeFileSync } from "node:fs";

import { expect, test, type Page, type Route, type TestInfo } from "@playwright/test";

import { GOLDEN_JOURNEY_METRICS_PATH } from "./global-setup";

const STORAGE_KEY = "study-agent-react-session";
const FIRST_QUESTION = "什么是二分查找？";
const FIRST_REPLY = "二分查找会在有序序列中反复把候选范围缩小一半。";
const CONTINUE_REPLY = "继续学习：请用自己的话解释左右边界为什么会变化。";
const RETRY_REPLY = "请求已恢复。二分查找每轮排除一半候选范围。";

const EMPTY_RAG = {
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

const RUNTIME_SETTINGS = {
  settings: {
    selected_role: "auto",
    selected_mode: "auto",
    selected_model: "auto",
    relationship_mode: "standard",
    entry_mode: "single",
    performance_mode: "fast",
    memory_mode: "manual",
    debug_mode: false,
    safe_mode: true,
    route_mode: "auto",
    context_mode: "light",
    current_version: "browser-audit",
    active_task: "",
    next_version: "",
    wechat_memory_capture_enabled: false,
    wechat_memory_capture_mode: "off",
    rag_enabled: true,
    rag_retrieval_mode: "hybrid",
    rag_search_top_k: 5,
    rag_chat_top_k: 3,
    rag_top_k: 5,
    rag_min_score: 0.01,
    web_policy: "off",
    cloud_context_policy: "allow_local_evidence",
  },
  options: {
    roles: [{ id: "auto", label: "自动" }],
    modes: [{ id: "auto", label: "自动" }],
    models: [{ id: "auto", label: "自动" }],
    performance_modes: [{ id: "fast", label: "快速" }],
    relationship_modes: [{ id: "standard", label: "标准" }],
    entry_modes: [{ id: "single", label: "单人" }],
    memory_modes: ["manual"],
    retrieval_modes: ["hybrid"],
    web_policies: ["off"],
    cloud_context_policies: ["allow_local_evidence"],
  },
  runtime_profile: {},
  warnings: [],
};

type SessionRow = {
  session_id: string;
  kind: string;
  name: string;
  path: string;
  size_bytes: number;
  mtime_ns: number;
  title: string;
  task_intent: string;
  objective: string;
  confirmed_points: string[];
  unresolved_gap: string;
  next_action: string;
  has_completed_turns: boolean;
};

type SessionDetail = {
  session_id: string;
  kind: string;
  path: string;
  messages: Array<Record<string, unknown>>;
  turns: Array<Record<string, unknown>>;
  settings: Record<string, unknown>;
  route: Record<string, unknown>;
  rag: Record<string, unknown>;
  learning_state: Record<string, unknown>;
  pedagogy: Record<string, unknown>;
  latest_attempted_pedagogy: Record<string, unknown>;
  navigation: Record<string, unknown>;
  conversation_instruction: string;
};

type ApiFixtureState = {
  sessions: SessionRow[];
  details: Map<string, SessionDetail>;
  failNextChat: boolean;
  chatAttempts: number;
  unexpectedApiPaths: string[];
};

type JourneyMetric = {
  journey: string;
  project: string;
  viewport: { width: number; height: number } | null;
  required_clicks: number;
  required_decisions: number;
  product_surfaces: number;
  recovery_clicks: number;
  has_actionable_failure: boolean;
  keyboard_only: boolean;
  refresh_restore: boolean;
  no_horizontal_overflow: boolean;
};

function makeLearningSession(): { row: SessionRow; detail: SessionDetail } {
  const learningState = {
    protocol: "socratic",
    objective: "理解二分查找边界条件",
    phase: "verify",
    confirmed_points: ["每轮缩小搜索区间"],
    unresolved_gap: "左右边界更新时机",
    hint_level: 0,
    turn_count: 3,
    payload: { next_action: "完成一次边界迁移练习" },
  };
  const row: SessionRow = {
    session_id: "returning-learning-session",
    kind: "current",
    name: "returning-learning-session.md",
    path: "",
    size_bytes: 0,
    mtime_ns: 1,
    title: "二分查找",
    task_intent: "learn",
    objective: learningState.objective,
    confirmed_points: learningState.confirmed_points,
    unresolved_gap: learningState.unresolved_gap,
    next_action: "完成一次边界迁移练习",
    has_completed_turns: true,
  };
  const route = {
    role: "nahida",
    mode: "苏格拉底",
    model_profile: "flash",
    task_contract: {
      task_intent: "learn",
      source_policy: "model_only",
      closure_eligibility: "learning_summary",
      learning_state_enabled: true,
    },
    learning_state: learningState,
  };
  const detail: SessionDetail = {
    session_id: row.session_id,
    kind: row.kind,
    path: "",
    messages: [
      {
        role: "user",
        content: "我想学习二分查找边界条件",
        turnId: "turn-returning-1",
        turnStatus: "completed",
      },
      {
        role: "assistant",
        content: "我们已经确认每轮会缩小搜索区间。",
        avatarRole: "nahida",
        turnId: "turn-returning-1",
        turnStatus: "completed",
      },
    ],
    turns: [
      {
        turn_id: "turn-returning-1",
        status: "completed",
        user_message: "我想学习二分查找边界条件",
        assistant_message: "我们已经确认每轮会缩小搜索区间。",
        parent_turn_id: null,
        route_snapshot: route,
        rag_snapshot: EMPTY_RAG,
        pedagogy_snapshot: {
          phase: "verify",
          committed_learning_state: learningState,
        },
      },
    ],
    settings: {
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
    },
    route,
    rag: EMPTY_RAG,
    learning_state: learningState,
    pedagogy: {
      phase: "verify",
      committed_learning_state: learningState,
    },
    latest_attempted_pedagogy: {},
    navigation: {
      phase: "verify",
      objective: learningState.objective,
      confirmed_points: learningState.confirmed_points,
      unresolved_gap: learningState.unresolved_gap,
      next_action: row.next_action,
    },
    conversation_instruction: "",
  };
  return { row, detail };
}

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

function replyFor(question: string, retry: boolean) {
  if (retry) return RETRY_REPLY;
  if (question.includes("继续当前任务")) return CONTINUE_REPLY;
  return FIRST_REPLY;
}

function taskIntentFor(question: string, current?: SessionRow) {
  if (current?.task_intent === "learn" || question.includes("继续当前任务")) return "learn";
  return "quick_answer";
}

async function installApiFixture(
  page: Page,
  options: { session?: { row: SessionRow; detail: SessionDetail }; failNextChat?: boolean } = {},
): Promise<ApiFixtureState> {
  const state: ApiFixtureState = {
    sessions: options.session ? [structuredClone(options.session.row)] : [],
    details: new Map(
      options.session
        ? [[options.session.row.session_id, structuredClone(options.session.detail)]]
        : [],
    ),
    failNextChat: options.failNextChat ?? false,
    chatAttempts: 0,
    unexpectedApiPaths: [],
  };

  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path === "/health") {
      await fulfillJson(route, { status: "ok", service: "study-agent", rag_index_exists: true });
      return;
    }
    if (path === "/rag/status") {
      await fulfillJson(route, {
        index_path: "browser-fixture",
        index_exists: true,
        documents: 1,
        chunks: 1,
        vector_backend: { name: "fixture", available: true },
      });
      return;
    }
    if (path === "/tools") {
      await fulfillJson(route, { tools: [] });
      return;
    }
    if (path === "/workflows/runs") {
      await fulfillJson(route, { runs: [] });
      return;
    }
    if (path === "/runtime/settings") {
      await fulfillJson(route, RUNTIME_SETTINGS);
      return;
    }
    if (path === "/memory") {
      await fulfillJson(route, {
        writable: true,
        memory_mode: "manual",
        safe_mode: true,
        reason: "",
        context_mode: "light",
        groups: {},
        files: [],
      });
      return;
    }
    if (path === "/wechat") {
      await fulfillJson(route, {
        group_thread_id: "",
        state: {},
        content: "",
        unread: "",
        has_unread: false,
        started: false,
        message_count: 0,
        unread_count: 0,
        summary: "",
      });
      return;
    }
    if (path === "/sessions" && request.method() === "GET") {
      await fulfillJson(route, { sessions: state.sessions });
      return;
    }
    if (path.startsWith("/sessions/") && request.method() === "GET") {
      const sessionId = decodeURIComponent(path.slice("/sessions/".length));
      const detail = state.details.get(sessionId);
      if (!detail) {
        await fulfillJson(route, { detail: "session not found" }, 404);
        return;
      }
      await fulfillJson(route, detail);
      return;
    }
    if (path === "/chat/stream" && request.method() === "POST") {
      state.chatAttempts += 1;
      if (state.failNextChat) {
        state.failNextChat = false;
        await route.fulfill({
          status: 503,
          contentType: "text/plain",
          body: "simulated chat outage",
        });
        return;
      }

      const payload = request.postDataJSON() as Record<string, unknown>;
      const question = String(payload.user_input ?? "");
      const requestedSession = String(payload.session_id ?? "");
      const existing = state.sessions.find((item) => item.session_id === requestedSession);
      const sessionId = requestedSession || existing?.session_id || "browser-first-session";
      const turnId = String(payload.turn_id ?? `turn-browser-${state.chatAttempts}`);
      const retry = Boolean(payload.retry_of_turn_id);
      const taskIntent = taskIntentFor(question, existing);
      const reply = replyFor(question, retry);
      const learningState = taskIntent === "learn"
        ? {
            protocol: "socratic",
            objective: existing?.objective || "理解二分查找边界条件",
            phase: "verify",
            confirmed_points: existing?.confirmed_points ?? ["每轮缩小搜索区间"],
            unresolved_gap: existing?.unresolved_gap ?? "左右边界更新时机",
            hint_level: 0,
            turn_count: 4,
            payload: { next_action: existing?.next_action ?? "完成一次边界迁移练习" },
          }
        : {};
      const responseRoute = {
        role: "nahida",
        mode: taskIntent === "learn" ? "苏格拉底" : "auto",
        model_profile: "flash",
        task_contract: {
          task_intent: taskIntent,
          source_policy: "model_only",
          closure_eligibility: taskIntent === "learn" ? "learning_summary" : "not_applicable",
          learning_state_enabled: taskIntent === "learn",
        },
        ...(taskIntent === "learn" ? { learning_state: learningState } : {}),
      };

      const previousDetail = state.details.get(sessionId);
      const nextMessages = [
        ...(previousDetail?.messages ?? []),
        { role: "user", content: question, turnId, turnStatus: "completed" },
        {
          role: "assistant",
          content: reply,
          avatarRole: "nahida",
          turnId,
          turnStatus: "completed",
        },
      ];
      const nextTurns = [
        ...(previousDetail?.turns ?? []),
        {
          turn_id: turnId,
          status: "completed",
          user_message: question,
          assistant_message: reply,
          parent_turn_id: payload.retry_of_turn_id ?? null,
          route_snapshot: responseRoute,
          rag_snapshot: EMPTY_RAG,
          pedagogy_snapshot: taskIntent === "learn"
            ? { phase: "verify", committed_learning_state: learningState }
            : {},
        },
      ];
      const row: SessionRow = {
        session_id: sessionId,
        kind: "current",
        name: `${sessionId}.md`,
        path: "",
        size_bytes: 0,
        mtime_ns: Date.now(),
        title: existing?.title || question,
        task_intent: taskIntent,
        objective: taskIntent === "learn" ? String(learningState.objective) : question,
        confirmed_points: taskIntent === "learn"
          ? (learningState.confirmed_points as string[])
          : [],
        unresolved_gap: taskIntent === "learn"
          ? String(learningState.unresolved_gap)
          : "",
        next_action: taskIntent === "learn"
          ? String((learningState.payload as Record<string, unknown>).next_action)
          : "继续提出下一个问题",
        has_completed_turns: true,
      };
      const detail: SessionDetail = {
        session_id: sessionId,
        kind: "current",
        path: "",
        messages: nextMessages,
        turns: nextTurns,
        settings: previousDetail?.settings ?? {
          selectedRole: "auto",
          selectedMode: "auto",
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
        },
        route: responseRoute,
        rag: EMPTY_RAG,
        learning_state: learningState,
        pedagogy: taskIntent === "learn"
          ? { phase: "verify", committed_learning_state: learningState }
          : {},
        latest_attempted_pedagogy: {},
        navigation: taskIntent === "learn"
          ? {
              phase: "verify",
              objective: learningState.objective,
              confirmed_points: learningState.confirmed_points,
              unresolved_gap: learningState.unresolved_gap,
              next_action: (learningState.payload as Record<string, unknown>).next_action,
            }
          : {},
        conversation_instruction: "",
      };
      state.sessions = [row, ...state.sessions.filter((item) => item.session_id !== sessionId)];
      state.details.set(sessionId, detail);

      const event = (name: string, data: unknown) =>
        `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`;
      const body = [
        event("session", {
          session_id: sessionId,
          turn_id: turnId,
          operation_id: `operation-${state.chatAttempts}`,
        }),
        event("route", { route: responseRoute }),
        event("rag", { rag: EMPTY_RAG }),
        event("token", { text: reply.slice(0, Math.ceil(reply.length / 2)) }),
        event("token", { text: reply.slice(Math.ceil(reply.length / 2)) }),
        event("done", {
          session_id: sessionId,
          turn_id: turnId,
          reply,
          pedagogy: taskIntent === "learn"
            ? { mode: "socratic", phase: "verify", move: "probe", disclosure_level: 1 }
            : undefined,
        }),
      ].join("");
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        headers: { "Cache-Control": "no-cache" },
        body,
      });
      return;
    }

    if (["fetch", "xhr"].includes(request.resourceType())) {
      state.unexpectedApiPaths.push(`${request.method()} ${path}`);
      await fulfillJson(route, { detail: `unhandled browser fixture path: ${path}` }, 404);
      return;
    }
    await route.continue();
  });

  return state;
}

async function focusComposerWithKeyboard(page: Page) {
  const composer = page.getByLabel("输入学习问题");
  for (let presses = 0; presses < 40; presses += 1) {
    if (await composer.evaluate((element) => document.activeElement === element)) {
      return presses;
    }
    await page.keyboard.press("Tab");
  }
  throw new Error("Keyboard focus could not reach the learning composer");
}

async function requiredComposerDecisions(page: Page) {
  return page.locator(
    'form.composer select:visible, form.composer [aria-required="true"]:visible',
  ).count();
}

async function visibleProductSurfaces(page: Page) {
  const selectors = ["main#chat:visible", '[role="dialog"]:visible'];
  let count = 0;
  for (const selector of selectors) count += await page.locator(selector).count();
  return count;
}

async function noHorizontalOverflow(page: Page) {
  return page.evaluate(() =>
    document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
  );
}

async function recordMetric(testInfo: TestInfo, metric: JourneyMetric) {
  const current: JourneyMetric[] = existsSync(GOLDEN_JOURNEY_METRICS_PATH)
    ? JSON.parse(readFileSync(GOLDEN_JOURNEY_METRICS_PATH, "utf8")) as JourneyMetric[]
    : [];
  const next = current
    .filter((item) => !(item.journey === metric.journey && item.project === metric.project))
    .concat(metric)
    .sort((left, right) =>
      `${left.journey}:${left.project}`.localeCompare(`${right.journey}:${right.project}`),
    );
  writeFileSync(GOLDEN_JOURNEY_METRICS_PATH, `${JSON.stringify(next, null, 2)}\n`);
  await testInfo.attach("golden-journey-metric", {
    body: Buffer.from(JSON.stringify(metric, null, 2)),
    contentType: "application/json",
  });
}

async function seedWorkspaceRecovery(page: Page, sessionId: string) {
  await page.addInitScript(
    ({ key, value }) => window.localStorage.setItem(key, value),
    {
      key: STORAGE_KEY,
      value: JSON.stringify({
        schemaVersion: 3,
        savedAt: new Date().toISOString(),
        workspace: {
          singleChatSessionId: sessionId,
          lastSessionId: sessionId,
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
      }),
    },
  );
}

test("first answer needs no configuration decision and survives refresh", async ({ page }, testInfo) => {
  const fixture = await installApiFixture(page);
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "学习工作台" })).toBeVisible();
  const requiredDecisions = await requiredComposerDecisions(page);
  const tabPresses = await focusComposerWithKeyboard(page);
  expect(tabPresses).toBeLessThan(40);
  await page.keyboard.type(FIRST_QUESTION);
  await page.keyboard.press("Enter");

  await expect(page.getByText(FIRST_REPLY, { exact: true })).toBeVisible();
  await page.waitForTimeout(350);
  await page.reload();
  await expect(page.getByText(FIRST_REPLY, { exact: true })).toBeVisible();

  expect(fixture.chatAttempts).toBe(1);
  expect(fixture.unexpectedApiPaths).toEqual([]);
  await recordMetric(testInfo, {
    journey: "first_answer",
    project: testInfo.project.name,
    viewport: page.viewportSize(),
    required_clicks: 0,
    required_decisions: requiredDecisions,
    product_surfaces: await visibleProductSurfaces(page),
    recovery_clicks: 0,
    has_actionable_failure: false,
    keyboard_only: true,
    refresh_restore: true,
    no_horizontal_overflow: await noHorizontalOverflow(page),
  });
});

test("returning learner restores context and continues in one explicit choice", async ({ page }, testInfo) => {
  const session = makeLearningSession();
  const fixture = await installApiFixture(page, { session });
  await seedWorkspaceRecovery(page, session.row.session_id);
  await page.goto("/");

  await expect(page.getByRole("region", { name: "继续当前任务" })).toBeVisible();
  await expect(page.getByText("理解二分查找边界条件", { exact: true })).toBeVisible();
  await expect(page.getByText("每轮缩小搜索区间", { exact: true })).toBeVisible();
  await expect(page.getByText("左右边界更新时机", { exact: true })).toBeVisible();
  await expect(page.getByText("完成一次边界迁移练习", { exact: true })).toBeVisible();

  let requiredClicks = 0;
  let requiredDecisions = 0;
  requiredClicks += 1;
  requiredDecisions += 1;
  await page.getByRole("button", { name: "继续这里" }).click();
  const composer = page.getByLabel("输入学习问题");
  await expect(composer).toHaveValue(/继续当前任务/);
  await composer.press("Enter");
  await expect(page.getByText(CONTINUE_REPLY, { exact: true })).toBeVisible();

  await page.waitForTimeout(350);
  await page.reload();
  await expect(page.getByText(CONTINUE_REPLY, { exact: true })).toBeVisible();
  await expect(page.getByText("理解二分查找边界条件", { exact: true })).toBeVisible();

  expect(fixture.chatAttempts).toBe(1);
  expect(fixture.unexpectedApiPaths).toEqual([]);
  await recordMetric(testInfo, {
    journey: "returning_learning",
    project: testInfo.project.name,
    viewport: page.viewportSize(),
    required_clicks: requiredClicks,
    required_decisions: requiredDecisions,
    product_surfaces: await visibleProductSurfaces(page),
    recovery_clicks: 1,
    has_actionable_failure: false,
    keyboard_only: false,
    refresh_restore: true,
    no_horizontal_overflow: await noHorizontalOverflow(page),
  });
});

test("chat failure exposes one-click retry and restores the answer", async ({ page }, testInfo) => {
  const fixture = await installApiFixture(page, { failNextChat: true });
  await page.goto("/");

  const composer = page.getByLabel("输入学习问题");
  await composer.fill(FIRST_QUESTION);
  await composer.press("Enter");

  await expect(page.getByText(/聊天请求失败：503/)).toBeVisible();
  const retry = page.getByRole("button", { name: "重新生成" });
  await expect(retry).toBeVisible();
  await retry.click();
  await expect(page.getByText(RETRY_REPLY, { exact: true })).toBeVisible();

  await page.waitForTimeout(350);
  await page.reload();
  await expect(page.getByText(RETRY_REPLY, { exact: true })).toBeVisible();

  expect(fixture.chatAttempts).toBe(2);
  expect(fixture.unexpectedApiPaths).toEqual([]);
  await recordMetric(testInfo, {
    journey: "chat_failure_recovery",
    project: testInfo.project.name,
    viewport: page.viewportSize(),
    required_clicks: 1,
    required_decisions: 0,
    product_surfaces: await visibleProductSurfaces(page),
    recovery_clicks: 1,
    has_actionable_failure: true,
    keyboard_only: false,
    refresh_restore: true,
    no_horizontal_overflow: await noHorizontalOverflow(page),
  });
});

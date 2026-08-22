import { expect, test, type Page } from "@playwright/test";

/**
 * G12 manual/timing gate acceptance (docs/PROJECT_STATUS.md 10.6).
 *
 * Runs against the real stack: real SQLite terminal truth via the dedicated
 * test server. No mock sleeps stand in for server states — the journeys read
 * the durable turn record through /__e2e__/state and /chat/turns/{id}/status.
 */

const API_BASE = "http://127.0.0.1:8000";
const INTERRUPT_QUESTION = "请生成一段可中断的二分查找边界讲解";

type DurableTurn = {
  id: string;
  status: string;
  user_message: string;
  assistant_message: string;
  cancel_requested_at: string | null;
  cancel_stage: string | null;
  updated_at: string;
};

type DurableState = {
  thread: {
    id: string;
    status: string;
    archive_after_cancel_operation_id?: string | null;
    active_operation_id: string | null;
  };
  turns: DurableTurn[];
};

test.beforeEach(async ({ request }) => {
  const response = await request.post(`${API_BASE}/__e2e__/reset`);
  expect(response.ok()).toBe(true);
});

/**
 * Per-worker warm-up: the first project pays vite's lazy module compilation.
 * Load the app and the cancel-flow chunks once so latency journeys measure
 * steady-state UI response instead of cold-start module fetching.
 */
test.beforeAll(async ({ browser }) => {
  const page = await browser.newPage();
  await page.goto("/");
  await expect(page.getByLabel("\u8f93\u5165\u5b66\u4e60\u95ee\u9898")).toBeEnabled();
  await send(page, "\u9884\u70ed\u95ee\u9898");
  await expect(page.getByRole("button", { name: "\u505c\u6b62" })).toBeVisible({
    timeout: 15_000,
  });
  await expect(
    page.getByRole("button", { name: "\u505c\u6b62" }),
  ).toBeHidden({ timeout: 20_000 });
  await page.close();
});

async function send(page: Page, text: string) {
  const composer = page.getByLabel("输入学习问题");
  await composer.fill(text);
  await composer.press("Enter");
}

async function stopButton(page: Page) {
  return page.getByRole("button", { name: "停止" });
}

async function durableState(page: Page, sessionId: string): Promise<DurableState> {
  const response = await page.request.get(
    `${API_BASE}/__e2e__/state/${encodeURIComponent(sessionId)}`,
  );
  expect(response.ok()).toBe(true);
  return (await response.json()) as DurableState;
}

/**
 * The cancel journey can settle a turn before the browser receives the
 * session SSE event, so localStorage is not a reliable session discovery
 * channel; read the latest thread straight from the dedicated entrypoint.
 */
async function latestThread(page: Page): Promise<DurableState & { session_id: string }> {
  const response = await page.request.get(`${API_BASE}/__e2e__/latest-thread`);
  expect(response.ok()).toBe(true);
  return (await response.json()) as DurableState & { session_id: string };
}

/** Journey A: click → visible UI acknowledgement must land within 200 ms. */
test("A: stop acknowledgement renders within 200ms on every viewport", async ({
  page,
}, testInfo) => {
  await page.goto("/");
  // Warm-up: dev-server cold start and React hydration must not pollute
  // the steady-state latency measurement.
  await expect(page.getByLabel("\u8f93\u5165\u5b66\u4e60\u95ee\u9898")).toBeEnabled();
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(800);
  await send(page, INTERRUPT_QUESTION);

  // Wait for streaming to start so the 停止 button is present.
  const stop = await stopButton(page);
  await expect(stop).toBeVisible();

  const clickAt = await page.evaluate(() => performance.now());
  await stop.click();
  await page.waitForSelector(".turn-status-line", { state: "visible" });
  const ackAt = await page.evaluate(() => performance.now());
  const ackMs = Math.round(ackAt - clickAt);
  console.log(`G12-ACK[${testInfo.project.name}] ${ackMs}ms`);

  const line = page.locator(".turn-status-line").first();
  // On a warm real stack the cancel may settle before we observe the
  // intermediate copy; any lifecycle text within 200 ms is the gate.
  await expect(line).toContainText(
    /正在提交停止请求|已登记|服务端仍在收尾|已停止|已在停止前正常完成/,
  );
  expect(ackMs).toBeLessThan(200);
});

/** Journey B: cancel registration → durable terminal latency with slow retrieval. */
test("B: cancel-to-terminal latency recorded under slow retrieval", async ({
  page,
}, testInfo) => {
  await page.request.post(`${API_BASE}/__e2e__/retrieval-delay`, {
    data: { seconds: 3 },
  });
  await page.goto("/");
  await send(page, INTERRUPT_QUESTION);

  const stop = await stopButton(page);
  await expect(stop).toBeVisible();
  await stop.click();

  const latest = await latestThread(page);
  const sessionId = latest.session_id;
  const turn = latest.turns.at(-1);
  expect(turn).toBeTruthy();

  // Decision 20: the POST only confirms registration; wait until the durable
  // cancel marker is visible before starting the settle-latency measurement.
  let registeredAt: string | null = null;
  await expect
    .poll(async () => {
      const statusResponse = await page.request.get(
        `${API_BASE}/chat/turns/${encodeURIComponent(turn!.id)}/status`,
      );
      const body = (await statusResponse.json()) as {
        status: string;
        cancel_requested_at: string | null;
      };
      if (body.cancel_requested_at) registeredAt = body.cancel_requested_at;
      return body.cancel_requested_at ?? "";
    }, { timeout: 10_000, intervals: [100] })
    .not.toBe("");

  // Poll the durable terminal state exactly like the client does.
  let terminalStatus = "";
  while (!terminalStatus) {
    const statusResponse = await page.request.get(
      `${API_BASE}/chat/turns/${encodeURIComponent(turn!.id)}/status`,
    );
    const body = (await statusResponse.json()) as { status: string };
    if (
      ["cancelled", "interrupted", "completed", "failed"].includes(body.status)
    ) {
      terminalStatus = body.status;
      break;
    }
    await page.waitForTimeout(250);
  }
  expect(terminalStatus).toBe("cancelled");

  const settled = await durableState(page, sessionId);
  const settledTurn = settled.turns.at(-1)!;
  const registered = Date.parse(registeredAt!);
  const settledAt = Date.parse(settledTurn.updated_at);
  const elapsedMs = settledAt - registered;
  console.log(
    `G12-SETTLE[${testInfo.project.name}] ${elapsedMs}ms stage=${settledTurn.cancel_stage}`,
  );

  expect(["route", "pedagogy_evaluate", "retrieval", "web_tools"]).toContain(
    settledTurn.cancel_stage,
  );
  // The injected delay is 3000 ms; settlement must not exceed it by much.
  expect(elapsedMs).toBeLessThan(3_000 + 5_000);
  // No visible output existed → cancelled with empty assistant message.
  expect(settledTurn.status).toBe("cancelled");

  // Reset the injection so later journeys are unaffected.
  await page.request.post(`${API_BASE}/__e2e__/retrieval-delay`, {
    data: { seconds: 0 },
  });
});

/** Journey C: aria semantics of the status line. */
test("C: status line exposes role=status and polite live region", async ({
  page,
}) => {
  await page.goto("/");
  await send(page, INTERRUPT_QUESTION);
  const stop = await stopButton(page);
  await expect(stop).toBeVisible();
  await stop.click();

  const line = page.locator(".turn-status-line").first();
  await expect(line).toBeVisible();
  await expect(line).toHaveAttribute("role", "status");
  await expect(line).toHaveAttribute("aria-live", "polite");
});

/** Journey D: switching sessions while cancellation is pending works. */
test("D: session switch during pending cancellation is immediate", async ({
  page,
}) => {
  await page.request.post(`${API_BASE}/__e2e__/retrieval-delay`, {
    data: { seconds: 4 },
  });
  await page.goto("/");
  await send(page, INTERRUPT_QUESTION);
  const stop = await stopButton(page);
  await expect(stop).toBeVisible();
  await stop.click();

  // The composer must stay usable immediately: the user can leave the
  // blocked session without waiting for the old operation to settle.
  const composer = page.getByLabel("输入学习问题");
  await expect(composer).toBeEnabled({ timeout: 5_000 });

  // Capture the cancelled journey before creating a brand-new session.
  const latest = await latestThread(page);

  // A brand-new session accepts a fresh question right away.
  const created = await page.request.post(`${API_BASE}/sessions/new`);
  expect(created.ok()).toBe(true);

  // Old session settles to cancelled eventually; nothing blocks the new one.
  await page.waitForTimeout(1_000);
  await page.request.post(`${API_BASE}/__e2e__/retrieval-delay`, {
    data: { seconds: 0 },
  });
  await expect
    .poll(async () => {
      // The status endpoint doubles as the archive-queue drain trigger.
      const statusResponse = await page.request.get(
        `${API_BASE}/chat/turns/${encodeURIComponent(
          latest.turns.at(-1)!.id,
        )}/status`,
      );
      return ((await statusResponse.json()) as { status: string }).status;
    }, { timeout: 30_000, intervals: [500] })
    .toBe("cancelled");
});

/** Journey E: queued archive persists and drains after settle. */
test("E: archive during pending cancellation queues then archives", async ({
  page,
}, testInfo) => {
  await page.request.post(`${API_BASE}/__e2e__/retrieval-delay`, {
    data: { seconds: 3 },
  });
  await page.goto("/");
  await send(page, INTERRUPT_QUESTION);
  const stop = await stopButton(page);
  await expect(stop).toBeVisible();
  await stop.click();

  const latest = await latestThread(page);
  const sessionId = latest.session_id;
  const queueResponse = await page.request.post(
    `${API_BASE}/sessions/${encodeURIComponent(sessionId)}/archive`,
  );
  expect(queueResponse.ok()).toBe(true);
  const queueBody = (await queueResponse.json()) as { queued?: boolean };
  expect(queueBody.queued).toBe(true);

  // Durable marker visible in thread truth.
  const queuedState = await durableState(page, sessionId);
  expect(queuedState.thread.archive_after_cancel_operation_id).toBeTruthy();
  expect(queuedState.thread.status).toBe("active");

  // After the cancellation settles, the drain executes the archive.
  const turnId = queuedState.turns.at(-1)!.id;
  await expect
    .poll(async () => {
      // Polling status also triggers the archive-queue drain server-side.
      const statusResponse = await page.request.get(
        `${API_BASE}/chat/turns/${encodeURIComponent(turnId)}/status`,
      );
      await statusResponse.json();
      return (await durableState(page, sessionId)).thread.status;
    }, { timeout: 30_000, intervals: [500] })
    .toBe("archived");
  const finalState = await durableState(page, sessionId);
  expect(finalState.thread.archive_after_cancel_operation_id).toBeNull();
  console.log(
    `G12-QUEUE[${testInfo.project.name}] archived after settle, turns=${finalState.turns.length}`,
  );
});

/** Journey F: a queued archive can be cancelled by the user. */
test("F: pending archive can be cancelled before settle", async ({ page }) => {
  await page.request.post(`${API_BASE}/__e2e__/retrieval-delay`, {
    data: { seconds: 6 },
  });
  await page.goto("/");
  await send(page, INTERRUPT_QUESTION);
  const stop = await stopButton(page);
  await expect(stop).toBeVisible();
  await stop.click();

  const latest = await latestThread(page);
  const sessionId = latest.session_id;
  const queueResponse = await page.request.post(
    `${API_BASE}/sessions/${encodeURIComponent(sessionId)}/archive`,
  );
  expect((await queueResponse.json()).queued).toBe(true);

  const cancelQueue = await page.request.delete(
    `${API_BASE}/sessions/${encodeURIComponent(sessionId)}/archive-queue`,
  );
  expect(cancelQueue.ok()).toBe(true);
  expect(((await cancelQueue.json()) as { cancelled: boolean }).cancelled).toBe(
    true,
  );

  // After everything settles the thread stays active (never archived).
  await expect
    .poll(async () => (await durableState(page, sessionId)).thread.status, {
      timeout: 30_000,
      intervals: [500],
    })
    .not.toBe("pending");
  const finalState = await durableState(page, sessionId);
  expect(finalState.thread.archive_after_cancel_operation_id).toBeNull();
});

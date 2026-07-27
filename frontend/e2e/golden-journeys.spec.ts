import { expect, test } from "@playwright/test";

import {
  CONTINUE_REPLY,
  FIRST_QUESTION,
  FIRST_REPLY,
  RETRY_REPLY,
  installApiFixture,
  makeLearningSession,
  seedWorkspaceRecovery,
} from "./api-fixture";
import {
  focusComposerWithKeyboard,
  noHorizontalOverflow,
  recordMetric,
  requiredComposerDecisions,
  visibleProductSurfaces,
} from "./journey-metrics";

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

  const restoreCard = page.getByRole("region", { name: "继续当前任务" });
  await expect(restoreCard).toBeVisible();
  await expect(
    restoreCard.getByText("理解二分查找边界条件", { exact: true }),
  ).toBeVisible();
  await expect(
    restoreCard.getByText("每轮缩小搜索区间", { exact: true }),
  ).toBeVisible();
  await expect(
    restoreCard.getByText("左右边界更新时机", { exact: true }),
  ).toBeVisible();
  await expect(
    restoreCard.getByText("完成一次边界迁移练习", { exact: true }),
  ).toBeVisible();

  let requiredClicks = 0;
  let requiredDecisions = 0;
  requiredClicks += 1;
  requiredDecisions += 1;
  await restoreCard.getByRole("button", { name: "继续这里" }).click();
  const composer = page.getByLabel("输入学习问题");
  await expect(composer).toHaveValue(/继续当前任务/);
  await composer.press("Enter");
  await expect(page.getByText(CONTINUE_REPLY, { exact: true })).toBeVisible();

  await page.waitForTimeout(350);
  await page.reload();
  await expect(page.getByText(CONTINUE_REPLY, { exact: true })).toBeVisible();
  const restoredCard = page.getByRole("region", { name: "继续当前任务" });
  await expect(
    restoredCard.getByText("理解二分查找边界条件", { exact: true }),
  ).toBeVisible();

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

  await expect(page.getByText(/聊天请求失败：503/).first()).toBeVisible();
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

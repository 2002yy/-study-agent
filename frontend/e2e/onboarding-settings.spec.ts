import { expect, test } from "@playwright/test";

import { FIRST_QUESTION, FIRST_REPLY, installApiFixture } from "./api-fixture";
import {
  noHorizontalOverflow,
  recordMetric,
  visibleProductSurfaces,
} from "./journey-metrics";

test("new session keeps direct input primary and progressively reveals explicit task overrides", async ({ page }, testInfo) => {
  const fixture = await installApiFixture(page);
  await page.goto("/");

  const start = page.getByRole("region", { name: "开始新任务" });
  await expect(start.getByRole("heading", { name: "直接输入问题即可开始" })).toBeVisible();
  await expect(start.getByRole("button", { name: /系统学习/ })).toBeVisible();
  await expect(start.getByRole("button", { name: /上传资料/ })).toBeVisible();
  await expect(start.getByRole("button", { name: /快速问答/ })).toHaveCount(0);
  await expect(start.getByRole("button", { name: /联网研究/ })).toHaveCount(0);
  await expect(start.getByRole("button", { name: /项目推进/ })).toHaveCount(0);

  await start.getByText("更多开始方式").click();
  await expect(start.getByRole("button", { name: /联网研究/ })).toBeVisible();
  await expect(start.getByRole("button", { name: /项目推进/ })).toBeVisible();

  const composer = page.getByLabel("输入学习问题");
  await composer.fill(FIRST_QUESTION);
  await composer.press("Enter");
  await expect(page.getByText(FIRST_REPLY, { exact: true })).toBeVisible();

  expect(fixture.chatAttempts).toBe(1);
  expect(fixture.unexpectedApiPaths).toEqual([]);
  await recordMetric(testInfo, {
    journey: "progressive_onboarding",
    project: testInfo.project.name,
    viewport: page.viewportSize(),
    required_clicks: 0,
    required_decisions: 0,
    product_surfaces: await visibleProductSurfaces(page),
    recovery_clicks: 0,
    has_actionable_failure: false,
    keyboard_only: false,
    refresh_restore: false,
    no_horizontal_overflow: await noHorizontalOverflow(page),
  });
});

test("ordinary settings hide engineering controls until advanced disclosure", async ({ page }, testInfo) => {
  const fixture = await installApiFixture(page);
  await page.goto("/");

  await page.getByLabel("打开更多学习工具").click();
  await page.getByRole("menuitem", { name: /设置/ }).click();

  const settings = page.getByRole("region", { name: "学习设置" });
  await expect(settings).toBeVisible();
  await expect(settings.getByRole("combobox", { name: "学习方式" })).toBeVisible();
  await expect(settings.getByRole("combobox", { name: "互动氛围" })).toBeVisible();
  await expect(settings.getByRole("checkbox", { name: "回答时使用我的资料" })).toBeVisible();
  await expect(settings.getByRole("combobox", { name: "联网策略" })).toBeVisible();
  await expect(settings.getByRole("combobox", { name: "模型上下文" })).toBeVisible();

  await expect(settings.getByRole("combobox", { name: "角色" })).toHaveCount(0);
  await expect(settings.getByRole("combobox", { name: "模型档位" })).toHaveCount(0);
  await expect(settings.getByRole("combobox", { name: "上下文深度" })).toHaveCount(0);
  await expect(settings.getByRole("combobox", { name: "检索方式" })).toHaveCount(0);

  await settings.getByText("高级设置", { exact: true }).click();
  await expect(settings.getByRole("combobox", { name: "角色" })).toBeVisible();
  await expect(settings.getByLabel("本会话微调")).toBeVisible();
  await expect(settings.getByRole("combobox", { name: "模型档位" })).toBeVisible();
  await expect(settings.getByRole("combobox", { name: "上下文深度" })).toBeVisible();
  await expect(settings.getByRole("combobox", { name: "检索方式" })).toBeVisible();
  await expect(settings.getByRole("spinbutton", { name: "候选来源" })).toBeVisible();
  await expect(settings.getByRole("spinbutton", { name: "回答引用" })).toBeVisible();
  await expect(settings.getByRole("spinbutton", { name: "最低相关度" })).toBeVisible();

  expect(fixture.unexpectedApiPaths).toEqual([]);
  const noOverflow = await noHorizontalOverflow(page);
  expect(noOverflow).toBe(true);
  await recordMetric(testInfo, {
    journey: "progressive_settings",
    project: testInfo.project.name,
    viewport: page.viewportSize(),
    required_clicks: 3,
    required_decisions: 0,
    product_surfaces: await visibleProductSurfaces(page),
    recovery_clicks: 0,
    has_actionable_failure: false,
    keyboard_only: false,
    refresh_restore: false,
    no_horizontal_overflow: noOverflow,
  });
});

test("provider health is checked on demand and leaves chat interaction unlocked", async ({ page }) => {
  const fixture = await installApiFixture(page);
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  await page.goto("/");

  await page.getByLabel("打开更多学习工具").click();
  await page.getByRole("menuitem", { name: /设置/ }).click();
  const settings = page.getByRole("region", { name: "学习设置" });

  await expect(settings.getByText("仅在点击时检查，不影响应用启动和聊天。")).toBeVisible();
  await settings.getByRole("button", { name: "检测联网搜索" }).click();
  await expect(settings.getByText("首选搜索源可用，可以正常联网检索。")).toBeVisible();
  await expect(settings.getByRole("list", { name: "联网搜索源状态" })).toContainText("SearXNG可用");

  await page.getByRole("button", { name: "关闭设置", exact: true }).click();
  await expect(page.getByLabel("输入学习问题")).toBeEnabled();
  expect(fixture.unexpectedApiPaths).toEqual([]);
  expect(consoleErrors).toEqual([]);
});

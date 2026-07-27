import { existsSync, readFileSync, writeFileSync } from "node:fs";

import type { Page, TestInfo } from "@playwright/test";

import { GOLDEN_JOURNEY_METRICS_PATH } from "./global-setup";

export type JourneyMetric = {
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

export async function focusComposerWithKeyboard(page: Page) {
  const composer = page.getByLabel("输入学习问题");
  for (let presses = 0; presses < 40; presses += 1) {
    if (await composer.evaluate((element) => document.activeElement === element)) {
      return presses;
    }
    await page.keyboard.press("Tab");
  }
  throw new Error("Keyboard focus could not reach the learning composer");
}

export async function requiredComposerDecisions(page: Page) {
  return page.locator(
    'form.composer select:visible, form.composer [aria-required="true"]:visible',
  ).count();
}

export async function visibleProductSurfaces(page: Page) {
  const selectors = ["main#chat:visible", '[role="dialog"]:visible'];
  let count = 0;
  for (const selector of selectors) count += await page.locator(selector).count();
  return count;
}

export async function noHorizontalOverflow(page: Page) {
  return page.evaluate(() =>
    document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
  );
}

export async function recordMetric(testInfo: TestInfo, metric: JourneyMetric) {
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

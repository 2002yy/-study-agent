import { defineConfig } from "@playwright/test";

const REAL_STACK_TESTS = [
  "**/real-stack.spec.ts",
  "**/real-stack-recovery.spec.ts",
  "**/real-stack-research.spec.ts",
];
const STANDARD_FIXTURE_IGNORES = [
  ...REAL_STACK_TESTS,
  "**/complex-content.spec.ts",
];

export default defineConfig({
  testDir: "./e2e",
  testIgnore: REAL_STACK_TESTS,
  globalSetup: "./e2e/global-setup.ts",
  globalTeardown: "./e2e/global-teardown.ts",
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  expect: {
    timeout: 7_000,
  },
  outputDir: "test-results/artifacts",
  reporter: [
    ["line"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:5173",
    channel: process.env.PLAYWRIGHT_USE_SYSTEM_CHROME ? "chrome" : undefined,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "desktop-chromium",
      testIgnore: STANDARD_FIXTURE_IGNORES,
      use: {
        browserName: "chromium",
        viewport: { width: 1440, height: 900 },
      },
    },
    {
      name: "mobile-chromium",
      testIgnore: STANDARD_FIXTURE_IGNORES,
      use: {
        browserName: "chromium",
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
    {
      name: "narrow-chromium",
      testMatch: [
        "**/complex-content.spec.ts",
        "**/extension-lab-journeys.spec.ts",
        "**/recovery-visibility.spec.ts",
      ],
      testIgnore: REAL_STACK_TESTS,
      use: {
        browserName: "chromium",
        viewport: { width: 360, height: 520 },
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
  webServer: {
    command: "npm run dev -- --host 127.0.0.1",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: false,
    timeout: 60_000,
  },
});

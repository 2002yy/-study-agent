import { existsSync, readFileSync, statSync } from "node:fs";
import { resolve } from "node:path";

import {
  GOLDEN_JOURNEY_METRICS_PATH,
  GOLDEN_JOURNEY_SUCCESS_DIR,
  GOLDEN_JOURNEY_SUCCESS_MANIFEST_PATH,
} from "./global-setup";
import type { JourneyMetric, SuccessArtifact } from "./journey-metrics";

const EXPECTED_STEPS: Record<string, string[]> = {
  first_answer: ["ready", "completed", "restored"],
  returning_learning: ["restored-context", "continued", "continued-restored"],
  chat_failure_recovery: ["failure-visible", "recovered", "recovered-restored"],
};
const EXPECTED_PROJECTS = ["desktop-chromium", "mobile-chromium"];

function requireFile(path: string, label: string) {
  if (!existsSync(path)) throw new Error(`${label} is missing: ${path}`);
  if (statSync(path).size <= 0) throw new Error(`${label} is empty: ${path}`);
}

export default function globalTeardown() {
  requireFile(GOLDEN_JOURNEY_SUCCESS_MANIFEST_PATH, "Success manifest");
  requireFile(GOLDEN_JOURNEY_METRICS_PATH, "Journey metrics");

  const manifest = JSON.parse(
    readFileSync(GOLDEN_JOURNEY_SUCCESS_MANIFEST_PATH, "utf8"),
  ) as SuccessArtifact[];
  const metrics = JSON.parse(
    readFileSync(GOLDEN_JOURNEY_METRICS_PATH, "utf8"),
  ) as JourneyMetric[];

  const expectedArtifactKeys = new Set<string>();
  for (const [journey, steps] of Object.entries(EXPECTED_STEPS)) {
    for (const project of EXPECTED_PROJECTS) {
      for (const step of steps) expectedArtifactKeys.add(`${journey}:${project}:${step}`);
    }
  }
  const actualArtifactKeys = new Set(
    manifest.map((item) => `${item.journey}:${item.project}:${item.step}`),
  );
  if (manifest.length !== expectedArtifactKeys.size) {
    throw new Error(
      `Expected ${expectedArtifactKeys.size} selected success artifacts, received ${manifest.length}`,
    );
  }
  for (const key of expectedArtifactKeys) {
    if (!actualArtifactKeys.has(key)) throw new Error(`Missing success artifact manifest entry: ${key}`);
  }

  for (const item of manifest) {
    if (item.screenshot_mode !== "viewport") {
      throw new Error(`Success artifact must use viewport capture: ${item.file}`);
    }
    if (!item.viewport || item.viewport.width <= 0 || item.viewport.height <= 0) {
      throw new Error(`Success artifact has invalid viewport: ${item.file}`);
    }
    if (!item.product_surfaces.includes("main")) {
      throw new Error(`Success artifact does not identify the main product surface: ${item.file}`);
    }
    requireFile(resolve(GOLDEN_JOURNEY_SUCCESS_DIR, item.file), "Success screenshot");
  }

  for (const journey of Object.keys(EXPECTED_STEPS)) {
    for (const project of EXPECTED_PROJECTS) {
      const metric = metrics.find(
        (item) => item.journey === journey && item.project === project,
      );
      if (!metric) throw new Error(`Missing observed metric: ${journey}:${project}`);
      if (!metric.action_summary) {
        throw new Error(`Observed metric has no action summary: ${journey}:${project}`);
      }
      if (metric.success_artifacts?.length !== EXPECTED_STEPS[journey].length) {
        throw new Error(`Observed metric has incomplete success artifacts: ${journey}:${project}`);
      }
      for (const file of metric.success_artifacts) {
        if (!manifest.some((item) => item.file === file)) {
          throw new Error(`Observed metric references an unknown success artifact: ${file}`);
        }
      }
    }
  }
}

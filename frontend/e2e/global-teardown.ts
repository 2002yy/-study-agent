import { existsSync, readFileSync, statSync } from "node:fs";
import { resolve } from "node:path";

import {
  GOLDEN_JOURNEY_METRICS_PATH,
  GOLDEN_JOURNEY_SUCCESS_DIR,
  GOLDEN_JOURNEY_SUCCESS_MANIFEST_PATH,
} from "./global-setup";
import type { JourneyMetric, SuccessArtifact } from "./journey-metrics";

type ExpectedJourney = {
  journey: string;
  projects: string[];
  steps: string[];
};

type ComplexArtifact = SuccessArtifact & {
  conversation_scroll_top?: number;
  conversation_scroll_height?: number;
  conversation_client_height?: number;
  conversation_distance_from_bottom?: number;
};

const GOLDEN_JOURNEY_SAMPLES: Array<{ journey: string; steps: string[] }> = [
  {
    journey: "first_answer",
    steps: ["ready", "completed", "restored"],
  },
  {
    journey: "returning_learning",
    steps: ["restored-context", "continued", "continued-restored"],
  },
  {
    journey: "chat_failure_recovery",
    steps: ["failure-visible", "recovered", "recovered-restored"],
  },
  {
    journey: "stale_revalidation",
    steps: ["stale-visible", "revalidated-current", "revalidated-restored"],
  },
];

const EXPECTED_JOURNEYS: ExpectedJourney[] = [
  ...GOLDEN_JOURNEY_SAMPLES.map((sample) => ({
    ...sample,
    projects: [
      "desktop-chromium",
      "mobile-chromium",
      "desktop-firefox",
      "desktop-webkit",
    ],
  })),
  {
    journey: "complex_content_narrow",
    projects: ["narrow-chromium"],
    steps: [
      "long-text-and-url",
      "wide-code",
      "user-scrolled",
      "back-to-latest",
      "restored",
    ],
  },
];

function requireFile(path: string, label: string) {
  if (!existsSync(path)) throw new Error(`${label} is missing: ${path}`);
  if (statSync(path).size <= 0) throw new Error(`${label} is empty: ${path}`);
}

export default function globalTeardown() {
  requireFile(GOLDEN_JOURNEY_SUCCESS_MANIFEST_PATH, "Success manifest");
  requireFile(GOLDEN_JOURNEY_METRICS_PATH, "Journey metrics");

  const manifest = JSON.parse(
    readFileSync(GOLDEN_JOURNEY_SUCCESS_MANIFEST_PATH, "utf8"),
  ) as ComplexArtifact[];
  const metrics = JSON.parse(
    readFileSync(GOLDEN_JOURNEY_METRICS_PATH, "utf8"),
  ) as JourneyMetric[];

  const expectedArtifactKeys = new Set<string>();
  for (const expected of EXPECTED_JOURNEYS) {
    for (const project of expected.projects) {
      for (const step of expected.steps) {
        expectedArtifactKeys.add(`${expected.journey}:${project}:${step}`);
      }
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
    if (!actualArtifactKeys.has(key)) {
      throw new Error(`Missing success artifact manifest entry: ${key}`);
    }
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

  for (const expected of EXPECTED_JOURNEYS) {
    for (const project of expected.projects) {
      const metric = metrics.find(
        (item) => item.journey === expected.journey && item.project === project,
      );
      if (!metric) throw new Error(`Missing observed metric: ${expected.journey}:${project}`);
      if (!metric.action_summary) {
        throw new Error(`Observed metric has no action summary: ${expected.journey}:${project}`);
      }
      if (metric.success_artifacts?.length !== expected.steps.length) {
        throw new Error(`Observed metric has incomplete success artifacts: ${expected.journey}:${project}`);
      }
      for (const file of metric.success_artifacts) {
        if (!manifest.some((item) => item.file === file)) {
          throw new Error(`Observed metric references an unknown success artifact: ${file}`);
        }
      }
    }
  }

  const narrowArtifacts = manifest.filter(
    (item) => item.journey === "complex_content_narrow" && item.project === "narrow-chromium",
  );
  for (const item of narrowArtifacts) {
    if (item.viewport?.width !== 360 || item.viewport?.height !== 520) {
      throw new Error(`Narrow evidence has the wrong viewport: ${item.file}`);
    }
    if (
      item.conversation_scroll_height === undefined
      || item.conversation_client_height === undefined
      || item.conversation_scroll_top === undefined
      || item.conversation_distance_from_bottom === undefined
    ) {
      throw new Error(`Narrow evidence lacks conversation scroll metadata: ${item.file}`);
    }
    if (item.conversation_scroll_height <= item.conversation_client_height) {
      throw new Error(`Narrow evidence did not produce a scrollable conversation: ${item.file}`);
    }
  }

  const userScrolled = narrowArtifacts.find((item) => item.step === "user-scrolled");
  if (!userScrolled || (userScrolled.conversation_distance_from_bottom ?? 0) < 100) {
    throw new Error("Narrow user-scroll evidence did not move meaningfully away from the latest message");
  }
  for (const step of ["back-to-latest", "restored"]) {
    const item = narrowArtifacts.find((artifact) => artifact.step === step);
    if (!item || (item.conversation_distance_from_bottom ?? Number.POSITIVE_INFINITY) >= 80) {
      throw new Error(`Narrow evidence is not at the latest message after ${step}`);
    }
  }

  const narrowMetric = metrics.find(
    (item) => item.journey === "complex_content_narrow" && item.project === "narrow-chromium",
  );
  if (!narrowMetric?.action_summary || narrowMetric.action_summary.scrolls < 1) {
    throw new Error("Narrow observed metric does not contain a real user scroll action");
  }
  if (!narrowMetric.no_horizontal_overflow) {
    throw new Error("Narrow complex-content journey has horizontal page overflow");
  }
}

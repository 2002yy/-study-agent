import { readdirSync, readFileSync, statSync } from "node:fs";
import { relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const srcRoot = fileURLToPath(new URL("../", import.meta.url));
const querySignals = [
  /input\.trim\(\)/,
  /lastChat\?\.rag\?\.query/,
  /ragController\.search\(/,
  /LocalKnowledgeInvocation/,
  /invocation:\s*currentToolInvocation/,
];

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = resolve(dir, name);
    if (statSync(path).isDirectory()) return walk(path);
    if (!/\.(ts|tsx)$/.test(name) || /\.(test|spec)\.(ts|tsx)$/.test(name)) return [];
    return [path];
  });
}

describe("active query production inventory", () => {
  it("prints every production query derivation before the selector boundary is finalized", () => {
    const matches = walk(srcRoot).flatMap((path) => {
      const lines = readFileSync(path, "utf8").split("\n");
      return lines.flatMap((line, index) =>
        querySignals.some((signal) => signal.test(line))
          ? [`${relative(srcRoot, path)}:${index + 1}: ${line.trim()}`]
          : [],
      );
    });

    expect(matches, `ACTIVE_QUERY_INVENTORY\n${matches.join("\n")}`).toEqual([]);
  });
});

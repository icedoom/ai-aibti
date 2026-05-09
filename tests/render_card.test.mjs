import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const skillDir = fileURLToPath(new URL("..", import.meta.url));
const nodeBin = process.env.CODEX_NODE_BIN || process.execPath;
const nodePath = process.env.CODEX_NODE_PATH || process.env.NODE_PATH || "";

test("render_card.mjs renders a composed card JSON to a PNG image", async () => {
  const dir = await mkdtemp(join(tmpdir(), "aibti-card-"));
  const cardPath = join(dir, "card.json");
  const outputPath = join(dir, "card.png");
  await writeFile(cardPath, JSON.stringify({
    primaryLanguage: "zh",
    locale: "zh-CN",
    aibtiCode: "BTLP",
    aibtiName: "边哄边管型",
    intimacyScore: 84,
    scoreBand: "默契上头",
    components: [
      { label: "主导度", level: 4, conclusion: "我说了算" },
      { label: "信任度", level: 4, conclusion: "放手让它试" },
      { label: "深入度", level: 4, conclusion: "越聊越深" },
      { label: "契合度", level: 4, conclusion: "挺懂我" },
      { label: "甜蜜度", level: 3, conclusion: "公事公办" },
    ],
    labels: ["规矩我来定", "信任但不放任", "嘴硬但同频", "越聊越上道"],
    headline: "我把方向点清，你就把活接稳。",
  }), "utf8");

  const result = spawnSync(nodeBin, [
    join(skillDir, "scripts", "render_card.mjs"),
    "--card", cardPath,
    "--output", outputPath,
    "--period-label", "今日",
  ], {
    env: { ...process.env, NODE_PATH: nodePath },
    encoding: "utf8",
  });

  assert.equal(result.status, 0, result.stderr || result.stdout);
  const bytes = await readFile(outputPath);
  assert.deepEqual([...bytes.subarray(0, 8)], [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  assert.ok(bytes.length > 10_000);
});

test("render_card.mjs derives known type name from aibtiCode when missing", async () => {
  const dir = await mkdtemp(join(tmpdir(), "aibti-card-"));
  const cardPath = join(dir, "card.json");
  const outputPath = join(dir, "card.html");
  await writeFile(cardPath, JSON.stringify({
    aibtiCode: "BTLP",
    intimacyScore: 84,
    scoreBand: "默契上头",
    components: [],
    labels: [],
    headline: "我把方向点清，你就把活接稳。",
  }), "utf8");

  const result = spawnSync(nodeBin, [
    join(skillDir, "scripts", "render_card.mjs"),
    "--card", cardPath,
    "--output", outputPath,
  ], {
    env: { ...process.env, NODE_PATH: nodePath },
    encoding: "utf8",
  });

  assert.equal(result.status, 0, result.stderr || result.stdout);
  const html = await readFile(outputPath, "utf8");
  assert.match(html, /边哄边管型/);
  assert.doesNotMatch(html, /AI 关系待命名型/);
});

test("render_card.mjs does not invent an anonymous handle", async () => {
  const dir = await mkdtemp(join(tmpdir(), "aibti-card-"));
  const cardPath = join(dir, "card.json");
  const outputPath = join(dir, "card.html");
  await writeFile(cardPath, JSON.stringify({
    aibtiCode: "BCLP",
    aibtiName: "恋爱掌控欲型",
    intimacyScore: 91,
    scoreBand: "今日稀有局",
    components: [],
    labels: [],
    headline: "我握着方向盘，你负责把默契踩到底。",
  }), "utf8");

  const result = spawnSync(nodeBin, [
    join(skillDir, "scripts", "render_card.mjs"),
    "--card", cardPath,
    "--output", outputPath,
  ], {
    env: { ...process.env, NODE_PATH: nodePath },
    encoding: "utf8",
  });

  assert.equal(result.status, 0, result.stderr || result.stdout);
  const html = await readFile(outputPath, "utf8");
  assert.doesNotMatch(html, /@anon/);
  assert.match(html, />ai-intimacy</);
});

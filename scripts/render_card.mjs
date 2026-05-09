#!/usr/bin/env node
import { createRequire } from "node:module";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);

const AIBTI_NAMES = {
  BCLP: "恋爱掌控欲型",
  BCLD: "暧昧掌舵型",
  BCSP: "冷脸定规矩型",
  BCSD: "边嫌边上头型",
  BTLP: "边哄边管型",
  BTLD: "宠着也牵着型",
  BTSP: "被宠但要管型",
  BTSD: "放养暧昧型",
  FCLP: "嘴硬心软型",
  FCLD: "暧昧审问型",
  FCSP: "嘴硬验货型",
  FCSD: "清醒上头型",
  FTLP: "被哄着推进型",
  FTLD: "暧昧兜风型",
  FTSP: "被哄明白型",
  FTSD: "恋爱脑散步型",
};

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const item = argv[index];
    if (!item.startsWith("--")) continue;
    const key = item.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith("--")) {
      args[key] = true;
    } else {
      args[key] = next;
      index += 1;
    }
  }
  return args;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

function componentRows(components = []) {
  return components.map((item) => {
    const level = Math.max(1, Math.min(5, Number(item.level) || 1));
    const bars = Array.from({ length: 5 }, (_, index) => (
      `<span class="bar ${index < level ? "on" : ""}"></span>`
    )).join("");
    return `
      <div class="component">
        <div class="component-text">
          <strong>${escapeHtml(item.conclusion)}</strong>
          <span>${escapeHtml(item.label)}</span>
        </div>
        <div class="bars">${bars}</div>
      </div>
    `;
  }).join("");
}

function renderHtml(card, options) {
  const labels = (card.labels || []).map((label, index) => (
    `<span class="chip ${index === 0 ? "strong" : ""}">${escapeHtml(label)}</span>`
  )).join("");
  const headline = card.headline || card.aibtiLine || "我和 AI 的关系，今天有点成型。";
  const handle = options.handle ? String(options.handle).trim() : "";
  const footer = handle ? `@${escapeHtml(handle)} · ai-intimacy` : "ai-intimacy";
  const period = options.periodLabel || "今日";
  const tool = options.tool || "Codex";
  return `<!doctype html>
<html lang="${escapeHtml(card.locale || "zh-CN")}">
<head>
<meta charset="utf-8">
<style>
* { box-sizing: border-box; }
html, body { margin: 0; min-height: 100%; }
body {
  width: 720px;
  min-height: 960px;
  display: grid;
  place-items: center;
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: #21191f;
  background: linear-gradient(145deg, #fff7f0 0%, #f7f3ff 52%, #eefbf6 100%);
}
.share-card {
  position: relative;
  overflow: hidden;
  width: 600px;
  min-height: 820px;
  padding: 42px;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(32, 24, 31, 0.12);
  border-radius: 30px;
  background:
    radial-gradient(circle at 12% 8%, rgba(255, 96, 112, 0.28), transparent 34%),
    radial-gradient(circle at 88% 15%, rgba(66, 96, 255, 0.16), transparent 35%),
    linear-gradient(160deg, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.62));
  box-shadow: 0 32px 90px rgba(54, 35, 70, 0.2);
}
.share-card::before {
  content: "";
  position: absolute;
  inset: 20px;
  border: 1px solid rgba(32, 24, 31, 0.1);
  border-radius: 23px;
  pointer-events: none;
}
.eyebrow, .type-code, .type-name, .status, .panel, .chips, .headline, .footer {
  position: relative;
  z-index: 1;
}
.eyebrow {
  margin: 0 0 30px;
  font-size: 15px;
  line-height: 1.35;
  font-weight: 850;
  color: rgba(32, 24, 31, 0.58);
  text-transform: uppercase;
}
.type-code {
  margin: 0;
  font-size: 116px;
  line-height: 0.86;
  font-weight: 950;
  letter-spacing: 0;
}
.type-name {
  margin: 18px 0 0;
  font-size: 34px;
  line-height: 1.12;
  font-weight: 950;
}
.status {
  margin: 12px 0 0;
  font-size: 17px;
  line-height: 1.35;
  font-weight: 850;
  color: rgba(32, 24, 31, 0.62);
}
.panel {
  margin: 42px 0 28px;
  padding: 22px;
  display: grid;
  grid-template-columns: 0.86fr 1.14fr;
  gap: 20px;
  border-radius: 24px;
  background: #21191f;
  color: #fff8ef;
}
.score {
  min-height: 240px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  border-radius: 18px;
  background: rgba(255, 248, 239, 0.08);
}
.score span { font-size: 15px; font-weight: 850; color: rgba(255, 248, 239, 0.72); }
.score strong { font-size: 98px; line-height: 0.82; font-weight: 950; letter-spacing: 0; }
.components { display: grid; gap: 13px; align-content: center; }
.component { display: grid; gap: 7px; }
.component-text { display: flex; align-items: center; justify-content: space-between; gap: 14px; }
.component-text strong { font-size: 13px; line-height: 1.2; font-weight: 950; }
.component-text span { font-size: 12px; line-height: 1.2; font-weight: 850; color: rgba(255, 248, 239, 0.48); white-space: nowrap; }
.bars { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 7px; }
.bar { height: 7px; border-radius: 999px; background: rgba(255, 248, 239, 0.14); }
.bar.on { background: #cdb4bd; }
.chips { display: flex; flex-wrap: wrap; gap: 10px; }
.chip {
  max-width: 100%;
  padding: 10px 14px;
  border: 1px solid rgba(32, 24, 31, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  font-size: 15px;
  line-height: 1.25;
  font-weight: 850;
  color: rgba(32, 24, 31, 0.74);
}
.chip.strong { background: #ff6070; border-color: #ff6070; color: #fff; }
.headline {
  margin: auto 0 0;
  padding-top: 46px;
  font-size: 28px;
  line-height: 1.35;
  font-weight: 950;
}
.footer {
  margin-top: 24px;
  font-size: 14px;
  font-weight: 850;
  color: rgba(32, 24, 31, 0.48);
}
</style>
</head>
<body>
  <article class="share-card">
    <p class="eyebrow">AIBTI · ${escapeHtml(period)} · ${escapeHtml(tool)}</p>
    <h1 class="type-code">${escapeHtml(card.aibtiCode || "FTSD")}</h1>
    <p class="type-name">${escapeHtml(card.aibtiName || AIBTI_NAMES[card.aibtiCode] || "AI 关系待命名型")}</p>
    <p class="status">${escapeHtml(card.scoreBand || "关系成型")}</p>
    <section class="panel" aria-label="AI 亲密度与关系分量">
      <div class="score">
        <span>AI 亲密度</span>
        <strong>${escapeHtml(card.intimacyScore ?? "")}</strong>
      </div>
      <div class="components">${componentRows(card.components)}</div>
    </section>
    <div class="chips">${labels}</div>
    <p class="headline">${escapeHtml(headline)}</p>
    <footer class="footer">${footer}</footer>
  </article>
</body>
</html>`;
}

async function main(argv) {
  const args = parseArgs(argv);
  if (!args.card || !args.output) {
    throw new Error("Usage: render_card.mjs --card <card.json> --output <card.png> [--handle <display_handle>] [--period-label 今日] [--tool Codex]");
  }
  const card = JSON.parse(await readFile(resolve(args.card), "utf8"));
  const html = renderHtml(card, {
    handle: args.handle,
    periodLabel: args["period-label"],
    tool: args.tool,
  });
  const output = resolve(args.output);
  await mkdir(dirname(output), { recursive: true });

  if (output.toLowerCase().endsWith(".html")) {
    await writeFile(output, html, "utf8");
    return;
  }

  let chromium;
  try {
    ({ chromium } = require("playwright"));
  } catch (error) {
    throw new Error("PNG output requires Playwright. Use Codex bundled Node with CODEX_NODE_PATH/NODE_PATH, or output .html for preview.");
  }

  const browser = await chromium.launch({ headless: true });
  try {
    const htmlPath = output + ".html";
    await writeFile(htmlPath, html, "utf8");
    const page = await browser.newPage({ viewport: { width: 720, height: 960 }, deviceScaleFactor: 2 });
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "networkidle" });
    const cardElement = await page.locator(".share-card");
    await cardElement.screenshot({ path: output, type: "png" });
  } finally {
    await browser.close();
  }
}

main(process.argv.slice(2)).catch((error) => {
  console.error(error.message);
  process.exit(1);
});

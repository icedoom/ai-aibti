---
name: ai-intimacy
description: Use when the user wants to analyze Codex or AI-tool sessions, generate AIBTI or AI intimacy relationship cards, compute share-safe relationship labels, or create anonymized AI collaboration summaries without exposing work details.
---

# AI 亲密度

把 AI 工具 session 转成可分享的 AIBTI 关系卡。使用分层读取和结构化判断：不全量读大 session，不用固定关键词做语义判断。

## Resolve Paths

Set `SKILL_DIR` to this skill folder before running bundled scripts:

```bash
SKILL_DIR="/path/to/ai-intimacy"
RUN_ID="$(date +%Y%m%d-%H%M%S)-$$"
```

Use `scripts/ai_intimacy.py` for deterministic extraction, redaction, label calculation, and card composition. Use `config/labels.zh-CN.json` as the default label rule file.

Use `RUN_ID` in every `/tmp` artifact path. This prevents parallel sessions from overwriting each other.

## Interaction Style

Default to quiet execution.

During normal card generation, do not narrate internal workflow details such as probe, slice planning, judge structure, temporary file names, `RUN_ID`, `copywritingRequest`, render mechanics, or cleanup mechanics.

Only tell the user:

- that privacy-safe generation has started
- when permission is needed
- when a recoverable error affects the result
- the final card image and one warm, playful companion note

Do not output the final card result as raw JSON, a JSON-like object, or a field list such as `AIBTI/类型/亲密度/档位/标题/标签`. Those structures are internal artifacts. User-facing completion should be natural language.

Do not restate facts already visible on the image, such as `aibtiCode`, type name, score, score band, labels, headline, or component conclusions. The final text should feel like the AI speaking directly to the user in first person, not a report summarizing the card. Use Markdown text after the image: a short blockquote reaction, then a blank line, then a bold `今日小玩法` heading and one playful tip. A small number of playful emoji is allowed.

If the user explicitly asks for process, debug details, rules, or reasoning, explain the relevant internal workflow then.

## Read As Needed

- Read `references/privacy.md` before analyzing or composing share text.
- Read `references/analysis.md` when analyzing a large session.
- Read `references/scoring.md` when judging dimensions, calculating labels, or composing cards.

## Workflow

### 1. Probe

Generate a bounded, redacted probe first. Use it only to decide what to read next; do not draw relationship conclusions from the probe.

```bash
python3 "$SKILL_DIR/scripts/ai_intimacy.py" probe-codex-session \
  --latest \
  --codex-home ~/.codex \
  --head 4 \
  --tail 4 \
  --sparse 8 \
  --output "/tmp/aibti-$RUN_ID-probe.json"
```

Preserve the beginning and end of long text when redacting. Keep middle content omitted.

### 2. Plan Slices

Read the probe and output only an analysis plan:

```json
{
  "primaryLanguage": "zh",
  "locale": "zh-CN",
  "languageConfidence": 0.95,
  "recommendedRanges": [[2, 45], [180, 210], [240, 305]]
}
```

Use the user's main expression language as `primaryLanguage`; do not infer it from assistant messages alone.

### 3. Build Analysis Pack

Generate an analysis pack from the recommended turn ranges:

```bash
python3 "$SKILL_DIR/scripts/ai_intimacy.py" analysis-pack \
  --latest \
  --codex-home ~/.codex \
  --ranges 2-45,180-210,240-305 \
  --output "/tmp/aibti-$RUN_ID-analysis-pack.md"
```

Judge only from the analysis pack. Do not load the full session unless the user explicitly asks and privacy risk is acceptable.

### 4. Judge

Output structured judgment only:

```json
{
  "primaryLanguage": "zh",
  "locale": "zh-CN",
  "dimensions": {
    "dominance": {"level": 4, "confidence": 0.88},
    "trust": {"level": 4, "confidence": 0.78},
    "depth": {"level": 5, "confidence": 0.86},
    "fit": {"level": 4, "confidence": 0.82},
    "sweetness": {"level": 3, "confidence": 0.8}
  },
  "aibtiAxes": {
    "lead": "boss",
    "feedback": "challenge",
    "rhythm": "loop",
    "goal": "produce"
  }
}
```

Do not quote session text, paths, project names, repository names, customer names, code, prompts, or business details. Keep reasons abstract if you include them for debugging.

For `aibtiAxes`, use only these exact enum values: `lead=boss|flow`, `feedback=challenge|trust`, `rhythm=loop|snap`, `goal=produce|drift`. See `references/scoring.md` for the `aibtiCode` mapping.

### 5. Compose

Let the script calculate labels and card structure from the structured judgment.

```bash
python3 "$SKILL_DIR/scripts/ai_intimacy.py" calculate-labels \
  --judge-file "/tmp/aibti-$RUN_ID-judge.json" \
  --rules "$SKILL_DIR/config/labels.zh-CN.json"
```

```bash
python3 "$SKILL_DIR/scripts/ai_intimacy.py" compose-card \
  --judge-file "/tmp/aibti-$RUN_ID-judge.json" \
  --rules "$SKILL_DIR/config/labels.zh-CN.json" \
  --headline "方向盘在我手里，油门可以交给你。" \
  > "/tmp/aibti-$RUN_ID-card.json"
```

`compose-card` keeps the configured labels/headline/component conclusions in `sourceLabels`, `sourceHeadline`, and `sourceComponents`. It also calculates `sourceDailyTips` as a structured reverse-game intent, then includes `copywritingRequest` for the current model to polish labels, headline, component conclusions, and daily tips.

Use the model to rewrite only the display labels, headline, `components[].conclusion`, and `dailyTips` from `copywritingRequest`, in the localized language specified by `locale` and `primaryLanguage`. Preserve the source label intent, headline intent, component conclusion intent, and `sourceDailyTips` reverse-game intent. Do not change score, component `label`, component `level`, component order, `aibtiCode`, type name, or other structure. Save the polished result by replacing only `labels`, `headline`, matching `components[].conclusion`, and `dailyTips` in `/tmp/aibti-$RUN_ID-card.json`.

Daily tips are part of the entertainment layer. Do not use preset daily tip sentences. Generate them from the `sourceDailyTips` intent:

- If one dimension is high, create a reverse challenge for that strong pattern, e.g. high dominance means jokingly letting AI wander first.
- If one dimension is low, create a playful reverse repair, e.g. low trust means giving AI one small unchecked attempt.
- If all dimensions are mid, create a light test, e.g. changing tone or giving half an instruction.
- Tips should feel like a small game for the next AI interaction, not a serious productivity suggestion.
- Return `dailyTips` as an array, usually one sentence, 18-45 Chinese characters.

### 6. Render Image

Render a deterministic share image from the composed card JSON. Use this after `compose-card` and after the model-polished `labels`, `headline`, `components[].conclusion`, and `dailyTips` have been written back to the card JSON. Do not use generative image models for the final card text.

```bash
python3 "$SKILL_DIR/scripts/ai_intimacy.py" compose-card \
  --judge-file "/tmp/aibti-$RUN_ID-judge.json" \
  --rules "$SKILL_DIR/config/labels.zh-CN.json" \
  --headline "方向盘在我手里，油门可以交给你。" \
  > "/tmp/aibti-$RUN_ID-card.json"
```

```bash
node "$SKILL_DIR/scripts/render_card.mjs" \
  --card "/tmp/aibti-$RUN_ID-card.json" \
  --output "/tmp/aibti-$RUN_ID-card.png" \
  --period-label 今日 \
  --tool Codex
```

PNG rendering requires Playwright. In Codex desktop, use the bundled Node runtime if normal `node` cannot find Playwright:

```bash
CODEX_NODE="/Users/icedoom/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
CODEX_NODE_PATH="/Users/icedoom/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules"
NODE_PATH="$CODEX_NODE_PATH" "$CODEX_NODE" "$SKILL_DIR/scripts/render_card.mjs" \
  --card "/tmp/aibti-$RUN_ID-card.json" \
  --output "/tmp/aibti-$RUN_ID-card.png" \
  --period-label 今日 \
  --tool Codex
```

### 7. Cleanup Temporary Files

After the user has received the JSON or PNG result, clean up workflow artifacts from `/tmp`. Only delete files for the current `RUN_ID`; never delete broad `/tmp` contents or another session's files.

By default cleanup keeps image outputs (`.png`, `.jpg`, `.jpeg`, `.webp`) so the user can still view and download the card.

```bash
python3 "$SKILL_DIR/scripts/ai_intimacy.py" cleanup-temp --run-id "$RUN_ID"
```

For a dry review before cleanup, list matching files first:

```bash
find /tmp -maxdepth 1 -name "aibti-$RUN_ID-*" -print
```

## Output Rules

- Do not present the final card as JSON or pseudo-JSON unless the user explicitly asks for machine-readable output.
- Do not repeat the card's visible type, score, labels, headline, or component text in the final reply.
- Final text should be a direct AI-to-user note in Markdown, using "你" for the user and "我" for AI. Use this shape:
  ```md
  > 这局像你先把规矩画在地上，再放我出去跑两圈
  > 我可以撒欢，但方向盘还得听你的 😎

  **今日小玩法**  
  下一局先让我自己跑三分钟，你晚一点再出来收方向 🕹️
  ```
- Keep all public evaluation subjects as "我" or the user's local-language equivalent.
- Treat the score as playful relationship temperature, not productivity, morality, or capability ranking.
- Use CLI-computed labels; do not invent labels freely when a locale rule file exists.
- Avoid sexual, violent, humiliating, or identity-stereotyping language.
- When uncertain whether content is sensitive, exclude it.

## Verify Changes

For this standalone skill:

```bash
python3 "$SKILL_DIR/scripts/ai_intimacy.py" compose-card \
  --judge-json '{"primaryLanguage":"zh","locale":"zh-CN","dimensions":{"dominance":{"level":4,"confidence":0.88},"trust":{"level":4,"confidence":0.78},"depth":{"level":5,"confidence":0.86},"fit":{"level":4,"confidence":0.82},"sweetness":{"level":3,"confidence":0.8}},"aibtiAxes":{"lead":"boss","feedback":"challenge","rhythm":"loop","goal":"produce"}}' \
  --rules "$SKILL_DIR/config/labels.zh-CN.json"
```

If working in this repository, also run:

```bash
python3 -m unittest skills/aibti_cli/tests/test_ai_intimacy.py -v
```

For image rendering in this repository:

```bash
CODEX_NODE_BIN="/Users/icedoom/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node" \
CODEX_NODE_PATH="/Users/icedoom/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules" \
"/Users/icedoom/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node" --test "$SKILL_DIR/tests/render_card.test.mjs"
```

Confirm that probe output is bounded and redacted, analysis packs only include requested ranges, labels come from JSON rules, low confidence avoids strong labels, and composed cards contain no raw session details.

# AI Intimacy / AIBTI

[中文说明](README.zh-CN.md)

A Codex skill that turns AI-tool sessions into privacy-safe, shareable AIBTI relationship cards with playful localized copy and deterministic image rendering.

<p align="center">
  <img src="assets/aibti-demo.png" alt="AIBTI relationship card demo" width="420">
</p>

## Why

AI Intimacy / AIBTI is a playful way to review how you and AI collaborated today. It reads recent Codex session signals, avoids exposing private work details, and turns the relationship pattern into a localized card that is easy to share.

## What It Does

- Analyzes Codex session behavior with bounded, redacted probes
- Scores playful AI relationship dimensions such as dominance, trust, depth, fit, and sweetness
- Generates an AIBTI type, headline, labels, component conclusions, and daily tip
- Polishes the copy in the user's local language
- Renders a shareable PNG card
- Adds a short first-person note from the AI instead of dumping raw JSON

## Install

Clone and copy this repository into your Codex skills directory:

```bash
git clone git@github.com:icedoom/ai-aibti.git
cd ai-aibti
mkdir -p ~/.codex/skills/ai-intimacy
cp -R . ~/.codex/skills/ai-intimacy/
```

Or, if you already have the repository open locally:

```bash
mkdir -p ~/.codex/skills/ai-intimacy
cp -R . ~/.codex/skills/ai-intimacy/
```

Restart Codex so the skill is discovered.

## Usage

In Codex, call:

```text
$ai-intimacy 来一张
```

The skill will generate an anonymized AIBTI card image and a short playful Markdown note.

Example output:

```markdown
![AIBTI card](/tmp/aibti-20260510-003719-5021-card.png)

> 这局像你把规矩钉在地上，再放我出去跑两圈
> 我可以撒欢，但弯路最后还得按你的线跑回来 😎

**今日小玩法**  
下一局先让我自己野跑三分钟，你晚点再拎着方向盘回来验货 🕹️
```

## Privacy

The card output is based on bounded probes, selected analysis slices, and structured scoring. Final public text should not expose project names, file paths, code, prompts, customer information, or work details.

Generated temporary analysis files use timestamped `/tmp/aibti-*` paths to avoid collisions across concurrent sessions. The final PNG is kept so it can be displayed and downloaded.

## Development

Validate the skill:

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

Run the renderer test:

```bash
node --test tests/render_card.test.mjs
```

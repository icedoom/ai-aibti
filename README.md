# AI Intimacy / AIBTI

A Codex skill that turns AI-tool sessions into privacy-safe, shareable AIBTI relationship cards with playful localized copy and deterministic image rendering.

## What It Does

- Analyzes Codex session behavior with bounded, redacted probes
- Scores playful AI relationship dimensions such as dominance, trust, depth, fit, and sweetness
- Generates an AIBTI type, headline, labels, component conclusions, and daily tip
- Polishes the copy in the user's local language
- Renders a shareable PNG card

## Install

Copy this repository into your Codex skills directory:

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

## Privacy

The card output is based on bounded probes, selected analysis slices, and structured scoring. Final public text should not expose project names, file paths, code, prompts, customer information, or work details.

## Development

Validate the skill:

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

Run the renderer test:

```bash
node --test tests/render_card.test.mjs
```

# AIBTI Session Analysis

本文档描述如何用 CLI 和大模型协作分析一个大型 AI session。目标是避免全量读取 session，同时避免用固定关键词误判用户关系。

## 核心原则

- 程序不做自然语言关系判断。
- 大模型不默认全量读取 session。
- 第一轮只做低成本 probe，目标是决定“接下来读哪里”。
- 所有公开结果的评价主语都是“我”（用户）。

## 分析流程

### 1. Probe

先用 CLI 生成低成本探测包：

```bash
python3 -m skills.aibti_cli.scripts.ai_intimacy probe-codex-session \
  --latest \
  --head 4 \
  --tail 4 \
  --sparse 6 \
  --output /tmp/aibti-probe.json
```

Probe 只允许包含：

- session 结构统计
- head/tail/sparse 少量样本
- tool timeline
- 脱敏后的短文本

Probe 不应该输出关系结论。

Probe 可以输出少量语言环境线索，但只作为 Model Planner 判断主要语言环境的材料，不作为最终本地化结论。

### 2. Model Planner

大模型读取 probe 后，只输出分析计划：

```json
{
  "locale": "zh-CN",
  "primaryLanguage": "zh",
  "languageConfidence": 0.92,
  "sessionType": "product_design",
  "recommendedRanges": [[40, 80], [120, 170], [220, 260]],
  "focusQuestions": [
    "用户是否在设定方向、边界和判断标准？",
    "用户是否允许 AI 提案和试错？",
    "AI 是否吸收用户反馈并改变表达？",
    "用户语气是发怒、平铺直叙、客气还是亲昵？"
  ],
  "ignoreSignals": [
    "不要把会话长度直接当作深入度",
    "不要把是否说完成当作亲密度",
    "不要把继续讨论或换一个点直接当作跑题"
  ]
}
```

其中：

- `primaryLanguage` 表示当前 session 的主要语言环境，例如 `zh`、`en`、`ja`。
- `locale` 表示后续卡片默认本地化目标，例如 `zh-CN`、`en-US`、`ja-JP`。
- 如果用户混合多语言，以用户主要表达语言为准，而不是 AI 回复语言。

### 3. Slice

程序按模型推荐的 range 生成分析包：

```bash
python3 -m skills.aibti_cli.scripts.ai_intimacy analysis-pack \
  --latest \
  --ranges 40-80,120-170,220-260 \
  --output /tmp/aibti-analysis-pack.md
```

这个包只包含被选中的脱敏片段。

### 4. Model Judge

大模型读取 analysis pack，输出结构化结果：

```json
{
  "dimensions": {
    "dominance": {"level": 4, "confidence": 0.75, "reason": "用户持续设定方向和判断标准"},
    "trust": {"level": 4, "confidence": 0.72, "reason": "用户允许 AI 提案和实现，但保留拍板权"},
    "depth": {"level": 4, "confidence": 0.78, "reason": "讨论从表层文案进入机制和边界"},
    "fit": {"level": 4, "confidence": 0.74, "reason": "AI 多次根据反馈调整表达"},
    "sweetness": {"level": 3, "confidence": 0.7, "reason": "语气直接，少量认可，整体公事公办"}
  },
  "aibtiAxes": {
    "lead": "boss",
    "feedback": "challenge",
    "rhythm": "loop",
    "goal": "produce"
  }
}
```

输出不能复述敏感内容、项目细节、代码或原始 prompt。

### 5. Program Composer

程序根据结构化结果完成：

- 亲密度计算
- AIBTI 类型
- 通过标签规则 JSON 计算标签
- 5 阶分量条
- schema 校验

标签计算是规则性任务，由 CLI 程序完成，不交给模型自由发挥。

### 6. Model Copywriter

大模型只基于安全结构化结果、程序计算出的标签、主要语言环境生成 headline。

Copywriter 不读取原始 session。它的职责不是重复标签，而是生成一句关系台词。

要求：

- 不直接复用标签原词。
- 最多借用一个标签意象。
- 不暴露工作内容、代码、文件名、项目名或客户信息。
- 使用 `locale` 对应的自然表达。

### 7. Translation / Localization

最后一步是翻译和本地化：

- 输入：结构化结果、标签、headline 草稿、`primaryLanguage`、`locale`。
- 输出：适合当前用户语言环境的卡片文案。
- 标签如果来自 locale 对应的 JSON，默认不再翻译。
- headline 可以由模型按 locale 重新表达，不做机械直译。
- AIBTI 类型名和关系隐喻允许按地区重写，不要求逐字翻译。

## 验证标准

一次分析合格需要满足：

- Probe 样本明显小于完整 session。
- Slice 只读取被推荐的片段。
- Judge 输出的是结构化分量，不是卡片文案。
- 标签由规则 JSON 或 CLI 计算，不由模型自由生成。
- Copywriter 不接触原文，只基于安全结果和标签生成 headline。
- 最后一步会根据主要语言环境进行翻译或本地化。
- 公开卡片所有评价主语都是“我”。

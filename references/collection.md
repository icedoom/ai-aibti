# 特征采集

本地分析只整理抽象特征，不保留原始工作内容。

基础特征包括：

- `goalType`
- `leadBalance`
- `feedbackStyle`
- `ruleSetting`
- `focusLevel`
- `closureState`
- `validationBehavior`
- `toolContext`
- `bossMoves`
- `obedienceMoves`
- `ruleSettingMoves`
- `repairLoops`
- `driftMoves`
- `closureMoves`
- `aiInitiative`
- `aiDrift`
- `aiCompliance`
- `aiRework`
- `aiValidation`
- `aiClosure`

采集规则用于把会话行为压缩成可判断的抽象信号。

## 字段说明

用户行为字段：

- `bossMoves`：用户改方向、设边界、拒绝跑偏、要求重做的强主导行为。
- `obedienceMoves`：用户接受 AI 建议并继续推进的行为。
- `ruleSettingMoves`：用户给 AI 设流程、格式、标准、边界或验证要求的行为。
- `repairLoops`：返工、纠错、重试、解释后再改的循环。
- `driftMoves`：明显换话题、发散探索、东拉西扯。
- `closureMoves`：推动收口、验收、确认完成。

AI 行为字段：

- `aiInitiative`：AI 主动提出方案、拆任务、推进下一步。
- `aiDrift`：AI 跑偏、脑补、过度发挥。
- `aiCompliance`：AI 按用户规则、格式、边界调整。
- `aiRework`：AI 被要求重做、修正、解释。
- `aiValidation`：AI 主动测试、验证、说明限制或风险。
- `aiClosure`：AI 帮助形成可交付结果或明确结论。

区间取值：

- `none`：没有明显出现
- `low`：少量出现
- `medium`：多次出现
- `high`：高频或主导性出现

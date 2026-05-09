# AI Intimacy / AIBTI

[English](README.md)

一个 Codex skill，把你和 AI 的协作 session 生成一张隐私安全、可分享、带点恋爱脑味道的 AIBTI 关系卡。

<p align="center">
  <img src="assets/aibti-demo.png" alt="AIBTI 关系卡示例" width="420">
</p>

## 它是什么

AI Intimacy / AIBTI 是一个偏娱乐向的 Codex skill。它会观察你最近一次 Codex session 里的协作方式，分析你和 AI 的关系模式，然后生成一张 AIBTI 卡片。

它不是工作报告，也不会把你的项目细节、代码、路径、客户信息或原始 prompt 暴露到最终图片里。最终输出更像是 AI 对你说的一句玩笑话，再加一个今天可以试试的小玩法。

## 它会做什么

- 用有限、脱敏的方式读取 Codex session 信号
- 计算主导度、信任度、深入度、契合度、甜蜜度等趣味维度
- 生成 AIBTI 类型、标题、标签、分量结论和今日小玩法
- 根据你的本地语言润色文案
- 渲染一张可以分享的 PNG 图片
- 最终只输出图片和一段轻松的 Markdown 文本，不输出原始 JSON

## 安装

克隆这个仓库，并复制到 Codex skills 目录：

```bash
git clone git@github.com:icedoom/ai-aibti.git
cd ai-aibti
mkdir -p ~/.codex/skills/ai-intimacy
cp -R . ~/.codex/skills/ai-intimacy/
```

如果你已经在本地打开了这个仓库：

```bash
mkdir -p ~/.codex/skills/ai-intimacy
cp -R . ~/.codex/skills/ai-intimacy/
```

然后重启 Codex，让它重新发现 skill。

## 使用

在 Codex 里输入：

```text
$ai-intimacy 来一张
```

它会生成一张匿名化的 AIBTI 关系卡，并附上一段 AI 第一人称的轻松小结。

示例输出：

```markdown
![AIBTI card](/tmp/aibti-20260510-003719-5021-card.png)

> 这局像你把规矩钉在地上，再放我出去跑两圈
> 我可以撒欢，但弯路最后还得按你的线跑回来 😎

**今日小玩法**  
下一局先让我自己野跑三分钟，你晚点再拎着方向盘回来验货 🕹️
```

## 隐私边界

这个 skill 的目标是生成“可分享”的关系卡，而不是复述你的工作内容。

最终图片和文字不应该包含：

- 项目名、仓库名、文件路径
- 代码、配置、密钥、日志
- 客户、公司、业务数据
- 原始 prompt 或 session 细节

临时分析文件会使用带时间戳的 `/tmp/aibti-*` 路径，避免多个 session 同时执行时互相覆盖。最终 PNG 图片会保留，方便在 Codex 里展示和下载。

## 开发

校验 skill：

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

运行渲染测试：

```bash
node --test tests/render_card.test.mjs
```

## License

MIT

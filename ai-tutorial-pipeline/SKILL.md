---
name: ai-tutorial-pipeline
description: 用网页版 AI（默认千问 chat.qwen.ai，跑在用户本机 Edge 的已登录会话里，经 WebBridge 接管）按大纲逐章生成高质量教程，并逐章自动保存到思源笔记指定文档下，入库前后自动做表格/公式格式校验。当用户提到"生成教程、用网页AI/千问/Qwen生成教程、教程存到思源、逐章生成、XX速成教程"等场景时使用；DeepSeek/豆包等站点改 plan 配置即可复用。自动处理 WebBridge 接管、CDP 真实点击、复制内容截获、表格行拼接、公式兼容等全部细节。
---

# ai-tutorial-pipeline：网页 AI 逐章生成教程 → 自动存思源

让网页版 AI 按用户的大纲逐章生成教程，每章生成完立即截获内容存进思源，边生成边保存、全程无需人工盯守。**默认接管用户本机 Edge（WebBridge，复用登录态），不用需要重新登录的隔离浏览器。**全部技术细节已固化在 scripts/ 里，不要现场重写脚本、不要用系统剪贴板、不要在 shell 里内联中文 JSON。

## 前置条件

- WebBridge（`~/.kimi-webbridge/`）+ Edge 扩展：脚本会自动启动守护进程；扩展连接不上时提示用户打开 Edge 检查扩展。
- 用户 Edge 已登录目标 AI 站点（默认千问）。
- 思源在运行（脚本从 conf.json 现读端口，不写死）。

## 工作流

### 第 0 步：确认输入（缺什么问什么，一次问全）

1. **大纲**：用户消息里通常已给。章节划分 = 大纲的层级（如"第一层~第五层 + 资源清单"各算一章）。
2. **思源父文档**：用户可能直接给 ID（也可能放在剪贴板里说"这个id"）。有 ID 用 ID；没有就跑 `check_env.py` 拿最近文档列表让用户选，或按用户习惯新建（如 `/硬件/<教程名>`）。
3. 教程风格提示词：沿用用户第一次的措辞（见下方模板）。

### 第 1 步：环境自检

```bash
python ~/.zcode/skills/ai-tutorial-pipeline/scripts/check_env.py --parent "<父文档ID或标题>"
```

输出 JSON：`bridge`（WebBridge 状态）、`kernel`（思源端口）、`parent`（解析出的父文档 id/notebook/hpath）。bridge 不 ok → 让用户打开 Edge 看扩展；思源没起 → 告诉用户，不要代启。

### 第 2 步：写 plan.json + prompts/

在工作目录建 `plan.json`（参照 `scripts/plan.example.json`），每章一个提示词文件 `prompts/chN.txt`。

提示词模板（第 1 章沿用用户的原始措辞；后续章保持一致的开头）：

```
第1章:  Qwen3.8-Max按照我给的大纲给我生成一个速成教程。质量第一，不限字数。细节由你定，我给的是参考的大纲。你可以优化内容。
        <大纲标题>
        <本章大纲条目，一行一条>
后续章: Qwen3.8-Max按照我给的大纲继续生成下一章。质量第一，不限字数。细节由你定，我给的是参考的大纲。你可以优化内容。
        <大纲标题>
        <本章大纲条目>
收尾章: ……生成最后一章：<章节名>。……最后给整个教程做一个全篇总结收尾。
```

关键 plan 字段：`session`（本次任务唯一名）、`parent_id`、`chat_url`、`composer_css`（输入框选择器，千问是 `textarea[placeholder="Ask Qwen"]`）、`poll_interval`（默认 20s）、`max_wait_min`（默认 25）、`chapters[].{key, prompt_file, fallback_title}`。换其他 AI 站点时只改 `chat_url`、`composer_css` 和复制按钮 CSS。

### 第 3 步：后台运行流水线

```bash
python ~/.zcode/skills/ai-tutorial-pipeline/scripts/generate.py --plan plan.json
```

**必须用 Bash 的 run_in_background 跑**，然后定期查看输出文件。流水线自动完成每章循环：等空闲 → 发提示词 → 轮询等生成完 → 截获内容 → **立刻发下一章提示词** → 回头存思源（入库前后自动做格式校验：表格行拼接、列数一致、伪表格检测、公式禁词；校验失败自动删掉坏文档并报错）。断点续传：中断后重跑同一 plan，已发送/已截获/已保存的章节自动跳过，绝不重复发送。

### 第 4 步：汇报

用 summary.json / 日志生成表格：每章标题、思源文档 ID、块数与表格数，附 `siyuan://blocks/<id>` 深链。告知用户标签组名（`group_title`），问一声是否要关。

## 速度须知（用户在意）

- 耗时大头是 **AI 站点自己的深度思考**（Qwen3.8-Max 每章 3~10 分钟，无法压缩）。
- 编排开销已被压到接近零：脚本全自动 + 章节重叠 + 20s 轮询。不要手动频繁插手。
- 若用户仍嫌慢：可以提出"多开 2~3 个对话标签并行生成不同章"（需复制 plan 按 session 拆分，属于未内置的进阶玩法，先征得同意再搞）。

## 故障救援

- 章节生成完了但流水线挂了：`python ~/.zcode/skills/ai-tutorial-pipeline/scripts/wb.py copy-latest <out.md> --session <plan.session>` 手动截获 → `python ~/.zcode/skills/ai-tutorial-pipeline/scripts/siyuan.py save <out.md> --parent-id <ID> --fallback <标题>` 手动入库（同样带格式校验）。
- 只想看页面状态：`python .../wb.py snapshot --session <plan.session>`。
- 重跑前先看 `progress.json` 确定断在哪一步（sent/baseline/copies0/captured/doc_id 标记）。

## 出问题先读

任何一步报错，先读 `references/gotchas.md` 对号入座——里面的坑全是实测踩出来的，脚本里已内置对策，不要重新发明。

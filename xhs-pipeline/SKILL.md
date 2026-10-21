---
name: xhs-pipeline
description: 小红书信息收集通用流水线（profile 驱动）：真实点击抓取→暂存→模型审内容/读图→按分类合并进思源汇总文档（题库可折叠题卡/岗位单页/其他自定义）。当用户要在小红书收集任何信息（面经、经验贴、岗位、资料、话题、竞品笔记等）并整理进思源或其他目标时使用。当前内置 job（找工作题库：ai infra / 数字ic设计 / 求职目标岗位）profile，新增收集场景只需加 profile 配置。
---

# xhs-pipeline：小红书信息收集通用流水线

profile 驱动的小红书收集引擎：`search` / `fetch-url` / `fetch-profile`（真实点击、单篇直收或博主主页整收→暂存）→ `review` + 模型审内容/读图 → `merge-q` / `merge-jobs` 等合并命令 → `clean-staging` 清临时文件。**依赖 ai-tutorial-pipeline 的 wb.py / siyuan.py（sys.path 引用）。**

## 命令（--profile 默认 profiles/job.json）

```bash
python scripts/pipeline.py check
python scripts/pipeline.py search "<关键词>" --category "<分类名>" --limit 3   # 后台跑（run_in_background），异常退出码=1；同一笔记跨关键词自动去重（_seen.json）
python scripts/pipeline.py search-tokens "<关键词>" --category "<分类名>" --limit 3  # 弹窗限流时的替代路径：从卡片 DOM 抽 xsec_token → 逐篇 explore 整页直开（见 gotchas X34）
python scripts/pipeline.py fetch-url "<笔记分享链接>" --category "<分类名>" [--keyword "<搜索兜底词>"]  # 用户直接丢单篇链接时用：优先借用已打开的标签页（零导航零风控）→ 直连分享链 → 风控时按 keyword 搜索兜底
python scripts/pipeline.py fetch-profile "<博主主页链接带xsec_token>" --category "<分类名>" [--limit 0]  # 博主主页整收：network 捕获 SSR 文档体抽 (noteId, xsec_token)，逐篇 explore 整页导航抓取（主页卡片点击开弹窗无效，见 gotchas X33）
python scripts/pipeline.py review
python scripts/pipeline.py prep-images        # 暂存图片转压成 ≤1400px JPG（conv/），大图 Read 前必跑；顺带报缺失图片
python scripts/pipeline.py merge-q --category "<分类名>" --file q.json       # 按累计 JSON 全量重建题目汇总
python scripts/pipeline.py merge-jobs --category "<分类名>" --file jobs.json # 按累计 JSON 全量重建岗位汇总
python scripts/pipeline.py clean-staging
```

## Profile 配置（profiles/*.json）

```json
{
  "name": "job", "session": "xhs-job-notes", "group_title": "面经收集",
  "site": "https://www.xiaohongshu.com",
  "parent_path": "/找工作/找工作题库",
  "staging_dir": "D:/Project/Zcode/xhs-data/job/staging",
  "categories": [
    {"name": "ai infra", "subpage_id": "…", "keywords": ["…"], "question_bank": true},
    {"name": "数字ic设计", "subpage_id": "…", "keywords": ["…"], "question_bank": true,
     "exclude_title_keywords": ["验证", "UVM"], "note": "只收设计，验证暂不关注"},
    {"name": "求职目标岗位", "subpage_id": "…", "keywords": ["…"], "jobs": true}
  ]
}
```

**新增收集场景** = 在 profiles/ 加一个 json：定义 parent_path（思源目标）、categories（名字 + 关键词 + 汇总形态）。汇总形态两种现成实现：`question_bank: true` → 题目汇总（可折叠题卡，见下）；`jobs: true` → 岗位汇总单页。其他形态在 pipeline.py 加对应 merge 命令（仿 merge-jobs 的装载-去重-整删整建模式）。

## 工作流（汇总制：思源只维护汇总文档，不建每帖页）

1. `check`：WebBridge/登录态/分类子页。
2. **按来源选命令**：单篇分享链接 → `fetch-url`；博主主页整收 → `fetch-profile`（SSR 抽 token 逐篇整页直开，X33）；关键词搜索 → `search`，**弹窗限流（点卡片无内容）不用冷却等待，直接改 `search-tokens`**（卡片 DOM 抽 token 整页直开，X34）。搜索 **run_in_background 跑**：抓取到暂存区（JSON+图片，暂存即临时文件），异常中断也会打印已暂存清单。**关键词每轮变换**：profile 里的 keywords 只是种子词，每轮在此基础上换同义/近义/拆词表达（如 ai infra：「大模型推理 面经」「vLLM 面经」「AI Infra 一面 秋招」；数字IC：「数字前端 面经」「RTL 设计 秋招」；岗位：用「招聘/校招/HC/内推」词根轮换），同词至少隔几轮再用——同词重复搜索返回高度重叠、白耗轮次（X31）。
3. `review` 一览（含 desc_chars/images/needs_image_read）→ **先看 desc 长度再决定读不读图**：题面在正文里的帖不读图；正文短图多的才 `prep-images` 后读图（同封面重复图读 1 张即可）→ 甄别广告/诱饵（系列专栏号、卖资料跳过；粗糙真实帖保留）。
4. **题目整理**：从帖子抽题，**基于原文书面化改写**（去口语、可结合上下文补全，不失真不虚构），按知识类型**追加进累计题目 JSON**（先读现有文件去重）——每题带 `a` 字段五要素：思路/考查/关键词/解答/拓展（解答要实质，不能凑字；字段压成单行，不写换行）→ `merge-q` 按 JSON **全量重建**汇总。题卡默认折叠（fold 属性自动设置），用户看题自测、点开看解答。**不写来源标注**。
5. **岗位整理**：书面概括成 `{"items":[{"title","summary","url"}]}` **追加进累计岗位 JSON** → `merge-jobs` 按 JSON 全量重建《岗位汇总》单页（保留链接）。
6. **核对清理**：export 读回汇总确认无误 → `clean-staging` 删临时文件。
7. **汇报**：新增题数/岗位数、跳过广告数；汇总文档 id 每次重建会变，按 hpath 路径定位。

## 当前 job profile 的分类约定

- ai infra：CUDA 与算子／推理框架（vLLM/SGLang）／模型结构与 KV Cache／解码与注意力加速／分布式并行与通信／训练并行与框架／量化／多模态与扩散模型／RL Infra 与训练推理一致性／分布式系统与存储／手撕代码题／基础八股／项目与开放性问题／微调与对齐。
- 数字ic设计：**只收设计方向，验证/UVM 暂不关注**（exclude_title_keywords=["验证","UVM"]，卡片与正文命中即跳过）。分类：数字设计基础／时序与 STA／CDC 与异步设计／总线与接口（AXI/PCIe/AHB）／低功耗与电源／SoC 架构与一致性／存储器专题／工艺与移植／手撕代码题（数字IC）／项目与开放性问题。

## 实用 tips 收集工作流（tips profile：话术/原则/方法论）

```bash
python scripts/pipeline.py --profile profiles/tips.json collect-current        # 抓你正在看的帖子的评论+正文
python scripts/pipeline.py --profile profiles/tips.json collect-search --keyword "<关键词>" --limit 2
python scripts/pipeline.py --profile profiles/tips.json collect-tokens --keyword "<关键词>" --limit 3  # 弹窗限流时的替代路径（X34）：搜索→卡片DOM抽token→逐篇explore整页直开→正文+滚动评论入累计库
python scripts/pipeline.py --profile profiles/tips.json merge-tips             # 重建《实用tips收藏》
```

- **collect-current**：借用你正在看的标签页（不导航），抓当前帖子的可见评论（滚动评论区 3 轮加载更多），按笔记 id 去重后入累计库；帖子正文（desc）也一并存档——tips 帖的正文本身就是内容。
- **collect-search**：按关键词搜索 → 逐帖点开抓评论 + 顺带抓正文 → 入累计库（comments.json，原始全量）。**租房类关键词会触发平台横幅「买卖租赁房屋请注意交易风险」混入 desc 且点卡片弹窗打不开（实测 2026-10）——直接改用 collect-tokens。**
- **审核编辑（必做）**：模型从「帖子正文 + 评论」中挑出**实用 tips**（可操作的话术/原则/方法才留；纯反应、刷屏、无答案提问删除），把精选结果写 `work_dir/tips_curated.json`：`{"posts":[{"title":"…","tips":["…"]}]}`——**条目只保留内容本身，不写作者/赞数**（用户明确）；判据是实用性，不是赞数。
- **merge-tips**：从 `tips_curated.json` 全量重建《实用tips收藏》（生活笔记本根目录，按帖子分组，tip 文本去重）。

## 出问题先读

`references/gotchas.md`（X1~X34 风控/交互/思源/工程坑 + F1~F3 折叠实验，全部实测实录，脚本已内置对策；**X33/X34 是限流绕开的两个新路径**）。分类按题目内容定不按抓取来源（GPU 架构面经归 ai infra、字节芯片部门训练 infra 面经也归 ai infra）；HR/开放题收编为合集条目；多关键词串行放一个后台任务（`=== SEARCH:` 标记分隔）；题面里的 C++ 指针星号要包行内代码（X29）；后台任务可能被提前回收（日志缺 `=== ALL DONE` 即截断），批量词表用同步短批或分段跑。

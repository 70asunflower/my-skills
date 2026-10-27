---
name: investment-analysis
description: 投资工作区（D:\Project\workspace\投资）的分析方法论与操作规程，基于林奇六分类方法卡 + 2026 环境校准 + 可证伪预测档案系统。当用户要求分析某只股票、判断能不能买、做池级重估/候选池研判、刷新行情或财务数据、登记预测/监控/决策/快照、调整评级或买点、问估值三轨/调整后PE/林奇分类，或要在美股分析系统里做任何研究写入时使用——即使没明说"投资分析"二字。
---

# 投资分析（投资工作区方法论）

一套**文件优先、面向十年尺度**的个人投资分析体系：每次分析沉淀为可回溯的研究史、可验证的预测记录、可积累的认知资产。系统不自动交易、不给买卖指令，只产出评级建议 + 买点区间——**最终决策永远由人做**。

工作区根：`D:\Project\workspace\投资`（下称 `<WS>`），主系统在 `<WS>\美股分析系统\`（下称 `<SYS>`）。

## 0. 动手前必读（顺序固定，跳步会翻车）

1. `<WS>\.workbuddy\memory\MEMORY.md` —— 长期记忆：数据源坑、API 契约、操作红线、宏观状态。再看最近一两天的 `YYYY-MM-DD.md` 日志。
2. `<SYS>\SYSTEM.md` —— 最高规则，与任何东西冲突时以它为准。
3. `<SYS>\framework\method_cards\value-basics.md` —— 方法论入口卡 v1.2.0，**必读其「〇·五 2026 环境校准」节：校准条款优先于林奇原著的一切历史参数**。
4. 按标的类型读对应专项卡（见 §2 路由表）。
5. 目标公司档案：`<SYS>\companies\<TICKER>\` 的 profile / 最新 snapshots / theses / monitoring / predictions。
6. 数据用最新快照：`<SYS>\data\market\` 与 `<SYS>\data\fundamentals\` 下日期最新的 `*_snapshot_*.json`；过期（>7 天）先跑 §5c 数据刷新。

## 1. 五条铁律（违反任何一条 = 分析作废）

1. **先定类型再分析。** "公司属于哪一类"是所有后续分析的起点，错一步满盘皆错；类型判定须写在快照开头（"本标的类型 = X，依据 = …"）。
2. **不编造。** 数字必须来自信源、`data/` 快照或确定性代码并标 as_of；不足写 `unknown` / `pending`。可核实而不核实 = 违规。
3. **快照不可变、append-only。** 新结论写新快照 + `evolves_from`，绝不回头改旧分析；被证伪的预测、失败尝试一律保留。
4. **每份分析至少 1 条可证伪预测**（quantified falsification：价格类必须含数字+单位锚，否则登记被拒）。
5. **指标由代码算，AI 只解释。** 公式唯一真相源 `<SYS>\config\metric_definitions.json`；估值分位、体检 verdict、三轨估值带全部走代码，禁止口算替代。

## 2. 林奇六分类路由（读专项卡）

| 类型 | 卡 | 2026 校准要点（详见各卡） |
|---|---|---|
| 慢速增长 | `slow-grower.md` | 股息率门槛对 30Y 长端（非 10Y）；派息率安全线 75%→70% |
| 稳定增长 | `stable-grower.md` | PE 分位必须利率调整后比较；剔除"被动溢价"假便宜 |
| 快速增长 | `fast-grower.md` | 新增第 11 问 capex 轻重（AVGO 1.8% vs GOOGL 115% vs SPCX 235%）；PEG 破位即走 |
| 周期 | `cyclical.md` | 加识别技术/资本开支周期（云厂 capex 指引=需求领先指标）；禁穿越周期 |
| 困境反转 | `distressed-reversal.md` | 现金跑道 4→6 季度 + 查 12 个月债务到期分布 |
| 隐蔽资产 | `asset-play.md` | 新增「被动忽视折价」（小盘 PE 14x vs 大盘 22x） |

2026 系统性红旗（写入所有分析）：前十大集中度 ~40%、被动溢价反转、散户托底使"恐慌见底"信号失灵、0DTE 杠杆放大波动、联储后盾弱化。

## 3. 方法论铁律（历史教训蒸馏，引用案例见 `<SYS>\docs\` 与 MEMORY.md）

- **利率调整后 PE**：`调整后 PE = 当前PE × (当前10Y ÷ 历史均值10Y)`。2026 实算约 ×2.0（10Y≈5%，均值取 2.5%）。报表低 PE 在 5% 利率下普遍不是便宜（NKE/1810/GOOGL 实算见 MEMORY.md）。
- **"低 PE"必做盈利质量校验**：剔除一次性项目后 EPS 趋势 + 可比销售方向 + 指引是否连续下修。反例 LULU：前瞻 PE ~10x 但 EPS 含 29% 一次性关税退款 = 价值陷阱。
- **建仓价位锚定盈利而非历史股价**：AVGO 案例——盈利 +86%/+96% 被动消化估值，死守原价位会踏空；反之价格跑赢盈利时（2026-09 的 TSM/QCOM），按新 EPS 重算买区而不是追高或死守旧区。
- **目标价滞后**：目标均价常不随一致预期下修（小米目标价 38.14→34.67 但 ROE 已 −39%），用目标价算上行空间会高估；小样本动量必须标注机构数（SPCX +25.6 仅 2 家 = 无意义）。
- **大佬持仓 ≠ 你的买点**：引用机构/名人持仓必查其成本与资金性质（伯克希尔 6.5% 折价建仓 Alphabet）。
- **表态 ≠ 执行**：AI CEO 公开呼吁减速与云厂商 capex 上调背离时，看资本配置行为，不看公开信。表外租赁承诺（~9000 亿美元）不入当期 capex，会计口径变化（折旧年限）≠物理减少。
- **评级语义**：BUY=明确买入逻辑；HOLD=持有现有仓位不加仓；WATCH=等买点或条件；SELL=退出。confidence ∈ {HIGH, MEDIUM, LOW}。

## 4. 估值三轨带（纪律尺，非决策器）

- **中轨（金）** = EPS × (min(CAGR, 30%) + 股息率)，封顶 40；
- **上轨（红）** = EPS × 季度 PE 分布 P75（剔异常，回退 5Y 年尾均值 ×1.3）；
- **下轨（绿）** = EPS ÷ min(1÷(rf+2%), 中轨PE×0.75)，**只有下轨依赖利率**（25bp ≈ 下轨 −3.5%）。
- 决策三区：低估买入区越近下轨越加仓 / 合理持有区坐稳不做T / 泡沫警戒区增速放缓才卖。
- 实现：`<SYS>\scripts\valuation.py`（倍数统一由 `_valuation_autofill` 写入，禁止两套公式漂移）。

## 5. 四个工作流

### a. 个股分析（新结论）
类型判定（§2）→ 读专项卡 → 用最新快照数据（§0.6）→ 三轨定位 → 写快照（`python scripts/new_snapshot.py --ticker T`，模板结构：类型判定→结论→触发→事实→主张（支持+反证）→假设→评级/买点/仓位→预测→监控）→ 登记可证伪预测（`prediction.py register`）→ 加监控（`monitor.py add`）→ 沉淀教训（`lesson.py add`）。写完跑 §6 校验循环。

### b. 池级重估（候选池研判）
模板：`<SYS>\docs\自选池全量更新与研判_20260922.md`（同构 20260912 版）。步骤：
1. 先 §5c 数据刷新；
2. westock 四维度到 `data/westock_<date>/`：`rating`（评级动量 = latest − 上月，**标注机构数**）、`fund short`（注意港美分母不同不可横比）、`consensus`（一致预期）、`fund south-holding`（港股）；
3. 从 fund_snapshot 提取年报营收/净利 YoY、ROE、PE 分位（fund_digest 模式）；
4. 大动作标的做新闻核查（价格异动必须有事实归因，防止把叙事当基本面）；
5. 三方交叉（评级动量 × 估值 × 价格）→ 背离区识别 → **gate 日历**（每个待裁决标的的财报/验证日期）；
6. 评级默认不动除非 fundamental gate 翻转；买区重算锚定新 EPS（PE 锚示例：`首批 = EPS×28~30`）；
7. 产出 doc 到 `<SYS>\docs\`，watchlist 变更经 core API 落盘（§5d）。

### c. 数据刷新（五组串行，断点续跑）
```bash
cd <SYS> && NODE="C:/Users/qilin/.workbuddy/binaries/node/versions/22.22.2-5/node.exe"  # 版本会升级，用前 ls 校验
python scripts/fetch_quotes.py --node "$NODE"      # ① 行情：westock 优先，不耗 Wind
python scripts/fetch_deep.py --node "$NODE"        # ② 深度：K线绩效/风险/事件（Wind）
python scripts/fetch_fund.py --node "$NODE"        # ③ 财务体检+估值分位（Wind）
python scripts/fetch_shareholder.py --node "$NODE" # ④ 股东回报（Wind）
python scripts/fetch_profile.py --node "$NODE"     # ⑤ 公司档案（Wind）
python scripts/refresh_rf.py                       # ⑥ 无风险利率（FRED，失败非致命）
```
重跑 = 只补缺失（--force 才全量）；Wind CLI 路径 `~/.agents/skills/wind-mcp-skill/`，余额/接口行为会变，报错先看 MEMORY.md 数据源备忘。

### d. 档案与候选池写入（必须走 core API / scripts，禁手写 JSON）
- CLI：`prediction.py register/verify/expire`、`monitor.py add/check/close`、`watchlist.py`、`lesson.py add`；或 `import core`（`sys.path.insert(0, "<SYS>/scripts")`）。
- **`core.watchlist_update(ticker, rating=None, confidence=None, zone=None, note=None)`**：只校验 rating 不校验 confidence，写前手动确认 ∈ {HIGH,MEDIUM,LOW}。
- **`core.C.update_json_record` 的 mutate 必须返回 data 本体或 None**——返回别的会把整个档案覆盖成那个结果（NKE 事故）。收集变更轨迹用闭包列表。
- 无 `core._fred_10y()` / `core.monitoring_list()`；用 `core.risk_free_10y_pct()` / 直接读 monitoring.json。
- 归档公司：`archive/companies/<T>_<date>` + watchlist 该行 status=ARCHIVED。

## 6. 数据源分工与口径陷阱（速查，全量见 MEMORY.md）

| 来源 | 负责 |
|---|---|
| 腾讯 westock | 行情/K线/评级动量/卖空/南下/一致预期/披露日（`C:\Users\qilin\.local\bin\westock.exe`，输出 UTF-8，subprocess 直调勿走 shell 管道） |
| Wind | 复权K线、PE 历史、深度财报、股东、估值分位（CLI 或 ZCode wind 插件 MCP 均可） |
| FRED | 美债 10Y（`core.refresh_risk_free_from_fred()`）；502 时可用 Wind EDB 补 |

高频陷阱：**① 同名字段会静默改单位**（市值、分红都发生过）——能自算的优先自算（市值=价格×股本；股息率=TTM 分红自算），跨日对比先验量级。② westock 美股 K 线**不复权**（拆股假缺口）；SPCX 历史含旧 SPAC 主体污染（用 `earliest_valid_date` 滤）。③ BRK-B 代码 `usBRK.B`（点号）。④ 港股卖空比率分母是成交量，不可与美股横比。⑤ 已知脏数据：CBRS PE 597、LULU 财务序列混季度（毛利率 1.2% 不可用）、RKLB/SPCX 亏损无 PE。⑥ 快照必须回填 `wind` 字段，下游估值图靠它。

## 7. 环境红线（本机）

- **禁止向 git 传中文路径参数**（2026-09-13 曾误删 255 文件）：移动/删除用 Python；暂存用 `git add -A --pathspec-from-file=<文件>`；排查用 `git ls-files -z` + Python 过滤。
- Git Bash 残缺（`head`/`wc`/`dirname` 不可用，`/tmp` 非 Windows 路径）：批量文本处理一律 Python。
- 改完必跑校验循环：`python scripts/check_integrity.py`（含 GATE 日历段）+ `python -m unittest discover -s tests`（当前 171 项）。日常盘前看 `python scripts/daily_brief.py`（gate → 持仓触发线 → 到期监控 → 组合红旗，只读）。
- 改前端必须改真源 `<SYS>\workbench\投资工作台.html`，再同步两副本（直接改副本会被覆盖）。
- 评级/买点/买卖属用户决策域：AI 更新数据、给建议、标漂移，不擅自改评级。

## 8. 输出纪律

- **汇报分层（2026-10-23 用户反馈，长期价值为主线）**：① 基本面/价值层先行——类型判定、盈利与现金流、估值（三轨/前瞻 PE）、基本面 gate；② 论点状态（支持/反证哪边在强化）；③ 技术面与触发线只作为**风险控制层**放最后，并注明：止损/减持线是用户自设的保险丝，卖出的正当理由是**论点被证伪或 gate 落空**，不是价格碰线；技术信号本身不构成买卖理由。
- 中文、结论先行；事实可核实必先调工具，核实不了标 `[待核实]`。
- 成功后附数据来源（"数据来源于万得 Wind 金融数据服务"等）。
- 报告落 `<SYS>\docs\`（池级）或 `companies/<T>/snapshots/`（个股，经脚本）；快照开头写类型判定。

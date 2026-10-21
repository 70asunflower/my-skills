# gotchas：小红书收集 pipeline 实测踩坑（X1~X30 + F1~F3 折叠/格式实验）

迁移自 xhs-job-notes（2026-08-30 升级为 xhs-pipeline），每条都是实测教训，脚本已内置对策。

## 风控与交互

### X1. Windows shell 内联中文 JSON 必坏
中文参数一律走 Python urllib（pipeline.py 封装）或文件，绝不 shell 内联。

### X2. WebBridge 的 `fill` 在千问/React 受控输入框上必失败
CDP 真实点击聚焦 → `Input.insertText` → 验证回显。已封装。

### X3. 合成 click() 点复制按钮不写剪贴板
必须 CDP `Input.dispatchMouseEvent`（受信任点击）。截获用拦截器（见 F2）。

### X4. 系统剪贴板可能整体不可用（360 等）
拦截器 hook `navigator.clipboard.writeText` 存 `window.__capA`，从 JS 变量取，永不依赖读系统剪贴板。

### X5. 两种 Copy 按钮 / X6. scrollIntoView 后坐标是动画瞬时值 / X7. 长回复按钮在视口外万像素
永远取文档序最后一个 Copy；滚动后等 2.5s 再量坐标；先判可见性再点。已封装在 ai-tutorial-pipeline 的 wb.py。

### X8. 生成中的判断：Stop 按钮是唯一可靠信号（AI 对话类 profile 适用）
思考期页面文字完全不增长但 Stop 存在 = 活着。完成 = Stop 消失 + 复制按钮数增加 + 双确认。

### X9. 新会话没有"当前标签页"返回 HTTP 502
会话先 `find_tab`/`navigate` 再做其他操作。

## 小红书专项

### X10. 直接拼 URL 访问笔记 → 300017「url is invalid」
打开笔记一律真实点击搜索卡片；搜索框交互后必须验证 `location.href` 含 `/search_result`（Enter 可能被联想下拉吞掉，重试一次再回退）；300017 错误页文本纳入 risk_blocked 检测。

### X11. 卡片坐标 (0,0)——虚拟化渲染
坐标现测现用；滚动步长随视口 `max(300, innerHeight-200)`（固定 800px 在矮视口有盲区）；点击点钳制在卡片内且 < innerHeight-10；提取失败对同一卡重试一次。

### X12. 关闭按钮 CDP 点击无效，Esc 一次即关
close_note 以 Esc 优先（两次）+ 验证 `#detail-title` 消失，关闭按钮点击做兜底；最终失败直接 raise。主循环整体 try/finally，异常也打印已暂存清单。

### X13. 同一篇反复弹出
卡片标题 `processed` + 提取标题 `seen_notes` 双重去重。

### X14. 登录态探测
`web_session` cookie 是 httpOnly，以"无登录弹窗"判定已登录。

### X15. 广告/诱饵识别 + 分类过滤
强特征（卖资料/付费/加微信/扣1…）命中即跳，弱特征命中两个跳；系列专栏号靠模型终审。分类可配 `exclude_title_keywords`（如数字IC profile 配 ["验证","UVM"]，卡片标题和正文前 200 字命中即跳过）。

## 思源侧

### X16. 汇总制：思源不存每帖页（用户决策 2026-08-30）
只维护《题目汇总（按知识类型）》×分类 与《岗位汇总》单页。帖子全文只存在于暂存期，抽题一次做对；核对完 `clean-staging` 删临时文件。汇总里的笔记链接 token 可能截断/失效，仅作 id 去重与线索。

### X17. 汇总重建必须整删整建（Fix B）——且 rebuild 分支也要删旧文档
两个坑叠加：① `--rebuild` 分支曾把 removeDocByID 整段跳过（被 `if not rebuild:` 包住）→ 每跑一次就多一个同名重复文档（用户截图实录：每分类 3 个同名汇总）；② delete children + updateBlock(root) 重建会因 deleteBlock 部分静默失效 + 根节点合并残留 → 旧行残留/URL 丢失/行数翻倍。**对策：无论 merge 还是 rebuild，都先删同路径全部旧文档（getIDsByHPath 可能返回多个 id 要全删）→ 轮询 getIDsByHPath 确认清空 → createDocWithMd（同路径）**，文档 id 每次会变（按 hpath 定位）。验证一律用创建时返回的 doc id（getHPathByID/export），不要立刻按 hpath 重查——块表 SQL 索引滞后会查到已删文档。
另：更根本的简化是「累计 JSON 全量重建」——累计题目/岗位 JSON 是唯一事实来源，merge 命令只做文件内去重 + 整删整建，不再解析思源里的旧文档（导出解析还有列表项答案丢失等问题）。

### X18. 装载已有汇总时"剥来源标注"只适用于题目汇总
题目汇总不写来源（用户要求）；岗位汇总的链接要保留——去重 id 必须在剥标注**之前**提取，且岗位页装载时不剥标注（2026-08-30 实录：剥了导致 3 条岗位全丢链接）。

## 折叠题卡（F 系列，2026-08-30 实验）

### F1. 列表项上的 IAL `{: fold="1"}` 不可靠
createDocWithMd 的 markdown 里写 IAL，存层的列表项会把 IAL 当**字面文本**保留（getBlockAttrs 查不到 fold），不要用。

### F2. 正确方案：创建后 setBlockAttrs
`/api/attr/setBlockAttrs {"id": <列表项块id>, "attrs": {"fold": "1"}}` 实测生效。题卡结构 = 题目列表项 + 嵌套子列表（思路/考查/关键词/解答/拓展），对"有子块的列表项"统一设 fold，叶子项跳过。

### F3. getChildBlocks 对列表项 id 的遍历有"重复访问"怪癖
walk 时同一列表项可能出现两次（folded 计数翻倍即此因），setBlockAttrs 幂等所以无实际影响；校验逻辑不要用遍历计数做断言，用 export 内容计数。

## 工程陷阱

### X19. `import wb` 后裸调 `wb(...)` 是 TypeError
模块 vs 函数重名陷阱，两个 skill 共踩过三次。新脚本写完先 `python -m py_compile` + import 冒烟。

### X20. 循环计数器写错导致超量抓取
停止条件必须用循环内真实递增的变量；长循环先小 limit 验证。

### X21. Git Bash heredoc 传含反斜杠/中文的补丁脚本不可靠
\U 等转义会被破坏。改用 Write 工具写脚本文件再执行。

### X22. 评论抓取（comments profile，2026-08-30 实测）
- 评论在笔记弹窗右侧面板：`.comment-item` + `.author .name` + `.content .note-text`，首屏可见即可抓（滚动 `.comment*` 容器加载更多，scrape_comments 内置 3 轮滚动+按文本去重）。
- 筛选规则：楼主回复 / ≥15 字 / 含问句保留，纯表情和灌水丢弃（`comments_dropped` 计数）。
- 点赞数解析：`parse_likes` 支持「2.1万」→ 21000；`badge` 记录「作者赞过」。
- 累计库：`work_dir/comments.json`，按笔记 id 去重，merge-comments 全量重建《神评论收藏》。
- 教训：任何新文件写入都必须走 Write 工具完整重写，heredoc 内嵌代码含 
 转义会把源码写坏（本次 pipeline.py 被写坏后整体重写恢复）。

### X23. 评论收集的筛选判据是实用性，不是赞数
首版按「楼主回复/≥15字/含问句」过滤，37 条里混入大量表情刷屏、重复引用、无答案提问。用户明确：**看实用性**——可操作的话术/原则/方法论才收，纯反应和灌水删。流程改为两段：collect 存原始全量（comments.json）→ 模型逐条按实用性精筛写 comments_curated.json → merge-comments 优先读 curated。赞数只作参考元数据，不作为保留依据。

### X24. tips 收集：判据是实用性，条目只留内容
用户 2026-08-30 明确两点：① 筛选看**实用性**（可操作的话术/原则/方法），赞数只作参考元数据不作为保留依据；② 汇总条目**不写作者/赞数**，只留内容本身。文档更名《实用tips收藏》（生活笔记本根目录），profile 更名 tips.json。tips 来源=帖子正文+评论（有些 tips 帖正文就是内容，collect 时 desc 必存）。

### X25. 暂存文件命名时间戳错位（2026-09-05 首跑实录，已修复）
旧版图片用下载时刻的 `int(time.time())`、JSON 用落盘时刻命名，同篇笔记二者常差 1 秒，按 JSON 文件名去猜图片文件名必然落空——本轮据此误判"腾讯帖 4 张图下载失败"，浪费多轮排查（真实文件名是 `_..._2_img0`，JSON 名是 `_...1s后_2.json`）。修复：每篇笔记生成统一 `uid`，图片与 JSON 同名不同后缀；`note_id`/`images_failed` 也写进暂存 JSON。排查图片问题时永远先 `ls 暂存目录` 看真实文件名，不要从 JSON 名推。

### X26. 跨关键词重复抓取同一笔记（已修复）
同轮多关键词搜索会反复命中同一热门笔记（"小鹏 ai infra部署 一面"被 3 个关键词各抓一次），旧版 `seen_notes` 只在单次 search 进程内去重，跨进程无效。修复：`visible_cards` 现在带出卡片 `href`，`cmd_search` 点开前先按笔记 id 查 `_seen.json` manifest（staging 内，clean-staging 一并删除），命中直接跳过不点击（省 2.5s/篇），并把已处理 id（含广告/过滤的）写回 manifest。注意：manifest 存活期间重复关键词的 dups 计数会升高，这是预期行为。

### X27. 读图工作流：先 review 看正文长度，再 prep-images 转压（2026-09-05 沉淀为命令）
- 大图（高分辨率 webp 截图）直接 Read 会报 "WebP image exceeds the model image budget"，必须先转压。新增 `prep-images` 命令：暂存图片统一转 ≤1400px JPG 到 `conv/` 子目录，顺带报告 JSON 引用但磁盘缺失的图片。
- 省轮次的核心判据：**先看 `review` 输出的 desc_chars**——面经帖题面往往正文就完整（寒武纪 742 字 10 题、小米玄戒 12 题），只在"正文短图多"时读图；同一封面重复 N 张的帖（如蚂蚁帖 3 图同一封面）读 1 张即可。
- 图片在下载时已有单张失败保护（images_failed 计数，不再炸整个 search）。

### X28. 收集侧约定补充（2026-09-05）
- **分类按题目内容定，不按抓取来源**：从"数字IC 实习"关键词抓到的摩尔线程 GPU 架构面经（CUDA/GPU 微架构题）应归 ai infra 题库。
- **HR 面/开放题收编为合集条目**：同公司的 HR 开放题合并成一条「XX 开放题合集」item（仿华为三面合集），不逐题建卡；先查库里是否已有同款合集（腾讯 HR 面 8 题与已有 #87 完全重合，直接跳过）。
- **多关键词串行放一个后台任务**：`for kw in ...; do python pipeline.py search ...; done` 用 run_in_background + `=== SEARCH:` 标记分隔，单浏览器通道不会争抢，报告可按标记切片。
- **上一轮残留暂存**：开工时 staging 里若有旧文件（上轮没跑 clean-staging），先对照累计库确认已合并再决定是否纳入本轮，merge 去重键会兜底防重复入库。

### X29. 题面星号与思源行首粗体交叉配对（2026-09-27 实测）
- 题面一行里有多个 `*`（如 C++ 指针写法 `const int*` 与 `int const*`）时，会与题卡行首的 `**Q…**` 粗体标记交叉配对，思源把中间文本渲染成斜体；export 校验按行首 `- **Q` 匹配就会表现为"merge 后行数比入库少 1"。
- 对策：题面里的指针/乘号星号一律包行内代码（`` `const int*` ``），写累计 JSON 时就处理好；排查行数差先 grep 导出内容找变形题卡（形如 `- *Q138. …`），别急着怀疑 merge 逻辑。

### X30. 单篇分享链接收集：fetch-url（2026-09-27 沉淀为命令）
- 用户直接丢笔记分享链接时用 `fetch-url <链接> --category <分类> [--keyword <兜底词>]`，不走搜索（单篇搜索点开既慢又可能被同名热门卡干扰）。
- 三级路径：① 浏览器已开着该笔记（按 note id 匹配当前标签页）→ 零导航零风控直接抓（最优）；② 直连带 xsec_token 的分享链接——实测 `/discovery/item/` 分享链可直开笔记**整页**（非弹窗），提取/下载图片全部正常；③ 触发风控且有 --keyword → 搜索真实点击兜底（兜底前 close_note 必须容错，错误页上无弹窗可关会抛错）。
- 坑：直开的笔记整页按 Esc 关不掉"弹窗"（本来就没有弹窗），收尾 close_note 抛"弹窗关闭失败"——已改为容错，数据先落盘后关页，报错不影响结果；页面留在笔记页无害，方便用户继续看。
- fetch-url 会把 note id 写进 `_seen.json`，同会话后续批量搜索自动跳过该篇，不会重复入暂存。

### X31. 同词重复搜索收益递减，每轮要变换搜索词（2026-09-27 用户明确）
- 小红书搜索排序稳定：同一关键词隔天再搜，视口内卡片与上轮高度重叠——实测一轮 9 词抓 18 篇中过半与累计库重复（同词是前几轮用过的种子词），同一热门帖还跨关键词重复命中（腾讯帖 2 次、士兰微帖 2 次），空耗轮次且容易撞"连续 4 次重复熔断"。
- 对策（用户明确要求）：**每次搜索轮换相关搜索词**——在 profile 种子词基础上换同义/近义/拆词表达（如「AI infra 面经」↔「大模型推理 面经」「vLLM 面经」「AI Infra 一面 秋招」；「数字IC 面经」↔「数字前端 面经」「RTL 设计 秋招」；岗位词用「招聘/校招/HC/内推」词根轮换），同词至少隔几轮再用。

### X32. 搜索抓空的两种形态：视口 0 卡片（时序）与连续提取失败（软限流）（2026-09-27 实测）
- **形态一：`视口内卡片 0 张`**——结果页 DOM 其实有卡片（诊断时 section.note-item 有 30 个），是搜索跳转后渲染/抓取时序问题，间歇性（同轮 9 词中 5 个抓空）。对策：**直接重跑该词即可**，重跑大概率正常；不用改交互链。
- **形态二：连续 `提取失败(已重试)`**——卡片列得出、点开弹窗但内容拿不到，连开 23 个卡片持续 7 分钟后自行恢复，非风控页（aborted 为 null）。疑似连续快开笔记触发内容限流。对策：cmd_search 已加 **fails>=5 熔断**（连续提取失败 5 次即停本关键词），避免把整页卡片硬扫一遍加剧限流；等待几分钟后重跑。
- 两种形态都不要当场反复重试硬刚——间隔后重跑是唯一正确姿势。
- **限流可持续 1 小时以上（2026-09-29 深夜实测）**：白日大量收集（16 篇+）后当晚限流，冷却 30 分钟未恢复、每 4 分钟重试反而延长限流；上一次（同日 16:43）仅 7 分钟恢复——当日累计操作量决定严重度。正确姿势：**长冷却（≥90 分钟）+ 单次探测**，探测成功才继续词表；连续短重试会让限流越滚越长。当日总弹窗开量是隐形配额，大量收集后主动收手。
### X33. 博主主页整收：卡片点击开弹窗无效，走 SSR token + 整页直开（2026-09-30 实测，fetch-profile 命令）
- **用户给博主主页链接要整收时，不要走 search/卡片点击**。实测主页卡片上 CDP 真实坐标点击（elementFromPoint 验证命中 `a.cover`）后**弹窗不开、URL 不变**——主页笔记数据是 SSR 直出（resource timing 无 user_posted 请求，`__INITIAL_STATE__` 的 Vue ref 里也没有 per-note token），SPA 点击处理器拿不到 token 就静默 no-op。裸 href（`/explore/<id>` 无 token）还会触发 `/404/sec_*` 安全重定向。
- **正确路径（已固化为 `fetch-profile` 命令）**：KimiBridge `network start` → 导航主页 URL → `network list/detail` 取**文档响应体**（约 250KB SSR HTML）→ 正则抽 `(noteId, xsec_token)` 配对（卡片链接形如 `/user/profile/<uid>/<noteId>?xsec_token=...`）→ 逐篇导航 `explore/<id>?xsec_token=<tok>` 整页直开（fetch-url 已验证的路径）→ extract_note 照常。实测 24/24 配对成功、24 篇全部抓到、0 失败，且**不受弹窗内容限流影响**（限流期整页 SSR 仍可开）。
- 排障教训：① 调试时 dump href 别 slice 截断——token 在 href 的 80 字符之外，截断导致误判「无 token」绕远路；② `find_tab` 按模糊 URL 匹配会抓到用户开着的其它小红书标签页（初判「点击无效」其实跑在别人页面上），精确匹配主页路径；③ 页内 fetch user_posted API 即使带 `_webmsxyw` 签名也报 `jarvis-gateway: create invoker failed`（缺 x-s-common），别恋战——network 捕获 SSR 文档体是零风险通路；④ CDP `Page.addScriptToEvaluateOnNewDocument` 需先 `Page.enable` 才生效，否则静默无效。
- 主页部分笔记 token 会重复（SSR 里相邻卡片共用同一 token），单篇失败不熔断流程，记 fails 后用 fetch-url 补漏即可。

### X34. 搜索弹窗限流的绕开路径：卡片 token 就在 DOM 里（2026-09-30 实测，search-tokens 命令）
- **搜索页弹窗被限流（点卡片弹窗无内容）时不必等冷却**：结果页每张卡片的 DOM 里都有一条 `/search_result/<id>?xsec_token=...` 链接（真实用户点它开弹窗用），token 完整可用。`visible_cards` 一直抓的是卡片第一个 `a[href]`——无 token 的 `/explore/<id>` 裸链，所以历史上从未发现 token 就在眼前。
- **正确路径（已固化为 `search-tokens` 命令）**：`do_search` 真实搜索交互 → `_dom_note_pairs` 从卡片 DOM 抽 (noteId, xsec_token, xsec_source) → 逐篇导航 `explore/<id>?xsec_token=<tok>&xsec_source=<原样回传>` 整页直开 → extract_note/图片/评论照常。实测弹窗限流期间「长鑫 面经」单词 2/2 成功。
- **搜索结果页没有 SSR 数据**（文档体 74KB 无卡片块、无 token；search/notes API 直连 URL 落地时不触发）——token 必须从 live DOM 取，且 `do_search` 的真实搜索框交互是触发结果渲染的可靠方式。
- 排障教训：network 捕获扫搜索数据源时，JSON 风格正则（`"id":"…"`）与 href 属性风格要分开；document body 用 detail 可取但搜索文档里没有卡片数据，别恋战。
- **2026-10-01 更新：X32 的「长冷却+单次探测」规程只在必须走弹窗的场景才需要**（collect-current/collect-search 评论区收集、fetch-url 借标签页路径）。内容收集（题库/岗位）已不依赖弹窗：搜索限流改 `search-tokens`（X34）、主页用 `fetch-profile`（X33）——限流当天两轮共 52 篇 0 失败即为实证。弹窗限流与 SSR 整页配额是分离的。

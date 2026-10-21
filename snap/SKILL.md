---
name: snap
description: 用本机 snap CLI 截图/体检/像素对比页面渲染效果，确认展示类项目的视觉质量（零依赖、一条命令、已实测验收）。当用户要"截图看看效果、看某个位置/某张图做得怎么样、检查页面/海报/演示页/网页效果对不对、交付前检查一遍、改版前后对比、视觉回归、截整页长图/元素图/高清图"时使用；HTML 海报、演示页、前端界面等展示项目迭代中确认视觉效果一律首选本技能，替代起浏览器编排截图。需要登录态的页面、需要点击填表交互、或桌面应用画面时不适用。
---

# snap：页面截图 / 体检 / 对比 / 基线校验

## 工具位置与要求

- CLI 单文件：`D:\Project\Zcode\snap\code\snap.mjs`，全局命令已注册为 `snap`（零 npm 依赖，Node 22 内置 WebSocket 直连 Chrome/Edge CDP，无头渲染）
- 运行要求：PATH 里有 Node 22+ 与本机 Chrome 或 Edge（Windows 自动 Fallback 至原生 Edge；若安装在特殊路径可设 `CHROME` 环境变量指向可执行文件）
- 完整文档在工具项目内：`docs/Design.md`（接口与退出码）、`docs/TDD.md`（实现原理）；改过工具后跑 `node D:\Project\Zcode\snap\code\tests\run-tests.mjs` 回归（34 项用例）

## 何时用 / 何时不用

| 场景 | 方案 |
|------|------|
| 看 HTML 海报/演示页/网页的渲染效果、检查某个位置的图 | 本技能（截图） |
| 交付前确认无坏图/溢出/文字裁切/控制台报错，并作为门禁拦截 | 本技能（`--audit --strict`，命中退出码 7） |
| 改版前后确认改动范围、视觉回归 | 本技能（`--diff`，看 `regions`） |
| 一条命令做「截图 → 比基线 → 退出码」 | 本技能（`--check`，超出容差退出码 8） |
| 需要登录态的真实页面 | WebBridge / control-browser（本技能每次用全新临时 profile，无登录态） |
| 需要点击、填表、滚动等交互 | control-browser |
| 桌面应用画面 | Computer Use |
| SVG 图交付思源 | svg-diagram-pipeline（其渲染环节与本工具同原理） |

## 四种模式

示例假设当前项目根目录有 `poster.html`；输出建议放项目 `tmp/`（或 git 忽略目录），避免产物混入正式文件。

### 1. 截图

```bash
snap poster.html --selector ".hero" --pad 16 --scale 2 -o tmp/hero.png
```

| 选项 | 作用 | 默认 |
|------|------|------|
| `--selector <css>` | 只截第一个匹配元素，"看某个位置"的主力 | 整个视口 |
| `--pad N` | 元素/区域截图向外扩展 N 像素（保留卡片阴影与呼吸感） | 0 |
| `--full` | 整页长图 | 视口 |
| `--clip x,y,w,h` | 页面坐标区域截图 | 视口 |
| `--vw N --vh N` | 视口尺寸 | 1280x800 |
| `--scale N` | 高清倍率 | 1 |
| `--color-scheme dark\|light\|auto` | 固定 `prefers-color-scheme`；auto 跟随系统 | auto |
| `--dark` | 等价于 `--color-scheme dark` | false |
| `--media <type>` | 仿真媒体类型（'screen' 或 'print'） | 默认 |
| `--ignore <css>` | 截取前把命中元素涂成纯色（可重复），动态内容回归必用 | 无 |
| `--wait N` | 字体图片就绪后追加等待毫秒数，动态内容多时加 `--wait 500` | 0 |
| `-o <路径>` | 输出文件 | `./snap-<时间戳>.png` |

输入支持 http(s) URL 与本地 HTML（file:// 直接加载，无需起服务）。

**系统主题是暗色时必须显式指定** `--color-scheme light`，否则浅色版式截不出来——无头 Chrome 默认跟随系统主题。

### 2. 体检（不产图，零图片 token）

```bash
snap poster.html --audit
snap poster.html --audit --strict          # 有缺陷即退出码 7，可做 CI 门禁
snap poster.html --audit --a11y            # 追加对比度/字号/alt/点击区检查
```

stdout 输出 JSON 报告：`brokenImages`（坏图，含 `status`/`naturalWidth`）、`overflow`（横向溢出元素）、`clippedText`（被裁切文字）、`consoleErrors`（控制台错误与资源加载失败）、`fontsReady`、`loadMs`、`counts`（真实总数）、`truncated`（是否因 8 条上限被截断）、`verdict`（`status`/`failed`/`gateFailed`）。`--a11y` 追加 `lowContrast`/`tinyText`/`missingAlt`/`smallTapTarget`。

判定"效果对不对"先跑体检，程序可断言的问题不花截图成本；需要审美判断时再截图。

### 3. 像素对比（视觉回归）

```bash
snap --diff v1.png v2.png -o tmp/diff.png
snap --diff v1.png v2.png --align bottom -o tmp/diff.png   # 高度不一致时
```

输出差异统计 JSON（差异像素数、占比、并集外接框 `bbox`）与红色标记差异图。关键字段：

- `regions[]`：差异按连通域聚类后的区域（最多 20 块，含 `width`/`height`/`diffPixels`），用于判断"改了几处、分别在哪"；`regionCount` 为真实区域数。**分散改动看 `regions`，不要只看 `bbox`**——bbox 是并集，多处改动会糊成一大块。
- `--threshold N` 控制单通道容差（默认 16，吸收抗锯齿抖动）。
- 尺寸不一致默认拒绝（退出码 6）；`--align top|bottom|min` 改为按公共区域比较并在 `aligned` 中标注裁剪信息（`bottom` 适合页脚改动，`top`/`min` 适合顶部改动）。
- `--region-gap N` 控制区域合并间距（默认 12）。

### 4. 基线校验（一条命令的回归闭环）

```bash
snap poster.html --check --full            # 首次自动建基线；之后比对，差异超容差退出码 8
snap poster.html --check --full --update-baseline   # 确认改动后更新基线
```

基线按「输入 + 视口 + 倍率 + 主题 + 媒体 + 整页 + 选择器 + 区域 + 忽略项」派生键，存于 `.snap/baseline/`（`--baseline-dir` 可改）。变更时把本次截图与差异图落在同目录（`<key>.current.png` / `<key>.diff.png`）供复核。**基线键含输入文件路径，重命名文件视为新基线。**

## agent 工作流闭环

1. 写/改 HTML 后跑截图命令，单次约 1.5–2 秒（其中浏览器冷启动约 1.6 秒，页面加载本身几十毫秒），浏览器独立起停无残留；
2. 用 Read 工具读取生成的 PNG，图片进入视觉通道即可判断效果——这一步就是"看一眼"；
3. 输出约定：进度消息走 stderr，最终结果（保存路径行或 JSON）走 stdout，脚本可据此编排；
4. 退出码：0 成功；1 运行错误；2 用法或输入错误；3 未找到 Chrome；4 页面加载失败；5 选择器未命中；6 尺寸不一致；7 体检门禁命中；8 基线差异超限。

## 故障排查

- `Google Chrome not found`：设 `CHROME` 环境变量指向 chrome.exe 完整路径；
- 浅色版式截出来是暗的：系统在暗色模式，加 `--color-scheme light`；
- 延迟加载的内容没截到：加 `--wait 500` 或更大；
- 动态内容（时间戳、canvas、随机图）导致回归永远有差异：用 `--ignore <css>` 涂平该区域；
- 改了一行字就报尺寸不一致：加 `--align bottom`（或 top）；
- 整页大图 diff 偏慢：改用 `--clip` 区域截图后再对比；
- 截图宽度比视口小 15px：不会发生，滚动条已内置隐藏（--hide-scrollbars）。

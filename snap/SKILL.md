---
name: snap
description: 用本机 snap CLI 截图/体检/像素对比页面渲染效果，确认展示类项目的视觉质量（零依赖、一条命令、已实测验收）。当用户要"截图看看效果、看某个位置/某张图做得怎么样、检查页面/海报/演示页/网页效果对不对、交付前检查一遍、改版前后对比、视觉回归、截整页长图/元素图/高清图"时使用；HTML 海报、演示页、前端界面等展示项目迭代中确认视觉效果一律首选本技能，替代起浏览器编排截图。需要登录态的页面、需要点击填表交互、或桌面应用画面时不适用。
---

# snap：页面截图 / 体检 / 像素对比

## 工具位置与要求

- CLI 单文件：`D:\Project\Zcode\snap\code\snap.mjs`，零 npm 依赖（Node 22 内置 WebSocket 直连 Chrome CDP，无头渲染）
- 运行要求：PATH 里有 Node 22+ 与本机 Chrome；Chrome 装在非默认路径时设 `CHROME` 环境变量指向 chrome.exe
- 完整文档在工具项目内：`docs/Design.md`（接口与退出码）、`docs/TDD.md`（实现原理）；改过工具后跑 `node D:\Project\Zcode\snap\code\tests\run-tests.mjs` 回归（13 项用例）

## 何时用 / 何时不用

| 场景 | 方案 |
|------|------|
| 看 HTML 海报/演示页/网页的渲染效果、检查某个位置的图 | 本技能（截图） |
| 交付前确认无坏图/溢出/文字裁切/控制台报错 | 本技能（--audit） |
| 改版前后确认改动范围、视觉回归 | 本技能（--diff） |
| 需要登录态的真实页面 | WebBridge / control-browser（本技能每次用全新临时 profile，无登录态） |
| 需要点击、填表、滚动等交互 | control-browser |
| 桌面应用画面 | Computer Use |
| SVG 图交付思源 | svg-diagram-pipeline（其渲染环节与本工具同原理） |

## 三种模式

示例假设当前项目根目录有 `poster.html`；输出建议放项目 `tmp/`（或 git 忽略目录），避免产物混入正式文件。

### 1. 截图

```
node D:\Project\Zcode\snap\code\snap.mjs poster.html --selector ".hero img" --scale 2 -o tmp\hero.png
```

| 选项 | 作用 | 默认 |
|------|------|------|
| `--selector <css>` | 只截第一个匹配元素，"看某个位置"的主力 | 整个视口 |
| `--full` | 整页长图 | 视口 |
| `--clip x,y,w,h` | 页面坐标区域截图 | 视口 |
| `--vw N --vh N` | 视口尺寸 | 1280x800 |
| `--scale N` | 高清倍率 | 1 |
| `--wait N` | 字体图片就绪后追加等待毫秒，动态内容多时加 `--wait 500` | 0 |
| `-o <路径>` | 输出文件 | `./snap-<时间戳>.png` |

输入支持 http(s) URL 与本地 HTML（file:// 直接加载，无需起服务）。

### 2. 体检（不产图，零图片 token）

```
node D:\Project\Zcode\snap\code\snap.mjs poster.html --audit
```

stdout 输出 JSON 报告：`brokenImages`（坏图）、`overflow`（横向溢出元素）、`clippedText`（被裁切文字）、`consoleErrors`（控制台错误与资源加载失败）、`fontsReady`、`loadMs`。判定"效果对不对"先跑体检，程序可断言的问题不花截图成本；需要审美判断时再截图。

### 3. 像素对比（视觉回归）

```
node D:\Project\Zcode\snap\code\snap.mjs --diff v1.png v2.png -o tmp\diff.png
```

改版前后各截一张再对比，确认"只改了想改的地方"。输出差异统计 JSON（差异像素数、占比、差异外接框）与红色标记差异图。`--threshold N` 控制单通道容差（默认 16，吸收抗锯齿抖动）；两图尺寸不一致时拒绝比较（退出码 6）。

## agent 工作流闭环

1. 写/改 HTML 后跑截图命令，单次约 0.1–3 秒，浏览器独立起停无残留；
2. 用 Read 工具读取生成的 PNG，图片进入视觉通道即可判断效果——这一步就是"看一眼"；
3. 输出约定：进度消息走 stderr，最终结果（保存路径行或 JSON）走 stdout，脚本可据此编排；
4. 退出码：0 成功；1 运行错误；2 用法或输入错误；3 未找到 Chrome；4 页面加载失败；5 选择器未命中；6 尺寸不一致。

## 故障排查

- `Google Chrome not found`：设 `CHROME` 环境变量指向 chrome.exe 完整路径；
- 延迟加载的内容没截到：加 `--wait 500` 或更大；
- 整页大图 diff 偏慢：改用 `--clip` 区域截图后再对比；
- 截图宽度比视口小 15px：不会发生，滚动条已内置隐藏（--hide-scrollbars）。

---
name: infographic
description: "Create professional editorial-style HTML infographic cards from articles or URLs. Designs follow a modern magazine aesthetic with dark backgrounds (#1a1a1a), orange-red accent colors (#e8613a), large serif titles, and numbered grid cards. Always use this skill when the user asks to make an infographic, information card, visual summary, or wants to convert an article/paper/URL into a visually striking HTML card. Also use when the user says 'generate an image from this article' or 'make a visual card'. Supports both Chinese and English content."
---

# Infographic Card Generator

从文章或 URL 生成深色杂志风格的信息卡 HTML，支持 draw.io 或 Playwright 导出 PNG 图片。

## 工作流程

### Step 1: 分析内容

分析传入的信息密度，决定布局策略：

- **低密度（内容少）**：采用"大字符主义" — 标题字号撑满，数据放大至 120px+ 作为背景视觉元素
- **中密度**：采用"双栏网格" — 2 列内容区格
- **高密度（内容多）**：采用"多栏网格" — 3 栏参考报纸排版

### Step 2: 生成 HTML

使用下面的设计规范生成完整的 HTML 文件。

### Step 3: 导出 PNG

运行截图脚本：

```bash
cd <skill-path>/scripts
python screenshot.py <path-to-html> [--output <output-png>] [--viewport 900x1200]
```

如果指定了 `--output`，图片保存到指定路径；否则默认保存到 HTML 同目录下，文件名加 `_card.png` 后缀。

---

## 设计规范

### 字体

```html
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@700;900&family=Noto+Sans+SC:wght@400;500;700&family=Oswald:wght@500;700&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
```

### 字号层级

| 用途 | 字号 | 字体 |
|------|------|------|
| 超大标题 | 72-84px, line-height: 1.0, weight: 900, letter-spacing: -0.04em | Noto Serif SC |
| 大标题 | 56px, line-height: 1.1 | Noto Serif SC |
| 中标题 | 32px, line-height: 1.2 | Noto Serif SC |
| 正文 | 18-20px, line-height: 1.6 | Inter / Noto Sans SC |
| 辅助信息 | 15-16px, line-height: 1.5 | Inter / Noto Sans SC |
| 元数据/标签 | 13px, letter-spacing: 0.15em, weight: 700, uppercase | Oswald |

### 色彩变量（深色杂志风）

```css
--accent: #e8613a;        /* 橙红色强调 */
--accent-light: #ff6b4a;  /* 浅强调色 */
--bg: #1a1a1a;            /* 深色背景 */
--bg-card: #222222;        /* 卡片背景 */
--text: #f0ece4;          /* 主文字（暖白） */
--muted: #888888;         /* 次要文字 */
--divider: rgba(255,255,255,0.08); /* 分割线 */
```

### 卡片框架（深色风格）

```css
.card {
  width: 900px;
  background: var(--bg);
  padding: 48px 50px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 28px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.6);
}
```

- 无噪点纹理 — 保持深色背景干净现代
- 左侧可加竖向强调条：`border-left: 5px solid var(--accent)`

### 移动端适配

```css
@media (max-width: 600px) {
  .card { padding: 28px 22px; }
  .main-title { font-size: 42px; }
  .grid-2 { grid-template-columns: 1fr; }
  .grid-cell { margin-bottom: 12px; }
  .card-num { font-size: 44px; }
}
```

### 内容布局模式

**2栏网格（一般内容）：**
```css
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
}
.grid-cell {
  padding: 24px 28px;
  border: 1px solid var(--divider);
  border-radius: 2px;
  background: var(--bg-card);
}
/* 每个卡片：编号（超大数字） + 标题（粗体衬线） + 描述 */
.card-num {
  font-family: 'Oswald', sans-serif;
  font-size: 60px;
  font-weight: 700;
  color: var(--accent);
  line-height: 1;
  margin-bottom: 6px;
}
.card-title {
  font-family: 'Noto Serif SC', serif;
  font-size: 22px;
  font-weight: 900;
  color: var(--text);
  margin-bottom: 8px;
}
.card-desc {
  font-size: 14px;
  line-height: 1.6;
  color: var(--muted);
}
```

**3栏网格（高密度）：**
```css
.concept-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
}
.concept-item {
  padding: 16px 20px;
  border-top: 3px solid var(--accent);
  background: var(--bg-card);
}
```

---

## 输出格式

1. 先输出 1 句话分析：「分析：高/中/低信息密度 — 采用 X 栏布局」
2. 输出完整 HTML（含 CSS）
3. 用 draw.io MCP 或 screenshot.py 导出 PNG

## HTML 文件命名

使用 kebab-case，英文优先：`coding-agent-components.html`

## 移动端自检

生成后确认：正文文字在 600px 以下屏幕能否一眼看清。网格栏自动切换为单栏。

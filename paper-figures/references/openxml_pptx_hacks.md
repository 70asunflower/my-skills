# python-pptx 底层 OpenXML DrawingML 高级控制速查

`python-pptx` 库提供了对常见 PPT 形状和文本的基本操作，但其高层 API 缺乏对**中文字体声明、圆角精细控制、阴影移除、透明遮罩**的直接支持。在制作高精度的学术海报与可编辑矢量图表时，必须通过 `shape._sp.spPr` 和 `run._r.get_or_add_rPr()` 注入底层 XML。

---

## 一、东亚中文字体强制声明 (`<a:ea>`)

### 痛点
当使用 `run.font.name = "Noto Serif SC"` 时，`python-pptx` 仅在 XML 中生成 `<a:rPr ...><a:latin typeface="Noto Serif SC"/></a:rPr>`。在 Windows Office PowerPoint 中打开时，PowerPoint 对 CJK 中文字符只读取 `<a:ea>` 标签！如果没有该标签，PPT 会静默将中文字体回退为系统默认的“宋体”或“微软雅黑”，导致字体设计完全走样。

### 解决方案
```python
from pptx.oxml import parse_xml

def apply_east_asian_font(run, font_name="Noto Serif SC"):
    """确保中文字符在 PowerPoint 中严格生效"""
    rPr = run._r.get_or_add_rPr()
    # 注入 <a:ea typeface="..."/>
    ea = parse_xml(f'<a:ea xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" typeface="{font_name}"/>')
    rPr.append(ea)
```

---

## 二、形状精细圆角微调 (`<a:gd name="adj" fmla="val ..."/>`)

### 痛点
PowerPoint 默认的 `ROUNDED_RECTANGLE` 的圆角比例参数 `adj` 默认值通常为 `16667`（即短边尺寸的 16.7%）。对于 15cm×20cm 的大卡片，这个圆角非常巨大，呈现出强烈的“移动端手机 App”既视感，缺乏学术排版的端庄与严谨。

### 解决方案
通过重构 `avLst`（Adjust List），将 `adj` 参数压缩至 `2500 ~ 4000`（即 2.5% ~ 4%），获得精致微妙的学术级圆角。

```python
from pptx.oxml import parse_xml

def set_round_radius(shape, adj_val=3000):
    """
    调整圆角矩形的圆弧曲率
    adj_val 推荐范围：
    - 学术正文大卡片：2500 - 3500（微妙克制）
    - 一级标题横幅：3000 - 4000
    - 二级分类胶囊标签：12000 - 25000（半圆胶囊）
    """
    try:
        spPr = shape._sp.spPr
        prstGeom = spPr.find('{http://schemas.openxmlformats.org/drawingml/2006/main}prstGeom')
        if prstGeom is not None:
            avLst = prstGeom.find('{http://schemas.openxmlformats.org/drawingml/2006/main}avLst')
            if avLst is not None:
                avLst.clear()
                gd = parse_xml(f'<a:gd xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="adj" fmla="val {adj_val}"/>')
                avLst.append(gd)
    except Exception as e:
        print(f"Warning setting radius: {e}")
```

---

## 三、强制移除形状投影效果 (`<a:effectLst>`)

### 痛点
某些 PowerPoint 默认母版或预设形状会自动带上模糊的深灰色投影，导致卡片边缘发脏发虚，违背现代学术出版物的扁平化矢量审美（Flat Vector Aesthetics）。

### 解决方案
直接检测并清空形状属性中的 `<a:effectLst>` 节点：

```python
def remove_shadow(shape):
    """彻底剥离阴影，实现干净清爽的扁平学术卡片"""
    try:
        spPr = shape._sp.spPr
        effectLst = spPr.find('{http://schemas.openxmlformats.org/drawingml/2006/main}effectLst')
        if effectLst is not None:
            spPr.remove(effectLst)
    except Exception as e:
        pass
```

---

## 四、文本框物理内边距清零 (Zero Textbox Margins)

### 痛点
PowerPoint 默认文本框四周带有 `0.1 inch` (约 7.2 pt / 2.54 mm) 的隐式内边距。对于严格按厘米计算列宽的学术海报排版，这 5 mm 的宽度吞噬会导致预想中正好排满一行的文字提前触发折行，进而引发**单个句号或分号掉落到下一行首（孤悬标点）**。

### 解决方案
所有新建文本框必须强制四向清零：

```python
def configure_text_frame(tf, word_wrap=True):
    """清空默认边距，保证排版计算绝对精准"""
    tf.word_wrap = word_wrap
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
```

---

## 五、下标与上标 OpenXML 设置

在学术正文或公式、化学分子式、脚注中，若需要设置下标（如 $H_2O$、Jetson Thor 模组 $t_0$）：

```python
def set_subscript(run):
    """设置字元下标偏移"""
    rPr = run._r.get_or_add_rPr()
    rPr.set("baseline", "-25000")

def set_superscript(run):
    """设置字元上标偏移"""
    rPr = run._r.get_or_add_rPr()
    rPr.set("baseline", "30000")
```

---

## 六、标准学术卡片复合工厂函数

将上述四项技术封装为可复用的工厂函数：

```python
def create_academic_card(slide, left, top, width, height, 
                         bg_color, border_color=None, line_width_pt=0.75, radius_adj=3000):
    """快速构建完全符合学术印刷标准的圆角扁平卡片"""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = Pt(line_width_pt)
    else:
        shape.line.fill.background()
    set_round_radius(shape, radius_adj)
    remove_shadow(shape)
    return shape
```

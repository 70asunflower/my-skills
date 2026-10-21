# 科研数据真实性与统计图例契约（Statistical Integrity Contract）

顶级期刊（Nature、Science、Cell、IEEE）对于数据篡改、误导性可视化与不完备统计陈述有极其严格的审查机制。本规范定义了科研绘图中的五大数据诚信硬法则与标准化图注结构。

---

## 一、五大统计诚信硬法则（Hard Rules）

### 1. 【柱状图零基准硬铁律】（Zero-Origin Baseline Rule）
- **违规痛点**：为了夸大组间差异，将柱状图（Bar Chart）的 Y 轴截断（如从 95% 起始，将 96% 和 99% 画出两倍差距）。此举在顶刊审稿中被视为严重误导行为（Misleading Visualization）；
- **执行准则**：**所有表达绝对数值量级或比例的柱状图，Y 轴底端必须从 0 开始！**
- **例外处理**：若要展示微小波动（如高精度时钟漂移、晶圆折射率），应使用**带点折线图（Line with Points）或箱线图（Boxplot）**，并在坐标轴处显式标注断轴符号 `//`。

### 2. 【原始数据散点叠加】（Show the Raw Data Rule）
- **违规痛点**：仅绘制“柱子 + 误差线”（Bar of Shame），掩盖了样本量不足、双峰分布或严重离群点；
- **执行准则**：在样本量 $n \le 50$ 的生物、材料与工程实验对比中，柱状图或箱线图上方**必须叠加半透明抖动真实散点**（Jittered Scatter / Strip Plot），让审稿人亲眼看见每一个独立样本的分布真实性。

### 3. 【误差线严格声明】（Error Bar Specification）
在图注与图表中严禁出现无定义的误差线。必须在图注中显式声明：
- **SD (标准差，Standard Deviation)**：反映数据的离散程度（适用于展示总体变异）；
- **SEM (标准误，Standard Error of the Mean)**：反映均值的抽样精度（常用于生物学对比）；
- **95% CI (置信区间)**：反映总体均值落在区间的置信概率。
- 绝不可混淆 SD 与 SEM，且必须声明中心线是**均值（Mean）还是中位数（Median）**。

### 4. 【统计显著性星号标准】（Significance Asterisk Protocol）
星号标注必须遵循国际学术通用单调规范，并在图注中完整声明：
- $\text{ns}$ (not significant, $P \ge 0.05$)
- $* \quad P < 0.05$
- $** \quad P < 0.01$
- $*** \quad P < 0.001$
- 必须在图注中明确指出使用的统计检验方法（如：“Two-tailed unpaired Student's $t$-test” 或 “One-way ANOVA with Tukey's post-hoc test”）。

### 5. 【数据断言双向一致性】（Claim-Evidence Alignment）
论文正文中的文字断言（如“性能提升 2.3 倍”、“故障率降低 45%”）必须与对应图表上的标高差或计算值 **100% 吻合**。

---

## 二、标准化图注素材库（`fig<N>_<slug>_notes.txt` 规范）

每张定稿图必须配套生成同名 `_notes.txt`，作为图注（Legend）与正文论述的素材源头：

```text
======================================================================
Figure 1 Notes: In-Situ Space Radiation Telemetry & Self-Healing Pipeline
======================================================================

1. BOLD TAKEAWAY SENTENCE (核心结论句)
Figure 1. Tri-fold orthogonal cold-power-cycling enables autonomous 
sub-10s recovery of satellite edge accelerators under heavy-ion radiation.

2. PANEL-BY-PANEL BREAKDOWN (逐子图详述)
(a) Schematic of the radiation beam line setup and in-situ telemetry monitoring.
(b) Real-time current transient during latchup event (t = 142.3 s).
(c) Statistical distribution of recovery times across N = 24 radiation trials.
(d) Comparative availability score between conventional watchdog and proposed pipeline.

3. STATISTICAL DETAILS & CONDITIONS (统计口径与实验环境)
- Sample Size: N = 24 independent radiation exposure cycles.
- Center and Dispersion: Data points represent Mean ± SD.
- Statistical Test: Two-tailed unpaired Student's t-test (*P < 0.05, **P < 0.01, ***P < 0.001).
- Beam Condition: 100 MeV/u Kr heavy ion beam, flux = 1.0e4 ions/cm2/s.

4. HONEST BOUNDARIES & EXCLUSIONS (诚实边界与例外声明)
- Excluded run #7 due to accelerator facility beam drop; documented in supplementary log.
- Raw CSV files archived under: /data/radiation_2026/run_01_24.csv
======================================================================
```

# Mica 视觉规范（Visual Identity）

> **Otter Workbench** — 一个温暖但克制、专业但不冷峻的内部采购工具。
>
> 本文件是 Mica 前端所有视觉决策的「宪法」。修改前端样式 / 颜色 / 间距 / 字体 / 组件外观时，必须查这一份。新加 Token 也要登记到这里。

**适用范围**：`frontend/src/` 下的所有 React 代码 + AntD 主题配置 + 图表配色。

**读者**：

1. 人类工程师 — 改前端时的对照标尺
2. AI coding agent（Claude / Cursor / Sisyphus-Junior）— `task(load_skills=[...])` 时连同此文件一起喂给子代理

**配套文件**：

- [`AGENTS.md`](../AGENTS.md) §5.8 前端主题约定
- `frontend/src/theme/tokens.ts` — Token 单一事实源
- `frontend/src/theme/antdTheme.ts` — AntD 主题映射
- `frontend/src/styles/global.css` — CSS variables + print + 响应式

---

## 0. 一页摘要（At a Glance）

### 一句话定位

> Mica 是 **a warm-bronze workbench for procurement teams** — 一个像账册（ledger）一样可读的采购工具：温暖的纸色画布、紧字距的 Inter、所有业务编号都用等宽字体、Otter Brown 严格保留给主操作。

### 五条铁律（Five Iron Rules — 不可违反）

1. **单一品牌色纪律**（Single Accent）— Otter Brown 只用于 Primary CTA / 选中态 / chart 主指标，**不做装饰、不做边框、不做大面积底色**
2. **Mono 字体专属业务标识符**（Mono for Identifiers）— PR/PO/合同号 / 金额 / 数量 / 日期 / SKU code / 邮箱 全部强制用 JetBrains Mono + `tabular-nums`
3. **底色分层优先于阴影**（Surfaces over Shadows）— Paper Beige 画布 + 白卡 + 1px hairline 形成层级，阴影压到几乎不可见
4. **Inter 紧字距**（Compressed Tracking）— 字号越大，字距越紧。display 30px → `-0.025em`，body 14px → 0
5. **密集优先于呼吸感**（Compact Density）— B 端工具的奢侈不是大留白，是**信息层级清晰**。section gap ≤ 32px，不学营销页的 80px

### Quick Token Reference

```text
画布 (Canvas)         #FAFAF8   Paper Beige
卡片 (Card)           #FFFFFF   Pure White
主品牌色 (Primary)    #8B5E3C   Otter Brown 500
正文 (Text Primary)   #1F1C19   Ink
次文 (Text Secondary) #4F4943   Graphite
辅助 (Text Tertiary)  #8F8881   Slate
边线 (Hairline)       #E8E4DF   Hairline Beige
```

---

## 1. 设计哲学

### 1.1 命名："Otter Workbench"

「Otter」沿用 Mica 的水獭 DNA — 这是 Mica 与所有 fintech / SaaS 工具的差异化资产，**不可放弃**。
「Workbench」明确身份 — 这是工程师 / 采购员每天用 8 小时的工作台，不是营销官网，不是 KPI 大屏。

### 1.2 三句话定位

1. **专业不冷峻** — 比 Brex 多一点温度（暖纸底 + 水獭吉祥物），比 SAP 少十倍冰冷（去掉企业级蓝灰深）
2. **密集不嘈杂** — 一屏放下 50 行 PR / 8 个 KPI / 3 张图表，但不靠堆砌颜色，靠字距、行高、tabular-nums
3. **效率不极简** — 我们不是 Linear / Vercel 的极客感，是面向"每天处理 10 个 PR 的采购员"的人体工学

### 1.3 与其他 B 端工具的差异化

| 维度 | SAP / Oracle | Linear / Vercel | Brex / Ramp | **Mica** |
|---|---|---|---|---|
| 调性 | 企业级冷峻 | 极客冷感 | 金融精密 | **温暖精密** |
| 画布 | 灰白 + 蓝色 | 近黑 | 纯白 | **Paper Beige** |
| 强调色 | 多色滥用 | 1 acid lime | 1 ember | **1 otter brown** |
| 装饰 | 图标多 + 渐变 | 完全无 | UI mockup | **水獭插画 + UI 卡** |
| 字体 | 系统字体 | Inter Variable | Inter / Flecha | **Inter + JBM** |
| 信息密度 | 中（表单冗长） | 高（compact） | 中（spacious） | **高（compact）** |

---

## 2. 五条铁律详解

### ① Single Accent Discipline（Otter Brown 用法纪律）

**Otter Brown `#8B5E3C` 只能用在以下场景**：

✅ 允许使用：

- Primary Button 填充背景（`<Button type="primary">`）
- 侧边栏选中菜单的背景 / 文字色
- Tab 选中态的下划线 / 文字色
- Checkbox / Radio / Switch 选中态
- Progress Bar 进度填充
- Chart 主指标线条（如「本月 PR 总额」趋势线）
- Status Badge `state-progress` 状态（处理中 / partially_converted）
- 链接文字（限定在重点链接，例如"查看详情"）

❌ 禁止使用：

- 卡片底色 / 大面积填充
- 装饰性边框 / 分隔线
- 普通文本超链接（用 `text.primary` + 下划线）
- 图标默认色（用 `text.secondary`）
- Tag 默认色（用各自语义色）
- Hover 装饰（用 surface 微变色，不要染主品牌色）

**为什么**：Otter Brown 是 Mica 的「身份信号」。当一屏出现 30 个褐色元素时，这个信号被稀释，用户看不到「这才是该点的按钮」。学 Brex 的 Ember `#ff5900`、Linear 的 Acid Lime `#e4f222` —— 一屏只允许 1-3 个褐色元素。

### ② Mono for Identifiers（业务标识符必须等宽）

**所有以下字段必须使用 `JetBrains Mono` + `font-variant-numeric: tabular-nums`**：

| 字段类型 | 例子 | 实现 |
|---|---|---|
| 业务编号 | `PR-2026-0017` `PO-2026-0019` `RFQ-2026-0003` `INV-2026-0042` | `<code class="mono-id">` |
| 金额 | `¥1,054,197.00` `$25,000.00` | `<span class="mono-num">` |
| 数量 + 单位 | `64 EA` `1024 GPU` | `<span class="mono-num">` |
| 日期时间戳 | `2026-06-22 09:43` | `<span class="mono-num">` |
| SKU code | `MBP16-M4PRO` `H100-80G` | `<code class="mono-id">` |
| 邮箱 / 手机 | `alice@company.com` `13800138000` | `<span class="mono-num">` |
| 状态码 / Tax ID | `PASS-2026-001` `91110000xxxxxxxxxx` | `<code class="mono-id">` |

**例外**（不用 Mono）：

- 自然语言文本中的金额（如审批通知的"本单合计 ¥10,000，请审批"—— 此处用 Inter 即可，因为是叙述）
- 用户姓名 / 部门名称 / 公司名称 / 物料中文名（这些是语言不是标识符）

**为什么**：

1. **数字对齐**：列表里 `¥1,054,197` 和 `¥12,500` 在 tabular-nums 下个位、十位、百位完美对齐，眼睛扫读速度 +30%
2. **ID 不易看错**：`PR-2026-0017` 和 `PR-2026-O017`（O vs 0）在 mono 下立刻区分
3. **工具感信号**：mono 字体是「这是工具不是营销页」的最强视觉信号（Linear / Stripe / GitHub 都这样做）

### ③ Surfaces over Shadows（底色分层优先）

**层级建立顺序（从弱到强）**：

1. **画布 vs 卡片**：Paper Beige `#FAFAF8` 画布 + Pure White `#FFFFFF` 卡片，已经形成主层级
2. **1px hairline border**：`#E8E4DF` 极淡边线，在密集列表里区分行 / 区分卡
3. **微阴影（带 Otter Brown 微染）**：`0 1px 2px rgba(139, 94, 60, 0.04)` — 仅在 modal / dropdown / popover 等"浮起"元素使用
4. **强阴影**：仅 modal mask + 全屏 overlay 使用，业务卡片绝不允许

**禁止**：

- AntD 默认的 `boxShadow: 0 1px 2px rgba(0, 0, 0, 0.1)`（纯黑、过深，破坏 Paper Beige 氛围）
- 多层 shadow stack（B 端工具不需要 Material Design 那种 6 级 elevation）
- 卡片 hover 时叠加阴影（用 hairline 颜色变化或微背景色变化代替）

**为什么**：纯黑阴影在暖纸底上会显得"廉价"。带 Otter Brown 微染的阴影让整页氛围统一、品牌化。学 Column 的 `rgba(17, 26, 74, 0.1)` 蓝染阴影。

### ④ Compressed Inter Tracking（紧字距规则）

**字号越大，字距越紧**：

| 字号 | letter-spacing | 应用 |
|---|---|---|
| 30px (display) | `-0.025em` | StatCard 大数字、PageHeader 主标题、登录页 hero |
| 24px (h) | `-0.02em` | 区块标题、Modal 标题 |
| 18px (h-sm) | `-0.015em` | 卡片标题 |
| 16px (sub) | `-0.01em` | 表单字段标题、列表行主文 |
| 14px (body) | `-0.005em` | 默认正文 |
| 13px (body-sm) | `0` | Tag、辅助说明 |
| 12px (caption) | `0` | 元信息、版权 |

**为什么**：Inter 在大字号时默认字距偏松，看起来像营销 hero。负字距让标题"工程化、密实"，与 Brex / Linear / Stripe 等成熟工具调性一致。CSS 写法：

```css
.h-display { font-size: 30px; letter-spacing: -0.025em; line-height: 1.15; }
```

### ⑤ Compact Density（密集优先）

| 间距类型 | 数值 | 应用 |
|---|---|---|
| Section gap | 24-32px | 页面区块之间（不是 80px） |
| Card padding | 16px (列表卡) / 24px (详情卡) | 比 Brex 的 32px 紧 |
| Element gap | 8-12px | 表单字段、按钮间 |
| Row height (table) | 40px | 列表表格（不是 56px） |
| Form item margin-bottom | 16px | 表单字段间 |

**为什么**：Mica 是密集业务系统，一个 PR 详情页要塞下：基本信息 + 物料 8 行 + 审批链 + 履约链 + 活动日志。如果学 Brex 的 80px section gap，这一屏要往下滚 4 屏。Linear 的 compact density 才是 B 端工具该学的。

---

## 3. 配色系统

### 3.1 Brand Palette（Otter Brown）

完整 11 阶色板（保留现有，不变）：

```ts
primary: {
  50:  '#F8F4F1',  // 极浅，用于 selected 行 hover
  100: '#EBE1D8',  // 浅，用于 selected 菜单项底色
  200: '#D8C3B1',  // 标签 / 浅边
  300: '#C4A48A',  // 浅强调
  400: '#B18563',  // 中等强调（图表辅助色）
  500: '#8B5E3C',  // ★ Base — 唯一的"品牌色"
  600: '#704B30',  // hover 态
  700: '#543824',  // active 态
  800: '#382518',  // 深底色
  900: '#1C130C',  // 极深，dark mode 选中底
}
```

**关键应用**：

- `primary.500` — Primary Button、菜单选中 text、tab 下划线
- `primary.50` — 菜单选中 background（极浅褐色高亮）
- `primary.100` — Tag `state-progress` 的 background
- `primary.700` — Primary Button hover/active

### 3.2 Neutral Palette（Paper Beige 系）

**关键改动**：默认背景从 `#FFFFFF` 改为 `#FAFAF8`（Paper Beige）。

```ts
neutral: {
  0:   '#FFFFFF',  // Pure White — 仅卡片表面
  25:  '#FAFAF8',  // ★ Paper Beige — 页面默认画布（新增）
  50:  '#F7F6F5',  // Subtle Beige — 卡片内的浅区块
  100: '#EFECE9',  // Sunken — 输入框 disabled / 浅分隔
  200: '#DFDBD7',  // Border default（旧）
  // 200 移除使用 — 改用 hairline 250
  250: '#E8E4DF',  // ★ Hairline Beige — 主要边线色（新增）
  300: '#CFCAC5',  // Border strong / disabled text
  400: '#AFA9A3',  // Tertiary border
  500: '#8F8881',  // Slate — Tertiary text
  600: '#6F6861',  // Steel — placeholder
  700: '#4F4943',  // Graphite — Secondary text
  800: '#2F2B27',  // Carbon — Strong border on dark
  900: '#1F1C19',  // Ink — Primary text
  950: '#0F0E0D',  // Onyx — dark mode canvas
}
```

**Token 映射**：

```ts
text: {
  primary:   neutral[900],  // #1F1C19  正文
  secondary: neutral[700],  // #4F4943  次文（详情页字段值）
  tertiary:  neutral[500],  // #8F8881  辅助说明
  disabled:  neutral[300],  // #CFCAC5
  placeholder: neutral[600], // #6F6861
}

surface: {
  bg:       neutral[25],  // #FAFAF8  ★ Paper Beige 画布
  card:     neutral[0],   // #FFFFFF  卡片
  subtle:   neutral[50],  // #F7F6F5  卡片内区块
  sunken:   neutral[100], // #EFECE9  输入框 / 表头
}

border: {
  hairline: neutral[250], // #E8E4DF  ★ 主要边线
  default:  neutral[300], // #CFCAC5  强边线（极少用）
  strong:   neutral[400], // #AFA9A3  分隔重点区块
}
```

### 3.3 State Tokens（6 个语义色）

**当前问题**：Mica 的 PR 状态、PO 状态、付款状态用了 10+ 种 AntD 默认色，没有统一规则。

**新规则**：所有业务状态必须映射到下面 6 个 token 之一。

| Token | Color | 应用语义 | 涉及业务状态 |
|---|---|---|---|
| `state-info` | `#3B82F6` | 中性、未开始、计划中 | PR draft、PO draft、payment planned |
| `state-progress` | `#8B5E3C` ★ | **进行中、已提交、处理中** | PR submitted、partial_converted、PO in_transit、approval pending |
| `state-success` | `#22C55E` | 完成、成功、通过 | PR approved、PO converted、payment paid、shipment received |
| `state-warning` | `#F59E0B` | 注意、待跟进、临期 | due_soon、returned、requires_attention |
| `state-error` | `#EF4444` | 错误、失败、超期、异常 | rejected、overdue、cancelled、price_anomaly |
| `state-neutral` | `#8F8881` | 已归档、已废弃、不适用 | archived、obsolete、n/a |

**state-progress 用 Otter Brown 的妙处**：把"进行中"这个最常见的状态绑定到品牌色，让用户一眼识别"这是 Mica 在帮你处理的事"，加强品牌存在感（Mica 50% 以上的状态都是"进行中"）。

**Tag / Badge 渲染规则**：

```css
/* 全部用 outline 风格，不用 solid fill */
.tag-state {
  background: var(--state-color-50);    /* 浅底（10% alpha） */
  color: var(--state-color-700);        /* 深字 */
  border: 1px solid var(--state-color-200); /* 中等边 */
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 12px;
  font-weight: 500;
}
```

→ 不用 AntD 默认的 solid Tag，因为在密集表格里太抢眼。

### 3.4 Data Viz Palette（图表 6 色）

**当前问题**：Recharts 默认蓝绿紫，与 Otter Brown 主题完全不搭，每张图表都是"颜色突兀"。

**新规则**：图表 fill / stroke 只能从下面 6 色中选。按业务语义命名（不是按颜色）。

| Token | Color | 业务语义 | 应用 |
|---|---|---|---|
| `viz-primary` | `#8B5E3C` ★ | 主指标（本期、本月、本部门） | 折线主线、柱状主柱 |
| `viz-secondary` | `#C4A48A` | 对比（上期、上月、对照组） | 第二条线、虚线 |
| `viz-positive` | `#2F8F69` | 正向（已完成、达标） | 绿色饱和度降低后的森林绿 |
| `viz-attention` | `#C97B3F` | 中等关注（进行中、临期） | 暖橙，与 Otter Brown 同色系 |
| `viz-critical` | `#B85450` | 异常（超额、延期、价格异常） | 降饱和的铁锈红 |
| `viz-baseline` | `#6F6861` | 基线（90 天均价、目标线） | 灰色虚线 |

**6 色都做了降饱和处理**，不是 Recharts 默认的"乐高积木彩"。在 Paper Beige 画布上和谐共存。

**多 SKU 趋势图**（v0.6.1+ 已有的 10 色 SKU palette）— 这是唯一例外，因为要区分 10 个不同 SKU。建议未来改为按 viz-primary 的色相 ±15° 的 10 个变体（待 v1.41+ 重构）。

### 3.5 Dark Mode 色阶

**当前问题**：暗色模式背景 `#0F0E0D` 偏纯黑，elevated `#2F2B27` 跳跃太大。

**新规则**：学 Linear 的 4 步暗色阶（差距小、靠 hairline 分层）：

```ts
dark: {
  canvas:   '#161514',  // ★ Onyx — 微暖偏褐的"近黑"，不是 #000
  nav:      '#1A1816',  // Charcoal — sidebar / header
  card:     '#1F1D1B',  // Card — 卡片背景
  subtle:   '#26221F',  // Subtle — 卡片内区块
  hairline: '#2F2B27',  // ★ 主要边线（暗）
  border:   '#3A3632',  // 强边线
}
```

**关键**：`canvas → nav → card → subtle` 四层，每层差距很小，靠 1px hairline border 区分。绝不靠"亮度跳一大段"做 elevation。

### 3.6 Dark Mode State & Viz 覆盖（v1.49.0）

亮模式的 State Tokens（`success-50/200/500/700`）是高饱和色对（`#F0FDF4` + `#15803D` 等），适合纸色画布。直接搬到暗色画布会"晃眼"：浅绿背景在 Onyx 上反而显眼到刺人。

**暗模式 state 重映射规则**：

```css
[data-theme="dark"] {
  /* tag-state 背景：18% / 14% alpha 的语义色，而不是 #50 浅纯色 */
  --color-state-success-50: rgba(34, 197, 94, 0.14);   /* 不是 #F0FDF4 */
  --color-state-success-200: rgba(34, 197, 94, 0.32);
  --color-state-success-500: #4ADE80;                  /* 提亮 +1 阶 */
  --color-state-success-700: #86EFAC;                  /* 文字提到 #200~#300 */
}
```

- **背景**: 浅色 50 → 暗色 14% alpha 的同色（保留色相，不再发光）
- **边框**: 浅色 200 → 暗色 32% alpha 同色
- **文字 / dot**: 浅色 700（深色文字）→ 暗色 200/300（浅色文字，保证 4.5:1 对比）

Same for `info / progress / warning / error / neutral`. 这套规则确保 `tag-state--success`、`status-badge--success`、Tag、Badge 在暗模式下"读得清但不刺眼"。

**Viz 暗色覆盖**（图表组件）：

```css
[data-theme="dark"] {
  --color-viz-positive: #4ADE80;  /* 亮色 #2F8F69 → 暗色提亮 */
  --color-viz-critical: #F87171;  /* 亮色 #B85450 → 暗色提亮 */
  --color-viz-attention: #FBBF24;
  --color-viz-grid: #2F2B27;       /* hairline 同色 */
  --color-viz-axis-text: #9E9790;  /* tertiary text */
  --color-viz-today-bg: rgba(177, 133, 99, 0.14);
}
```

**AntD ComponentToken 暗色覆盖**：`Modal / Drawer / Select / Dropdown / Tag / Tooltip / Popover` 在 `darkTheme.components` 里都必须显式重写 `headerBg / contentBg / colorBgElevated / optionSelectedBg / colorBgSpotlight` 等 — 因为 baseTheme 把它们硬编码到 `tokens.color.surface.light.*`，darkAlgorithm 不会自动覆盖 componentToken。

> 这是 v1.49.0 修复的核心 — 在此之前，整页 Drawer / Modal 在暗模式下白底白字。

---

## 4. 字体系统

### 4.1 Inter（UI 主字体）

```css
font-family: 'Inter', -apple-system, BlinkMacSystemFont,
             'PingFang SC', 'Microsoft YaHei', sans-serif;
```

**已加载字重**：400 / 500 / 600 / 700。
**字重使用约束**（学 Brex 的 3 级）：

- `400` — 正文（body / caption）
- `500` — UI 强调（按钮、菜单、标签、表单 label、列表行主文）
- `600` — 标题（h-sm / h / display）
- ❌ `700` — **禁止**（过粗破坏精密感，全站零使用）

### 4.2 JetBrains Mono（业务标识符）

```css
font-family: 'JetBrains Mono', ui-monospace, 'Cascadia Code', Consolas, monospace;
```

**字重**：仅 `400`。
**Open Type Features**：

```css
font-feature-settings: 'tnum' 1, 'zero' 1, 'ss19' 1;
font-variant-numeric: tabular-nums;
```

- `tnum` — tabular-nums（等宽数字，列对齐用）
- `zero` — slashed zero（区分 0 和 O）
- `ss19` — JBM 的简化变体（`6` `9` 不带尾巴，更紧凑）

**Utility Class 定义**：

```css
.mono-id {
  font-family: var(--font-mono);
  font-size: 0.95em;        /* 比正文略小 */
  letter-spacing: 0;
  font-feature-settings: 'tnum' 1, 'zero' 1, 'ss19' 1;
  background: transparent;
  color: inherit;
}

.mono-num {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum' 1, 'zero' 1;
  /* 表格金额列必须右对齐 */
}

.mono-num--right { text-align: right; }
```

### 4.3 Type Scale（8 步 × 3 字重）

**8 个固定字号 token，禁止使用其他值**：

| Token | Size | Weight | Line Height | Tracking | 应用场景 |
|---|---|---|---|---|---|
| `caption` | 12px | 400 | 1.5 | 0 | 元信息、时间戳、版本号、状态机说明 |
| `body-sm` | 13px | 400 | 1.5 | 0 | Tag、表格次要列、辅助说明 |
| `body` | 14px | 400 | 1.5 | -0.005em | **默认正文**、表格主列、表单值 |
| `body-em` | 14px | 500 | 1.5 | -0.005em | 列表行标题、强调正文 |
| `sub` | 16px | 500 | 1.4 | -0.01em | 表单字段 label、卡片次标题 |
| `h-sm` | 18px | 600 | 1.3 | -0.015em | 卡片标题、Tab 标题 |
| `h` | 24px | 600 | 1.2 | -0.02em | 区块标题、Modal 标题 |
| `display` | 30px | 600 | 1.15 | -0.025em | 页面主标题、StatCard 主数字 |

**禁止字号**：15px、17px、20px、22px、28px、36px。这些都不在 token 里。

**Why 14px not 16px 默认正文**：B 端密集型工具行业惯例（Linear / Notion / GitHub / Figma 都是 13-14px），16px 会把表格撑大一倍信息密度减半。

### 4.4 tabular-nums 全站规则

**Body 也启用 tabular-nums**（关键优化）：

```css
body {
  font-feature-settings: 'tnum' 1;  /* 全站数字等宽 */
}
```

→ 即使是 Inter 字体，开启 tnum 后所有数字字符宽度一致，表格金额自动对齐。配合 mono 用于 ID 字段，达到"工业级 ledger"质感。

---

## 5. 形状 & 阴影

### 5.1 三档圆角（强声明）

**全站只允许 4 个 radius 值**：

| Token | Value | 应用 |
|---|---|---|
| `radius-sm` | `4px` | Tag、Badge、内嵌 chip、状态点 |
| `radius-md` | `8px` | Button、Input、Select、DatePicker |
| `radius-lg` | `12px` | Card、Modal、Drawer、Dropdown、Popover |
| `radius-pill` | `9999px` | Avatar、极少数 status pill |

**禁止值**：6px、10px、14px、16px、20px。AntD 默认的 6px 必须 override 为 8px。

### 5.2 Brand-tinted Shadow（品牌微染阴影）

```css
/* 阴影颜色用 Otter Brown 微染（rgba(139, 94, 60, ...）），不是纯黑 */
--shadow-card: 0 1px 2px rgba(139, 94, 60, 0.04);
--shadow-card-hover: 0 2px 6px rgba(139, 94, 60, 0.08);
--shadow-floating:
  0 4px 12px rgba(139, 94, 60, 0.08),
  0 1px 3px rgba(139, 94, 60, 0.04);
--shadow-modal:
  0 16px 48px rgba(139, 94, 60, 0.12),
  0 4px 12px rgba(139, 94, 60, 0.06);
--shadow-button-hover: 0 2px 4px rgba(139, 94, 60, 0.10);

/* Dark mode 用纯黑阴影 + 边框微提亮 */
--shadow-card-dark: 0 1px 2px rgba(0, 0, 0, 0.2);
```

**应用层级**：

| 元素 | 阴影 |
|---|---|
| 普通业务卡片 | `none` 或 `shadow-card`（几乎不可见） |
| 卡片 hover | `shadow-card-hover` |
| Dropdown / Popover | `shadow-floating` |
| Modal / Drawer | `shadow-modal` |
| Primary Button | `none`（靠填色） |
| Primary Button hover | `shadow-button-hover` |

### 5.3 Hairline Border 作为主要分层

```css
.card {
  background: var(--surface-card);     /* #FFFFFF */
  border: 1px solid var(--border-hairline); /* #E8E4DF */
  border-radius: var(--radius-lg);     /* 12px */
  /* 默认无 shadow，hover 时才显现微 shadow */
}

.card:hover {
  border-color: var(--neutral-300);
  box-shadow: var(--shadow-card-hover);
}
```

**列表表格分隔**：

- 表头底边 `1px solid hairline`
- 行间分隔 `1px solid hairline`（极淡）
- hover 行 `background: var(--neutral-25)`（即 Paper Beige 微深）

---

## 6. 间距 & 密度

### 6.1 间距 Token

```ts
space: {
  0: 0,
  1: 4,
  2: 8,
  3: 12,
  4: 16,
  5: 24,
  6: 32,
  7: 48,
  8: 64,
}
```

保留现有间距 token，**不新增**。

### 6.2 密度规则（B 端 compact）

| 场景 | 间距 | 备注 |
|---|---|---|
| Section gap（区块间） | `space-5` (24px) | 详情页 ≤ `space-6` (32px) |
| Card padding（详情卡） | `space-5` (24px) | 表单区域可 `space-4` (16px) |
| Card padding（列表卡） | `space-4` (16px) | 移动端可 `space-3` (12px) |
| Form item gap | `space-4` (16px) | margin-bottom |
| Form field internal gap | `space-2` (8px) | label 与 input |
| Button group gap | `space-2` (8px) | 操作按钮组 |
| Tag gap | `space-1` (4px) | 多个 tag 排列 |
| Table row height | 40px | 列表（compact）；详情可 48px |
| Table cell padding-x | 12px | 不是 AntD 默认的 16px |

**响应式断点**（保留现有）：

```ts
breakpoint: { xs: 480, sm: 576, md: 768, lg: 992, xl: 1200, xxl: 1600 }
```

---

## 7. 组件视觉规范（12 个核心组件）

### 7.1 Button

**Primary Button**（主操作 — 一屏只允许 1-2 个）：

- 背景 `Otter Brown 500 #8B5E3C`
- 文字 `Pure White #FFFFFF`，font-weight 500
- `radius-md` 8px、padding `8px 16px`、height 36px
- 无 border、无 shadow（rest 态）
- Hover：`Otter Brown 600 #704B30` + `shadow-button-hover`
- Active：`Otter Brown 700 #543824`
- Disabled：`neutral-200` 底 + `neutral-400` 字

**Default Button**（次要操作）：

- 背景 `transparent`、border `1px solid neutral-300`、文字 `text-primary`
- font-weight 500
- Hover：border `neutral-400` + 微底色 `neutral-50`
- 不要给 default button 用 Otter Brown border（违反铁律 ①）

**Text Button / Link**：

- 背景 transparent、border 无、文字 `text-primary` + 下划线
- Hover：文字色不变，下划线加重
- 仅对"查看详情"等强意图链接才允许文字色 `Otter Brown 600`

**Danger Button**（删除 / 拒绝）：

- 背景 `state-error #EF4444`、文字白
- Hover：变深 + 微 shadow

**禁止**：

- pill 按钮（`radius-pill`）— 不符合工具调性
- 渐变底色
- 大于 600 的字重
- shadow 在 rest 态可见

### 7.2 Card

```css
.card {
  background: #FFFFFF;
  border: 1px solid #E8E4DF;       /* hairline */
  border-radius: 12px;             /* radius-lg */
  padding: 24px;                   /* 详情卡 / 16px 列表卡 */
  box-shadow: none;                /* 默认无阴影 */
}

.card-header {
  font-size: 18px;                 /* h-sm */
  font-weight: 600;
  letter-spacing: -0.015em;
  color: #1F1C19;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #E8E4DF;
}
```

**禁止**：

- AntD 默认的 `boxShadow: 0 1px 2px rgba(0,0,0,0.05)` 黑染阴影
- 卡片之间用 margin 大间距营造"漂浮"感（用 hairline + Paper Beige canvas 自然分层）

### 7.3 Tag

```css
.tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 4px;              /* radius-sm */
  font-size: 12px;                 /* caption */
  font-weight: 500;
  line-height: 1.4;
  border: 1px solid;
  /* color/bg/border 由 state 决定 */
}
```

**6 个 state 变体**（参见 §3.3 State Tokens）：

```css
.tag-info     { bg: #EFF6FF; color: #1D4ED8; border-color: #BFDBFE; }
.tag-progress { bg: #F8F4F1; color: #543824; border-color: #D8C3B1; } /* Otter Brown */
.tag-success  { bg: #F0FDF4; color: #15803D; border-color: #BBF7D0; }
.tag-warning  { bg: #FFFBEB; color: #B45309; border-color: #FDE68A; }
.tag-error    { bg: #FEF2F2; color: #B91C1C; border-color: #FECACA; }
.tag-neutral  { bg: #F7F6F5; color: #4F4943; border-color: #DFDBD7; }
```

**禁止**：solid filled tag（深底白字）— 在密集表格里过于抢眼。

### 7.4 Status Badge（状态点）

带圆点的状态显示（用于 PR / PO 列表的"状态"列）：

```jsx
<span class="status-badge status-progress">
  <span class="status-dot"></span>
  审批中
</span>
```

```css
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 9999px;
  background: var(--state-color-500);
  display: inline-block;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--state-color-700);
  /* 无 background、无 border */
}
```

→ 比 Tag 更轻，用于密集表格的状态列（一屏 50 行不会视觉嘈杂）。

### 7.5 Table

```css
.table {
  font-size: 14px;
  background: #FFFFFF;
}

.table thead th {
  background: #F7F6F5;             /* subtle */
  border-bottom: 1px solid #E8E4DF;
  padding: 10px 12px;
  font-size: 13px;                 /* body-sm */
  font-weight: 500;
  color: #4F4943;                  /* secondary */
  letter-spacing: 0;
}

.table tbody td {
  padding: 10px 12px;
  border-bottom: 1px solid #E8E4DF;
  height: 40px;                    /* compact row */
  vertical-align: middle;
}

.table tbody tr:hover {
  background: #FAFAF8;             /* paper beige hover */
}
```

**关键规则**：

- 数字列必须右对齐 + `mono-num` class
- ID 列 / SKU 列必须 `mono-id` class
- 行 hover 用 Paper Beige，不要用 `primary-50`（避免褐色泛滥）
- 表格 ≥ 100 行时启用虚拟滚动（Mica 已有 ProTable / VirtualTable 方案）

### 7.6 Form / Input

```css
.input {
  height: 36px;
  padding: 0 12px;
  border: 1px solid #DFDBD7;
  border-radius: 8px;              /* radius-md */
  background: #FFFFFF;
  font-size: 14px;
  color: #1F1C19;
}

.input::placeholder { color: #6F6861; }

.input:hover { border-color: #C4A48A; }     /* primary-300 */
.input:focus {
  border-color: #8B5E3C;            /* primary-500 */
  box-shadow: 0 0 0 3px rgba(139, 94, 60, 0.10);  /* focus ring */
  outline: none;
}

.input:disabled {
  background: #F7F6F5;
  color: #8F8881;
  cursor: not-allowed;
}
```

**Form Item Layout**：

- label 在上、input 在下，label 用 `sub` (16px / 500)
- 必填标记 `*` 用 `state-error` 色
- 错误提示在 input 下方，用 `caption` (12px / 400) + `state-error` 色
- helper text 在 input 下方，用 `caption` + `text-tertiary`

### 7.7 Select

复用 `.input` 样式，下拉指示用 `text-tertiary` 色 `▼` 图标。

下拉面板：

- `radius-lg` 12px、`shadow-floating`、`border: 1px solid hairline`
- 选项 hover：`background: neutral-50`
- 选项 selected：`background: primary-50` + `color: primary-700`
- 选项 padding：`8px 12px`、字号 `body` (14px)

### 7.8 PageHeader（页面主标题区）

每个页面顶部的标题 + 操作按钮区：

```jsx
<PageHeader>
  <Title>采购订单详情</Title>
  <SubTitle><code class="mono-id">PO-2026-0019</code></SubTitle>
  <Description>2026-06-22 由 alice 创建</Description>
  <Actions>
    <Button>导出 PDF</Button>
    <Button type="primary">提交审批</Button>
  </Actions>
</PageHeader>
```

```css
.page-header-title {
  font-size: 24px;                 /* h */
  font-weight: 600;
  letter-spacing: -0.02em;
  color: #1F1C19;
  line-height: 1.2;
}

.page-header-subtitle {
  /* 业务编号 — mono */
  margin-left: 12px;
  font-size: 16px;
  color: #4F4943;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding: 24px 0 16px;
  border-bottom: 1px solid #E8E4DF;
  margin-bottom: 24px;
}
```

### 7.9 StatCard（KPI 卡片）

Dashboard 的核心组件，体现 VI 升级最直观的位置。

```jsx
<StatCard
  label="本月 PR 总额"
  value="¥1,054,197"
  delta={{ value: '+12.5%', trend: 'up' }}
  icon={<TrendIcon />}
/>
```

```css
.stat-card {
  background: #FFFFFF;
  border: 1px solid #E8E4DF;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-card-label {
  font-size: 13px;                 /* body-sm */
  font-weight: 500;
  color: #4F4943;
  letter-spacing: 0;
}

.stat-card-value {
  font-family: var(--font-mono);   /* ★ JBM */
  font-size: 30px;                 /* display */
  font-weight: 600;
  letter-spacing: -0.025em;
  color: #1F1C19;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;

  /* 防溢出 */
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stat-card-delta {
  font-size: 12px;
  font-family: var(--font-mono);
  /* 正向 success / 负向 error / 中性 secondary */
}
```

**Accent 变体**（强调卡片）— 学 Brex/v1.37.0 的 modal accent：

```css
.stat-card--accent {
  border-left: 3px solid #8B5E3C;  /* 左边条 */
  /* 卡片底色 / 文字色不变 — 只用左条强调 */
}
```

### 7.10 Modal

```css
.modal {
  background: #FFFFFF;
  border-radius: 12px;
  box-shadow: 0 16px 48px rgba(139, 94, 60, 0.12);
  max-width: min(640px, calc(100vw - 32px));
}

.modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid #E8E4DF;
}

.modal-title {
  font-size: 18px;                 /* h-sm */
  font-weight: 600;
  letter-spacing: -0.015em;
}

.modal-body { padding: 24px; }

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid #E8E4DF;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.modal-mask {
  background: rgba(15, 14, 13, 0.4);  /* Onyx 40% */
}
```

### 7.11 Drawer

样式与 Modal 一致，但：

- 从右侧滑出（`width: 480px` 默认；详情型 `width: 720px`）
- 移动端全屏
- 顶部固定 header（`position: sticky`），底部固定 footer

### 7.12 Sidebar（侧边栏导航）

```css
.sidebar {
  background: #FFFFFF;
  border-right: 1px solid #E8E4DF;
  width: 220px;                    /* collapsed: 80px */
}

.sidebar-item {
  height: 40px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  font-weight: 500;
  color: #4F4943;                  /* secondary */
  border-radius: 8px;
  margin: 2px 8px;
}

.sidebar-item:hover {
  background: #F7F6F5;
  color: #1F1C19;
}

.sidebar-item--active {
  background: #F8F4F1;             /* primary-50 */
  color: #543824;                  /* primary-700 */
  font-weight: 600;
}

.sidebar-item--active::before {
  content: '';
  position: absolute;
  left: 0;
  width: 3px;
  height: 20px;
  background: #8B5E3C;             /* primary-500 */
  border-radius: 0 2px 2px 0;
}
```

→ 选中态用浅褐底 + 左侧 3px 主品牌色边条，是 Otter Brown 唯一允许的"装饰性"使用。

---

## 8. Do's and Don'ts（清单 + 理由）

### ✅ Do

1. 所有业务编号 / 金额 / 日期戳 / SKU code 用 `mono-id` 或 `mono-num` class，启用 `tabular-nums`
2. Otter Brown 仅用于：Primary Button、菜单/Tab 选中、checkbox/radio 选中、chart 主指标、`state-progress` Tag
3. 卡片用 1px hairline border + 12px radius，shadow 默认 none，hover 才出现微 shadow
4. 字号严格走 8 步 token（caption/body-sm/body/body-em/sub/h-sm/h/display），禁止其他值
5. 字距越大越紧（display -0.025em，body 0），引用 §4.3 表格
6. 阴影必须 Otter Brown 微染（`rgba(139, 94, 60, ...)`）— 不是纯黑
7. 状态徽章用 outline 风格（浅底 + 中等边 + 深字），不用 solid fill
8. 表格 row hover 用 Paper Beige `#FAFAF8`，不用 primary-50
9. 数字列右对齐 + `mono-num`，ID 列 `mono-id`
10. 下拉 / Modal / Popover 共享 `shadow-floating` 阴影 token
11. 暗色模式靠 hairline 分层，不靠亮度跳一大段
12. 修改前端样式前必须查本文件；新加 token 必须登记到本文件

### ❌ Don't

1. **禁止 Otter Brown 用于装饰性边框 / 普通超链接 / 大面积底色** — 稀释品牌信号
2. **禁止纯黑阴影** — 在 Paper Beige 画布上显廉价
3. **禁止使用 8 步外的字号**（15/17/20/22/28/36px） — 破坏 type scale 纪律
4. **禁止 font-weight 700+** — 与精密感冲突
5. **禁止 6px / 10px / 14px / 16px / 20px 圆角** — 仅 4 / 8 / 12 / 9999
6. **禁止 pill 按钮**（`border-radius: 9999`） — 不符合工具调性
7. **禁止给业务卡片加 hover 阴影叠加**（如 Material Design 风格） — 用 hairline 颜色变化代替
8. **禁止 solid filled Tag** — 在密集表格抢眼
9. **禁止 Recharts 默认配色** — 必须用 §3.4 dataViz palette
10. **禁止状态色随意发明** — 所有状态映射到 §3.3 的 6 个 state token
11. **禁止 section gap > 32px** — B 端工具不需要营销页奢侈
12. **禁止给数字列用 Inter 而不开 tabular-nums** — 表格金额对不齐 = 扫读速度减半
13. **禁止引入 Tailwind / styled-components / emotion** — 破坏 token 单一事实源
14. **禁止移除水獭吉祥物** — 这是 Mica 的差异化资产
15. **禁止 dark mode 用 #000000** — 用 `#161514` Onyx

---

## 9. 落地路线

### Phase 1（v1.39.0）— Foundation Tokens（低风险，纯 token + CSS）

**只动 4 个文件，不碰任何业务页面**：

1. `frontend/src/theme/tokens.ts` — 重构 token 体系
   - 新增 `neutral.25` Paper Beige、`neutral.250` Hairline
   - 新增 `font.display` 层级 + `font.tracking` 表
   - 新增 `color.dataViz` 6 色
   - 新增 `color.state` 6 色（替代之前 success/warning/error）
   - shadow 全部改为 Otter Brown 微染
2. `frontend/src/theme/antdTheme.ts` — AntD 主题映射
   - `Button.controlHeight = 36`、`borderRadius = 8`
   - `Card.borderRadiusLG = 12`、`boxShadowTertiary = none`
   - `Table.headerBg = neutral.50`、`rowHoverBg = neutral.25`
3. `frontend/src/styles/global.css`
   - body bg 改为 `#FAFAF8`
   - 全站 `font-feature-settings: 'tnum' 1`
   - 加 `.mono-id`、`.mono-num`、`.tabular-nums` utility class
   - 加 `.tag-state-*` 6 个 state 变体
4. `frontend/package.json` — 新增 `@fontsource/jetbrains-mono`（如未引入）

**预期效果**：

- 所有页面 bg 立刻从纯白变 Paper Beige
- 卡片阴影统一为 Otter Brown 微染
- 数字（含 Inter 渲染的金额）自动等宽对齐

**风险**：极低。只改 token，不动组件。

**Bump**：`v1.38.x → v1.39.0`，CHANGELOG 记 "VI Foundation Tokens"。

### Phase 2（v1.40.0）— Typography & Identifier Pass

**全站推 mono 业务标识符 + display token**：

1. 创建 `<MonoId>` 和 `<MonoNum>` React 组件，封装 class
2. 全站搜索替换：
   - `pr.pr_number` 渲染处全部包 `<MonoId>`
   - `po.po_number` 同上
   - 所有金额渲染 `fmtAmount(...)` 改为返回 `<MonoNum>`
   - 所有日期渲染 `fmtDate(...)` 同上
   - SKU code、订单号、合同号、发票号同上
3. StatCard 主数字应用 `display` token（30px / 600 / mono / tabular-nums）
4. PageHeader 标题应用 `h` token

**预期效果**：

- 列表表格扫读速度 +30%（数字对齐、ID 等宽）
- StatCard 视觉立刻"高级化"
- 整站立刻识别为"工具不是营销页"

**风险**：中。需要全站文本替换。建议 ralph-loop 自动化处理。

**Bump**：`v1.40.0`。

### Phase 3（v1.41.0+）— Component-by-Component Refresh

**按页面增量改造，每个版本一个域**：

- v1.41 — Dashboard（StatCard + chart 配色）
- v1.42 — PR/PO 列表（state badge + 表格 hover）
- v1.43 — PR/PO 详情（信息层级 + 履约链可视化）
- v1.44 — Admin 控制台（密集表单优化）
- v1.45 — Mobile 适配（compact density 在小屏的退化策略）

**风险**：每版独立可回滚。

---

## 10. AI Agent Quick Prompt Guide

> 本节给 Claude / Cursor / Sisyphus-Junior 看。改前端时直接引用此节作为 design context。

### Quick Color Reference

```text
# Surfaces
bg:        #FAFAF8  Paper Beige (page canvas)
card:      #FFFFFF  Pure White
subtle:    #F7F6F5  card-internal section
sunken:    #EFECE9  disabled / nested

# Text
primary:   #1F1C19  body, headings
secondary: #4F4943  field values, labels
tertiary:  #8F8881  metadata, captions
disabled:  #CFCAC5

# Border
hairline:  #E8E4DF  default 1px border
default:   #DFDBD7  emphasis (rare)
strong:    #AFA9A3  section divider

# Brand
primary:   #8B5E3C  Otter Brown — single accent

# State
info:      #3B82F6
progress:  #8B5E3C  (Otter Brown — 进行中绑定品牌色)
success:   #22C55E
warning:   #F59E0B
error:     #EF4444
neutral:   #8F8881

# Shadow (Brand-tinted)
card:      0 1px 2px rgba(139, 94, 60, 0.04)
floating:  0 4px 12px rgba(139, 94, 60, 0.08)
modal:     0 16px 48px rgba(139, 94, 60, 0.12)
```

### Component Generation Prompts

每段都是给 AI 的"参数化模板"：

#### 1. Card

> White (`#FFFFFF`) background, 12px radius, 1px solid `#E8E4DF` border, 24px padding (or 16px for list cards), no default shadow. Header inside card is `h-sm` token: 18px Inter weight 600 letter-spacing -0.015em color `#1F1C19`, with 1px hairline bottom border + 12px margin-bottom.

#### 2. Primary Button

> Background `#8B5E3C` (Otter Brown 500), white text Inter 14px weight 500, 8px border-radius, 8px 16px padding, height 36px, no border, no rest-state shadow. Hover: background `#704B30`, add shadow `0 2px 4px rgba(139, 94, 60, 0.10)`. Active: `#543824`. Use only for the single most important action per region.

#### 3. Default Button

> Transparent background, 1px solid `#CFCAC5` border, `#1F1C19` text Inter 14px weight 500, same padding/height as Primary Button. Hover: border `#AFA9A3`, background `#F7F6F5`. **Never use Otter Brown border on default buttons.**

#### 4. Status Badge

> Inline-flex with 6px circular dot of `var(--state-color-500)` + label in Inter 13px weight 500 in `var(--state-color-700)`. No background, no border. 6px gap between dot and label. Use for status columns in dense tables.

#### 5. Tag

> 12px Inter weight 500, 4px radius, 1px solid `var(--state-color-200)` border, `var(--state-color-50)` background, `var(--state-color-700)` text, 2px 8px padding. Outlined variant only — never solid filled.

#### 6. Stat Card (KPI)

> White card 12px radius, 1px hairline border, 20px padding. Label: `body-sm` (13px / 500 / `#4F4943`). Value: `display` token (30px / 600 / **JetBrains Mono** / -0.025em / tabular-nums / `#1F1C19`) with white-space nowrap + ellipsis. Delta: 12px JBM color matched to state.

#### 7. Business Identifier (e.g. PR-2026-0017)

> Wrap in `<code class="mono-id">PR-2026-0017</code>`. JetBrains Mono 0.95em with `font-feature-settings: 'tnum' 1, 'zero' 1, 'ss19' 1`, transparent background, color inherits from parent.

#### 8. Currency Amount (e.g. ¥1,054,197.00)

> Wrap in `<span class="mono-num">¥1,054,197.00</span>`. JetBrains Mono with `font-variant-numeric: tabular-nums`. In tables, also add `.mono-num--right` for right alignment.

#### 9. Table

> 14px font-size. Header background `#F7F6F5`, header text `body-sm` (13px / 500 / `#4F4943`), 10px 12px header padding, 1px `#E8E4DF` bottom border. Row height 40px, padding 10px 12px, 1px `#E8E4DF` bottom border. Row hover background `#FAFAF8`. Number columns `mono-num` + right-aligned. ID columns `mono-id`.

#### 10. Modal

> White 12px radius, `0 16px 48px rgba(139, 94, 60, 0.12)` shadow, max-width `min(640px, calc(100vw - 32px))`. Header: 20px 24px padding, 1px hairline bottom border, title `h-sm` (18px / 600). Body: 24px padding. Footer: 16px 24px padding, 1px hairline top border, right-aligned button group with 8px gap.

#### 11. Sidebar Active Item

> Background `#F8F4F1` (primary-50), text color `#543824` (primary-700) Inter 14px weight 600. 3px wide `#8B5E3C` left edge bar with 0 2px 2px 0 radius. This is the only "decorative" use of Otter Brown allowed.

#### 12. Chart (Recharts)

> Stroke / fill colors limited to dataViz palette: `#8B5E3C` (primary), `#C4A48A` (secondary), `#2F8F69` (positive), `#C97B3F` (attention), `#B85450` (critical), `#6F6861` (baseline). Grid lines `#E8E4DF` 1px dashed. Axis labels `caption` (12px / 400 / `#8F8881`). Legend Inter 12px / 500.

### Forbidden Patterns（让 AI 不要生成的代码）

```jsx
// ❌ 不要硬编码颜色
<div style={{ background: '#fff', color: '#333' }}>

// ❌ 不要用 inline shadow
<Card style={{ boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>

// ❌ 不要 Otter Brown 装饰边框
<div style={{ border: '1px solid #8B5E3C' }}>

// ❌ 不要 solid filled Tag
<Tag color="success">已完成</Tag>  // AntD solid 风格

// ❌ 不要给金额硬编码 mono
<span style={{ fontFamily: 'monospace' }}>¥10,000</span>

// ❌ 不要用 8 步外的字号
<h2 style={{ fontSize: 20 }}>标题</h2>

// ❌ 不要 pill 按钮
<Button style={{ borderRadius: 9999 }}>提交</Button>

// ✅ 正确做法
<Card>  {/* 走 token */}
  <Title level={4}>标题</Title>  {/* h-sm token */}
  <Tag className="tag-success">已完成</Tag>
  <span className="mono-num">¥10,000.00</span>
</Card>
```

---

## 11. 维护准则

### 何时需要修改本文档

- 新增 design token（颜色 / 字号 / 阴影 / 间距）— **必须**登记到本文件
- 修改铁律 / 增删 Don't 项 — 必须经过设计 review
- 新增组件 spec — 在 §7 增加章节
- v1.39 / v1.40 / v1.41 落地后 — 在 §9 标 ✅ 完成

### 文档变更流程

1. 修改 `docs/DESIGN.md`
2. 同步更新 `frontend/src/theme/tokens.ts` 注释
3. 在 `CHANGELOG.md` 记录"design system update"条目
4. 不需要 bump version（除非伴随实际代码改动）

### 变更优先级

- **变 token 值**：低优先级，符合本文档原则即可（如调暗 hairline 一点）
- **变 token 命名**：高优先级，全站搜索替换 + lint 验证
- **新增/移除铁律**：最高优先级，需要写 ADR

### 与 AGENTS.md 的关系

`AGENTS.md` §5.8 是"前端主题约定"的入口，本文件是详细规范。AGENTS.md 不重复本文件，只引用：

```markdown
### 5.8 前端主题
详见 [docs/DESIGN.md](docs/DESIGN.md)。简言之：
- 颜色/间距/字号 → 用 tokens（`frontend/src/theme/tokens.ts`），不要硬编码
- Otter Brown 仅用于 primary CTA / 选中态 / chart 主指标
- 业务编号 / 金额 / 日期戳必须用 `mono-id` 或 `mono-num` class
```

---

**文档版本**：1.0  
**最近更新**：2026-06-23  
**下一次审阅**：v1.39.0 落地后

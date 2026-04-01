# Learn Theme — 从公众号文章 URL 提取排版主题

**日期**: 2026-04-01
**状态**: 设计完成，待实现

## 概述

新增 `learn-theme` 功能：用户提供一个微信公众号文章 URL，脚本自动抓取 HTML、提取 inline style，生成与现有 16 个主题格式一致的 YAML 主题文件，立即可用于排版。

## 用户接口

```bash
python3 toolkit/cli.py learn-theme https://mp.weixin.qq.com/s/xxxx --name my-style
```

- `url`（必填）：微信公众号文章链接
- `--name`（必填）：主题名称，用于文件名和后续引用
- 输出：`toolkit/themes/{name}.yaml`

成功后终端打印提取摘要（主色、字号、行高等）并提示：
```
Theme saved to toolkit/themes/my-style.yaml
Use it: python3 toolkit/cli.py preview article.md --theme my-style
Or set in style.yaml: theme: my-style
```

## 核心流程

```
URL → fetch HTML → parse #js_content → 按元素类型提取 inline style
→ 频率统计 + 语义角色推断 → 生成 theme YAML → 写入 toolkit/themes/
```

### Step 1: Fetch

- `requests.get(url)` + 浏览器 User-Agent header
- 强制 UTF-8 解码（微信 API 不声明 charset）
- 验证返回的 HTML 包含 `#js_content`，否则报错退出

### Step 2: Extract

用 BeautifulSoup 解析 `#js_content` 内所有带 inline style 的元素，按标签类型分组收集 CSS 属性值。

目标元素：`p`, `section`, `span`, `strong`, `h1`-`h4`, `blockquote`, `code`, `pre`, `img`

每个元素提取的属性：`color`, `font-size`, `line-height`, `letter-spacing`, `font-family`, `background`, `background-color`, `border-left`, `border-bottom`, `border-radius`, `margin`, `padding`

### Step 3: Analyze — 语义角色推断

**层 1 — 配色 + 字号体系（占观感 ~70%）：**

| 目标属性 | 数据来源 | 推断逻辑 |
|---------|---------|---------|
| `text` | `<p>` 的 `color` | 最高频颜色 |
| `text_light` | 所有元素的灰色系 `color` | 排除亮度 >0.85 和 <0.15 的值，取亮度最高的灰色 |
| `primary` | `<strong>`, `<section>`(font-size≥20px) 的非灰色 `color` | 大字号标题色权重 ×5，取最高频 |
| `secondary` | 同上 | 第二高频非灰色，无则从 primary 调亮 10% 派生 |
| `background` | `#js_content` 或顶层 `section` 的 `background` | 直接取，无则默认 `#ffffff` |
| 正文字号 | `<p>` 的 `font-size` | 众数 |
| 行高 | `<p>` 的 `line-height` | 众数 |
| 字间距 | `<p>` 的 `letter-spacing` | 众数，无则不设 |
| 字体 | `<span>` 的 `font-family` | 最高频 |

**层 2 — 装饰细节（占观感 ~20%）：**

| 目标属性 | 数据来源 | 推断逻辑 |
|---------|---------|---------|
| `quote_border` | 含 `border-left` 的 `blockquote`/`section` | 直接取 border-left-color，无则用 primary |
| `quote_bg` | 同上的 `background` | 直接取，无则从 primary 派生浅底色 |
| `code_bg` | `<code>`, `<pre>` 的 `background` | 直接取，无则默认深色 `#1e293b` |
| `code_color` | `<code>`, `<pre>` 的 `color` | 直接取，无则默认 `#e2e8f0` |
| `border_radius` | 所有元素 `border-radius` | 众数，无则默认 `6px` |
| 标题装饰 | `<h1>`-`<h3>` 的 border/padding | 直接映射到 CSS |
| 段落间距 | `<p>` 的 `margin` | 众数，映射到 body margin 和 p margin |

### Step 4: Generate

基于提取结果，以 `professional-clean.yaml` 为模板（确保所有 CSS selector 覆盖完整），替换颜色值和排版参数，生成完整的 theme YAML。

结构：
```yaml
name: "{name}"
description: "从 {article_title} 学习的排版主题"
colors:
  primary: "{extracted}"
  secondary: "{extracted}"
  text: "{extracted}"
  text_light: "{extracted}"
  background: "{extracted}"
  code_bg: "{extracted}"
  code_color: "{extracted}"
  quote_border: "{extracted}"
  quote_bg: "{extracted}"
  border_radius: "{extracted}"
darkmode:
  # 从 light mode 颜色自动派生
base_css: |
  # 基于 professional-clean 模板，替换提取到的值
```

**Darkmode 派生规则：**
- `background` → 取反亮度，钳位到 `#1a1a1a`-`#2a2a2a`
- `text` → 亮度提升到 0.8，如 `#c8c8c8`
- `primary` → 饱和度不变，亮度提升 15%
- 其余属性同理微调

### Step 5: Report

终端输出提取摘要：
```
Learned theme from: 短剧行业的AI重构
  text:       #000000
  primary:    #2d71d6 (blue)
  secondary:  #5f9cef
  font:       Optima-Regular, PingFangTC-light
  size:       16px / line-height 1.75 / spacing 1px

Theme saved → toolkit/themes/my-style.yaml
```

## Fallback 策略

每个属性提取失败时的默认值继承自 `professional-clean` 主题，确保输出始终是一个完整可用的主题文件。不会因为文章结构简单就生成残缺主题。

## 文件结构

```
scripts/learn_theme.py      # 核心逻辑：fetch + extract + analyze + generate
toolkit/cli.py              # 新增 learn-theme 子命令，调用 scripts/learn_theme.py
```

**不修改的文件：** `theme.py`, `converter.py`, 现有主题文件 — 零侵入。

## SKILL.md 集成

在辅助功能列表中新增触发词"学习排版"/"学排版"，调用：
```bash
python3 scripts/learn_theme.py <url> --name <name>
```

## 依赖

- `requests`（已有）
- `beautifulsoup4`（已有）
- `pyyaml`（已有）
- `colorsys`（标准库）

无新依赖。

## 不做的事

- 不学习结构布局（卡片嵌套、多栏、SVG 分割线）
- 不支持本地 HTML 文件输入（仅 URL）
- 不自动处理微信登录/验证码（抓取失败直接报错）
- 不修改现有主题系统代码

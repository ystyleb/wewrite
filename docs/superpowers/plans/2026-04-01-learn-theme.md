# Learn Theme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `learn-theme` command that extracts a reusable theme YAML from any WeChat article URL.

**Architecture:** New script `scripts/learn_theme.py` handles fetch → extract → analyze → generate. CLI adds a `learn-theme` subcommand that calls the script. SKILL.md gets a new trigger word. Zero changes to existing theme/converter code.

**Tech Stack:** Python 3.11+, requests, BeautifulSoup4, PyYAML, colorsys (stdlib)

**Spec:** `docs/superpowers/specs/2026-04-01-learn-theme-design.md`

---

### Task 1: Color utility helpers

**Files:**
- Create: `scripts/learn_theme.py`

These pure functions have no dependencies and are used by all later tasks.

- [ ] **Step 1: Create `scripts/learn_theme.py` with color utilities**

```python
#!/usr/bin/env python3
"""
Learn a WeChat formatting theme from a public article URL.

Usage:
    python3 scripts/learn_theme.py <url> --name <theme-name>
"""

import colorsys
import re


def rgb_to_hex(rgb_str: str) -> str:
    """Convert 'rgb(r, g, b)' or 'rgba(r,g,b,a)' to '#rrggbb'.

    Returns the original string if it doesn't match rgb/rgba format.
    If already a hex color, returns it lowercased.
    """
    if rgb_str.startswith("#"):
        return rgb_str.lower()
    m = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", rgb_str)
    if m:
        return "#{:02x}{:02x}{:02x}".format(
            int(m.group(1)), int(m.group(2)), int(m.group(3))
        )
    return rgb_str


def lightness(hex_color: str) -> float:
    """Return HLS lightness (0.0–1.0) for a hex color."""
    if not hex_color.startswith("#") or len(hex_color) != 7:
        return 0.5
    r = int(hex_color[1:3], 16) / 255
    g = int(hex_color[3:5], 16) / 255
    b = int(hex_color[5:7], 16) / 255
    return colorsys.rgb_to_hls(r, g, b)[1]


def is_gray(hex_color: str, threshold: int = 30) -> bool:
    """Check if a color is grayscale (R/G/B within `threshold` of each other)."""
    if not hex_color.startswith("#") or len(hex_color) != 7:
        return False
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return max(r, g, b) - min(r, g, b) < threshold


def adjust_lightness(hex_color: str, target_l: float) -> str:
    """Return a new hex color with lightness set to `target_l` (0.0–1.0)."""
    if not hex_color.startswith("#") or len(hex_color) != 7:
        return hex_color
    r = int(hex_color[1:3], 16) / 255
    g = int(hex_color[3:5], 16) / 255
    b = int(hex_color[5:7], 16) / 255
    h, _l, s = colorsys.rgb_to_hls(r, g, b)
    nr, ng, nb = colorsys.hls_to_rgb(h, max(0, min(1, target_l)), s)
    return "#{:02x}{:02x}{:02x}".format(
        int(nr * 255), int(ng * 255), int(nb * 255)
    )


def derive_darkmode(colors: dict) -> dict:
    """Derive dark mode colors from light mode colors."""
    dm = {}
    dm["background"] = "#1e1e1e"
    dm["text"] = adjust_lightness(colors.get("text", "#333333"), 0.8)
    dm["text_light"] = adjust_lightness(colors.get("text_light", "#666666"), 0.6)
    primary = colors.get("primary", "#2563eb")
    dm["primary"] = adjust_lightness(primary, min(lightness(primary) + 0.15, 0.85))
    dm["code_bg"] = "#2d2d2d"
    dm["code_color"] = "#d4d4d4"
    dm["quote_bg"] = "#252525"
    dm["quote_border"] = dm["primary"]
    return dm
```

- [ ] **Step 2: Verify file runs without errors**

Run: `python3 scripts/learn_theme.py` (will exit with no output since no CLI yet — just checks import/syntax)

Expected: No traceback. May print nothing or the usage error we'll add later.

- [ ] **Step 3: Commit**

```bash
git add scripts/learn_theme.py
git commit -m "feat(learn-theme): add color utility helpers"
```

---

### Task 2: HTML fetch and style extraction

**Files:**
- Modify: `scripts/learn_theme.py`

Add the functions to fetch a WeChat article and extract inline styles by element type.

- [ ] **Step 1: Add `parse_inline_style` function**

Append after the existing code in `scripts/learn_theme.py`:

```python
def parse_inline_style(style_str: str) -> dict[str, str]:
    """Parse an inline style string into a {property: value} dict."""
    props = {}
    for part in style_str.split(";"):
        part = part.strip()
        if ":" in part:
            k, v = part.split(":", 1)
            props[k.strip().lower()] = v.strip()
    return props
```

- [ ] **Step 2: Add `fetch_article` function**

Append:

```python
import requests
from bs4 import BeautifulSoup


def fetch_article(url: str) -> BeautifulSoup:
    """Fetch a WeChat article and return the #js_content element as soup.

    Raises SystemExit on fetch failure or missing content element.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    content = soup.find(id="js_content")
    if not content:
        print(f"Error: #js_content not found — the URL may require verification.", file=__import__("sys").stderr)
        raise SystemExit(1)

    # Also try to grab the article title
    title_el = soup.find("h1", class_="rich_media_title") or soup.find("h1", id="activity-name")
    title = title_el.get_text(strip=True) if title_el else ""
    content._wewrite_title = title  # stash on the element for later use

    return content
```

- [ ] **Step 3: Add `extract_styles` function**

Append:

```python
from collections import Counter


def extract_styles(content: BeautifulSoup) -> dict:
    """Extract inline styles from #js_content grouped by element type.

    Returns a dict like:
        {
            "p": [{"color": "rgb(0,0,0)", "font-size": "16px", ...}, ...],
            "section": [...],
            ...
        }
    """
    TARGET_TAGS = ("p", "section", "span", "strong", "em",
                   "h1", "h2", "h3", "h4",
                   "blockquote", "code", "pre", "img", "a")

    grouped: dict[str, list[dict]] = {tag: [] for tag in TARGET_TAGS}

    for el in content.find_all(True, recursive=True):
        tag = el.name
        if tag not in grouped:
            continue
        style = el.get("style", "")
        if not style:
            continue
        props = parse_inline_style(style)
        if props:
            grouped[tag].append(props)

    return grouped
```

- [ ] **Step 4: Quick smoke test with the saved HTML from earlier exploration**

Run:
```bash
python3 -c "
from scripts.learn_theme import parse_inline_style, extract_styles
from bs4 import BeautifulSoup
with open('/tmp/wechat_article.html', 'r') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')
content = soup.find(id='js_content')
styles = extract_styles(content)
print(f'p: {len(styles[\"p\"])} elements')
print(f'section: {len(styles[\"section\"])} elements')
print(f'span: {len(styles[\"span\"])} elements')
print(f'strong: {len(styles[\"strong\"])} elements')
"
```

Expected: Counts matching our earlier exploration (p: ~70, section: ~60, span: ~87, strong: ~16).

- [ ] **Step 5: Commit**

```bash
git add scripts/learn_theme.py
git commit -m "feat(learn-theme): add HTML fetch and style extraction"
```

---

### Task 3: Style analysis — infer semantic color roles

**Files:**
- Modify: `scripts/learn_theme.py`

This is the core logic: take raw extracted styles and infer the theme's semantic color/typography properties.

- [ ] **Step 1: Add `most_common_value` helper**

Append to `scripts/learn_theme.py`:

```python
def most_common_value(style_list: list[dict], prop: str) -> str | None:
    """Return the most common value of `prop` across a list of parsed style dicts."""
    counter = Counter()
    for props in style_list:
        if prop in props:
            counter[props[prop]] += 1
    if not counter:
        return None
    return counter.most_common(1)[0][0]
```

- [ ] **Step 2: Add `analyze_styles` function**

Append:

```python
# Defaults from professional-clean, used when extraction finds nothing
DEFAULTS = {
    "primary": "#2563eb",
    "secondary": "#3b82f6",
    "text": "#333333",
    "text_light": "#666666",
    "background": "#ffffff",
    "code_bg": "#1e293b",
    "code_color": "#e2e8f0",
    "quote_border": "#2563eb",
    "quote_bg": "#eff6ff",
    "border_radius": "8px",
    "font_size": "16px",
    "line_height": "1.8",
    "letter_spacing": "0",
    "font_family": (
        '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, '
        '"Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", '
        '"Microsoft YaHei", sans-serif'
    ),
    "p_margin": "12px 0",
}


def analyze_styles(grouped: dict) -> dict:
    """Infer semantic theme properties from grouped inline styles.

    Returns a flat dict with keys: primary, secondary, text, text_light,
    background, code_bg, code_color, quote_border, quote_bg, border_radius,
    font_size, line_height, letter_spacing, font_family, p_margin.
    """
    result = dict(DEFAULTS)

    # --- Layer 1: Colors + Typography ---

    # text: most common color on <p>
    p_color = most_common_value(grouped.get("p", []), "color")
    if p_color:
        result["text"] = rgb_to_hex(p_color)

    # text_light: gray color with lightness between 0.15 and 0.85, excluding text
    all_colors = Counter()
    for tag_styles in grouped.values():
        for props in tag_styles:
            if "color" in props:
                h = rgb_to_hex(props["color"])
                all_colors[h] += 1
    gray_candidates = [
        (c, n) for c, n in all_colors.most_common(30)
        if is_gray(c) and c != result["text"]
        and 0.15 < lightness(c) < 0.85
    ]
    if gray_candidates:
        # Pick the one with highest lightness (= the "lighter" text)
        gray_candidates.sort(key=lambda x: lightness(x[0]), reverse=True)
        result["text_light"] = gray_candidates[0][0]

    # primary: non-gray color on strong/section, boost large font-size headings
    accent_counter = Counter()
    for tag in ("strong", "section", "h1", "h2", "h3", "span"):
        for props in grouped.get(tag, []):
            if "color" not in props:
                continue
            h = rgb_to_hex(props["color"])
            if is_gray(h) or h == result["text"]:
                continue
            # Boost heading-sized elements
            fs = props.get("font-size", "")
            fs_match = re.search(r"(\d+)", fs)
            if fs_match and int(fs_match.group(1)) >= 20:
                accent_counter[h] += 5
            else:
                accent_counter[h] += 1
    if accent_counter:
        result["primary"] = accent_counter.most_common(1)[0][0]
        # secondary: second most common accent, or derive from primary
        rest = [(c, n) for c, n in accent_counter.most_common(5) if c != result["primary"]]
        if rest:
            result["secondary"] = rest[0][0]
        else:
            result["secondary"] = adjust_lightness(
                result["primary"],
                min(lightness(result["primary"]) + 0.10, 0.90),
            )

    # background
    content_bg = None
    for tag in ("section",):
        # Check top-level sections only (first few)
        for props in grouped.get(tag, [])[:5]:
            for k in ("background", "background-color"):
                if k in props:
                    v = props[k]
                    if "url" not in v and "transparent" not in v and "100%" not in v:
                        candidate = rgb_to_hex(v)
                        if lightness(candidate) > 0.85:
                            content_bg = candidate
                            break
    if content_bg:
        result["background"] = content_bg

    # Typography from <p>
    p_styles = grouped.get("p", [])
    for prop, key in [
        ("font-size", "font_size"),
        ("line-height", "line_height"),
        ("letter-spacing", "letter_spacing"),
        ("margin", "p_margin"),
    ]:
        val = most_common_value(p_styles, prop)
        if val:
            result[key] = val

    # Font family from <span> (WeChat wraps text in spans with font-family)
    span_font = most_common_value(grouped.get("span", []), "font-family")
    if span_font:
        result["font_family"] = span_font

    # --- Layer 2: Decorative ---

    # quote: look for border-left on blockquote or section
    for tag in ("blockquote", "section"):
        for props in grouped.get(tag, []):
            bl = props.get("border-left", "")
            if bl:
                color_match = re.search(r"(#[0-9a-fA-F]{3,6}|rgb\([^)]+\))", bl)
                if color_match:
                    result["quote_border"] = rgb_to_hex(color_match.group(1))
                bg = props.get("background", props.get("background-color", ""))
                if bg and "transparent" not in bg and "url" not in bg:
                    result["quote_bg"] = rgb_to_hex(bg)
                break
    # If no explicit quote found, derive from primary
    if result["quote_border"] == DEFAULTS["quote_border"] and result["primary"] != DEFAULTS["primary"]:
        result["quote_border"] = result["primary"]
        # Derive a light tint of primary for quote_bg
        result["quote_bg"] = adjust_lightness(result["primary"], 0.95)

    # code blocks
    for tag in ("pre", "code"):
        for props in grouped.get(tag, []):
            bg = props.get("background", props.get("background-color", ""))
            if bg and "none" not in bg and "transparent" not in bg:
                result["code_bg"] = rgb_to_hex(bg)
            if "color" in props:
                result["code_color"] = rgb_to_hex(props["color"])
            break

    # border-radius: mode across all elements
    radius_counter = Counter()
    for tag_styles in grouped.values():
        for props in tag_styles:
            if "border-radius" in props:
                radius_counter[props["border-radius"]] += 1
    if radius_counter:
        result["border_radius"] = radius_counter.most_common(1)[0][0]

    return result
```

- [ ] **Step 3: Smoke test analysis against saved HTML**

Run:
```bash
python3 -c "
from scripts.learn_theme import extract_styles, analyze_styles
from bs4 import BeautifulSoup
with open('/tmp/wechat_article.html', 'r') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')
content = soup.find(id='js_content')
grouped = extract_styles(content)
result = analyze_styles(grouped)
for k, v in sorted(result.items()):
    print(f'  {k:20s} {v}')
"
```

Expected: `primary` ≈ `#2d71d6`, `text` ≈ `#000000`, `font_size` = `16px`, `line_height` = `1.75`, `letter_spacing` = `1px`, `font_family` contains `Optima-Regular`.

- [ ] **Step 4: Commit**

```bash
git add scripts/learn_theme.py
git commit -m "feat(learn-theme): add style analysis with semantic role inference"
```

---

### Task 4: Theme YAML generation

**Files:**
- Modify: `scripts/learn_theme.py`

Generate the final YAML theme file using `professional-clean.yaml` as the CSS template.

- [ ] **Step 1: Add `generate_theme_yaml` function**

Append to `scripts/learn_theme.py`:

```python
from pathlib import Path
import yaml


TEMPLATE_THEME = "professional-clean"
THEMES_DIR = Path(__file__).resolve().parent.parent / "toolkit" / "themes"


def _load_template_css() -> str:
    """Load the base_css from professional-clean as a template."""
    template_path = THEMES_DIR / f"{TEMPLATE_THEME}.yaml"
    with open(template_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["base_css"]


def generate_theme_yaml(name: str, title: str, analyzed: dict) -> str:
    """Generate a complete theme YAML string from analyzed style properties.

    Uses professional-clean's base_css as template, replacing color values
    and typography properties with the extracted ones.
    """
    css = _load_template_css()

    colors = {
        "primary": analyzed["primary"],
        "secondary": analyzed["secondary"],
        "text": analyzed["text"],
        "text_light": analyzed["text_light"],
        "background": analyzed["background"],
        "code_bg": analyzed["code_bg"],
        "code_color": analyzed["code_color"],
        "quote_border": analyzed["quote_border"],
        "quote_bg": analyzed["quote_bg"],
        "border_radius": analyzed["border_radius"],
    }

    # Replace colors in CSS template
    # Map template default colors -> extracted colors
    replacements = {
        "#2563eb": analyzed["primary"],     # primary
        "#3b82f6": analyzed["secondary"],   # secondary
        "#333333": analyzed["text"],        # text
        "#666666": analyzed["text_light"],  # text_light
        "#1e293b": analyzed["code_bg"],     # code_bg
        "#e2e8f0": analyzed["code_color"],  # code_color
        "#eff6ff": analyzed["quote_bg"],    # quote_bg
    }
    for old, new in replacements.items():
        css = css.replace(old, new)

    # Replace typography
    # font-size on body
    css = re.sub(
        r"(body\s*\{[^}]*font-size:\s*)\d+px",
        rf"\g<1>{analyzed['font_size']}",
        css,
    )
    # line-height on body
    css = re.sub(
        r"(body\s*\{[^}]*line-height:\s*)[\d.]+",
        rf"\g<1>{analyzed['line_height']}",
        css,
    )
    # font-family on body
    css = re.sub(
        r'(body\s*\{[^}]*font-family:\s*)[^;]+',
        rf'\g<1>{analyzed["font_family"]}',
        css,
    )
    # p line-height
    css = re.sub(
        r"(p\s*\{[^}]*line-height:\s*)[\d.]+",
        rf"\g<1>{analyzed['line_height']}",
        css,
    )
    # p margin
    css = re.sub(
        r"(p\s*\{[^}]*margin:\s*)[^;]+",
        rf"\g<1>{analyzed['p_margin']}",
        css,
    )
    # li line-height to match p
    css = re.sub(
        r"(li\s*\{[^}]*line-height:\s*)[\d.]+",
        rf"\g<1>{analyzed['line_height']}",
        css,
    )
    # border-radius on relevant selectors (pre, blockquote, img, code)
    css = css.replace("border-radius: 8px", f"border-radius: {analyzed['border_radius']}")
    css = css.replace("border-radius: 4px", f"border-radius: {analyzed['border_radius']}")

    dm = derive_darkmode(colors)

    desc = f"从「{title}」学习的排版主题" if title else f"Learned theme: {name}"

    theme_data = {
        "name": name,
        "description": desc,
        "colors": {**colors, "darkmode": dm},
        "base_css": css,
    }

    return yaml.dump(theme_data, allow_unicode=True, default_flow_style=False, sort_keys=False)
```

- [ ] **Step 2: Test YAML generation**

Run:
```bash
python3 -c "
from scripts.learn_theme import extract_styles, analyze_styles, generate_theme_yaml
from bs4 import BeautifulSoup
with open('/tmp/wechat_article.html', 'r') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')
content = soup.find(id='js_content')
grouped = extract_styles(content)
analyzed = analyze_styles(grouped)
output = generate_theme_yaml('test-learned', 'AI短剧测试', analyzed)
print(output[:500])
print('...')
# Verify it's valid YAML
import yaml
data = yaml.safe_load(output)
assert data['name'] == 'test-learned'
assert 'primary' in data['colors']
assert 'darkmode' in data['colors']
assert 'base_css' in data
print('YAML validation passed')
"
```

Expected: Valid YAML output with name, colors (including darkmode), and base_css. No traceback.

- [ ] **Step 3: Commit**

```bash
git add scripts/learn_theme.py
git commit -m "feat(learn-theme): add theme YAML generation from analyzed styles"
```

---

### Task 5: CLI integration and terminal report

**Files:**
- Modify: `scripts/learn_theme.py` (add `main()` and CLI arg parsing)
- Modify: `toolkit/cli.py` (add `learn-theme` subcommand)

- [ ] **Step 1: Add `main()` with argparse to `scripts/learn_theme.py`**

Append to `scripts/learn_theme.py`:

```python
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Learn a WeChat formatting theme from an article URL.",
    )
    parser.add_argument("url", help="WeChat article URL (https://mp.weixin.qq.com/s/...)")
    parser.add_argument("--name", required=True, help="Theme name (used as filename and reference)")
    parser.add_argument("--output-dir", default=None, help="Output directory (default: toolkit/themes/)")
    args = parser.parse_args()

    # Validate name
    if not re.match(r"^[a-zA-Z0-9_-]+$", args.name):
        print("Error: --name must contain only letters, digits, hyphens, and underscores.", file=sys.stderr)
        raise SystemExit(1)

    output_dir = Path(args.output_dir) if args.output_dir else THEMES_DIR
    output_path = output_dir / f"{args.name}.yaml"

    if output_path.exists():
        print(f"Warning: {output_path} already exists, will be overwritten.", file=sys.stderr)

    # Step 1: Fetch
    print(f"Fetching article...")
    content = fetch_article(args.url)
    title = getattr(content, "_wewrite_title", "")
    if title:
        print(f"Title: {title}")

    # Step 2: Extract
    grouped = extract_styles(content)
    styled_count = sum(len(v) for v in grouped.values())
    print(f"Extracted {styled_count} styled elements.")

    # Step 3: Analyze
    analyzed = analyze_styles(grouped)

    # Step 4: Generate & write
    theme_yaml = generate_theme_yaml(args.name, title, analyzed)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(theme_yaml, encoding="utf-8")

    # Step 5: Report
    print()
    print(f"Learned theme from: {title or args.url}")
    print(f"  text:       {analyzed['text']}")
    print(f"  text_light: {analyzed['text_light']}")
    print(f"  primary:    {analyzed['primary']}")
    print(f"  secondary:  {analyzed['secondary']}")
    print(f"  background: {analyzed['background']}")
    print(f"  font:       {analyzed['font_family'][:50]}")
    print(f"  size:       {analyzed['font_size']} / line-height {analyzed['line_height']} / spacing {analyzed['letter_spacing']}")
    print()
    print(f"Theme saved → {output_path}")
    print(f"Use it:  python3 toolkit/cli.py preview article.md --theme {args.name}")
    print(f"Or set:  theme: {args.name}  in style.yaml")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Move imports to top of file**

Reorganize the imports at the top of `scripts/learn_theme.py` so all imports are at the top (PEP 8):

```python
import argparse
import colorsys
import re
import sys
from collections import Counter
from pathlib import Path

import requests
import yaml
from bs4 import BeautifulSoup
```

Remove the inline `import` statements from `fetch_article` (`__import__("sys").stderr` → `sys.stderr`), `extract_styles` (Counter already imported), and `generate_theme_yaml` (Path, yaml already imported).

- [ ] **Step 3: Test full CLI flow against saved HTML**

Since we may not be able to reliably fetch from WeChat during automated testing, test with the already-saved HTML first by temporarily using a local path. But first, verify the script's `--help` works:

Run:
```bash
python3 scripts/learn_theme.py --help
```

Expected: Usage message showing `url` positional arg and `--name` required arg.

- [ ] **Step 4: Add `learn-theme` subcommand to `toolkit/cli.py`**

In `toolkit/cli.py`, add the subcommand registration and handler.

Add after the `cmd_gallery` function (before `_gallery_sample_markdown`):

```python
def cmd_learn_theme(args):
    """Learn a theme from a WeChat article URL."""
    import subprocess
    script = Path(__file__).parent.parent / "scripts" / "learn_theme.py"
    cmd = [sys.executable, str(script), args.url, "--name", args.name]
    result = subprocess.run(cmd)
    sys.exit(result.returncode)
```

Add subparser registration after the `p_gallery` block (before `args = parser.parse_args()`):

```python
    # learn-theme
    p_learn = sub.add_parser("learn-theme", help="Learn formatting theme from a WeChat article URL")
    p_learn.add_argument("url", help="WeChat article URL")
    p_learn.add_argument("--name", required=True, help="Theme name")
```

Add handler in the `try` block, after the `elif args.command == "gallery":` case:

```python
        elif args.command == "learn-theme":
            cmd_learn_theme(args)
```

- [ ] **Step 5: Test CLI integration**

Run:
```bash
python3 toolkit/cli.py learn-theme --help
```

Expected: Shows usage for `learn-theme` subcommand with `url` and `--name` args.

- [ ] **Step 6: Commit**

```bash
git add scripts/learn_theme.py toolkit/cli.py
git commit -m "feat(learn-theme): add CLI with terminal report"
```

---

### Task 6: End-to-end test with real URL

**Files:** None (manual verification)

- [ ] **Step 1: Run full pipeline against the example article**

Run:
```bash
python3 scripts/learn_theme.py https://mp.weixin.qq.com/s/WRBHkWP6wdQ6Qznq-KHIYg --name test-learned
```

Expected output:
```
Fetching article...
Title: <article title>
Extracted N styled elements.

Learned theme from: <title>
  text:       #000000
  primary:    #2d71d6
  ...
Theme saved → .../toolkit/themes/test-learned.yaml
```

- [ ] **Step 2: Verify the generated theme works with preview**

Run:
```bash
python3 toolkit/cli.py preview toolkit/../docs/superpowers/specs/2026-04-01-learn-theme-design.md --theme test-learned --no-open -o /tmp/test-learned-preview.html
```

Expected: HTML file generated without errors. Open manually to inspect if desired.

- [ ] **Step 3: Verify theme appears in theme list**

Run:
```bash
python3 toolkit/cli.py themes | grep test-learned
```

Expected: Shows `test-learned` with its description.

- [ ] **Step 4: Clean up test theme**

Run:
```bash
rm toolkit/themes/test-learned.yaml
```

- [ ] **Step 5: Commit (no code changes — this is a verification task)**

No commit needed.

---

### Task 7: SKILL.md integration

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: Add "学习排版" trigger to auxiliary functions section**

In `SKILL.md`, locate the auxiliary functions block (line ~46). Add a new entry after the "学习我的修改" line:

```markdown
- 用户说"学习排版"/"学排版" → `python3 {skill_dir}/scripts/learn_theme.py <url> --name <name>`，用户需提供一个公众号文章 URL 和主题名称。提取完成后提示用户设置 `style.yaml` 的 `theme` 字段。
```

- [ ] **Step 2: Add to the Step 8.3 trigger table**

In the trigger-word table near the end of SKILL.md, add a row:

```markdown
| 学习排版 / 学排版 | `python3 {skill_dir}/scripts/learn_theme.py <url> --name <name>` |
```

- [ ] **Step 3: Commit**

```bash
git add SKILL.md
git commit -m "feat(learn-theme): add trigger words to SKILL.md"
```

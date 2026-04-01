# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WeWrite is a WeChat public account (公众号) content generation AI skill. It automates the full workflow from trending topic discovery to draft box publishing. It works as both a Claude Code skill (via SKILL.md) and an OpenClaw-compatible skill (via `dist/openclaw/`).

The core pipeline is defined in SKILL.md (Steps 1-8): environment check → topic selection → framework + material collection → writing → SEO/anti-AI verification → visual AI → formatting/publishing → wrap-up.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Toolkit CLI
python3 toolkit/cli.py preview article.md --theme sspai       # Preview as HTML
python3 toolkit/cli.py publish article.md --cover cover.png --title "标题"  # Publish to WeChat
python3 toolkit/cli.py gallery                                  # Browse all 16 themes
python3 toolkit/cli.py themes                                   # List theme names
python3 toolkit/cli.py image-post img1.jpg img2.jpg -t "标题"   # Image post (carousel)
python3 toolkit/cli.py learn-theme <url> --name <name>         # Learn theme from WeChat article

# Scoring and diagnostics
python3 scripts/humanness_score.py article.md --verbose         # AI detection scoring (11 checks, 0-1 continuous)
python3 scripts/humanness_score.py article.md --json --tier3 0.7  # With agent Tier 3 score
python3 scripts/diagnose.py                                      # Anti-AI config diagnostic
python3 scripts/diagnose.py --json                               # JSON output for agent

# Exemplar library (SICO-style few-shot)
python3 scripts/extract_exemplar.py article.md                    # Extract exemplar from article
python3 scripts/extract_exemplar.py article.md -c tech-opinion -s "账号名"  # With category + source
python3 scripts/extract_exemplar.py article1.md article2.md       # Batch import
python3 scripts/extract_exemplar.py --list                        # List exemplar library

# Data collection scripts
python3 scripts/fetch_hotspots.py --limit 20                   # Trending topics
python3 scripts/seo_keywords.py --json "关键词1" "关键词2"      # SEO keyword analysis
python3 scripts/fetch_stats.py <article_id>                     # WeChat article stats

# Build OpenClaw-compatible skill (also runs in CI on push to main)
python3 scripts/build_openclaw.py
```

No formal test suite exists. CI only rebuilds the OpenClaw version on push to main.

## Architecture

### Dual Nature: Skill + Toolkit

- **As a skill** (SKILL.md): An agent-orchestrated 8-step pipeline with TaskCreate progress tracking. The LLM reads SKILL.md and executes steps, calling Python scripts as tools. Reference docs in `references/` are loaded on-demand by the agent at specific steps.
- **As a standalone toolkit** (`toolkit/cli.py`): A Python CLI for Markdown→WeChat HTML conversion and publishing, usable independently of the skill.

### Anti-AI Detection System

Three-tier approach aligned with how detectors work (defined in `references/writing-guide.md`):
- **Tier 1 Statistical** (rules 1.1-1.6): Sentence variance, vocabulary richness, paragraph rhythm, emotion polarity, adverb density, style drift. Counters perplexity/burstiness detection.
- **Tier 2 Linguistic** (rules 2.1-2.4): Banned words, broken sentences, unexpected words, coherence breaking. Counters syntax/vocabulary fingerprinting.
- **Tier 3 Content** (rules 3.1-3.4): Real data anchoring, specificity, density waves, dimension randomization. Counters semantic analysis.

`scripts/humanness_score.py` implements Tier 1+2 programmatically (11 checks, continuous 0-1 scores). Tier 3 is done by the agent in SKILL.md Step 5.3. Each check maps to a `writing-config.yaml` parameter via the `param` field in JSON output.

### Self-Learning Flywheel

- **Scoring feedback**: Step 5.3 scores each article → Step 8.1 records `composite_score` + `writing_config_snapshot` to `history.yaml` → Step 4.1 reads historical best params for next article.
- **Edit learning**: `scripts/learn_edits.py` captures typed patterns (key/type/description/rule) with confidence scoring and 30-day decay → `playbook.md` stores rules as structured YAML → Step 4.3 applies rules gated by confidence (≥5 hard constraint, <5 soft reference, <2 pruned).
- **Parameter optimization**: "优化参数" auxiliary function in SKILL.md runs agent-driven iterative loop (write test article → score → adjust lowest params → repeat).

### Key Directories

- `scripts/` — Scoring, diagnostics, data collection, and build tools.
- `toolkit/` — Markdown→WeChat HTML converter, theme engine, WeChat API client, image generation. CLI entry point: `toolkit/cli.py`.
- `personas/` — 5 YAML writing personality presets controlling tone, data presentation, emotional arc.
- `references/` — Agent-loaded instruction docs (writing rules, frameworks, SEO, topic scoring). NOT code.
- `toolkit/themes/` — 16 YAML theme definitions, applied as inline CSS.

### Configuration Files

- `config.yaml` (from `config.example.yaml`) — WeChat API credentials + image API key. Missing → graceful degradation (skip_publish, skip_image_gen).
- `style.yaml` (from `style.example.yaml`) — User's writing profile (name, topics, tone, persona, theme). Auto-created via onboard flow on first run.
- `writing-config.yaml` (from `writing-config.example.yaml`) — Writing parameters mapped to anti-AI rules. Optimized per-user via "优化参数" auxiliary function.
- `playbook.md` — Structured YAML rules learned from user edits, with confidence scores and decay.

All four are .gitignored — each user generates their own.

### Graceful Degradation

The pipeline never hard-fails. Missing config → skip_publish/skip_image_gen flags. Script failures → WebSearch or LLM fallback. Image gen fails → output prompts only. These flags are set in Step 1 and automatically respected by later steps.

## Language & Conventions

- All code is Python 3.11+. No type checking or linter configured.
- Commit messages use format: `type: description` (e.g., `fix: ...`, `feat: ...`, `chore: ...`).
- The project language (README, SKILL.md, comments, references) is Chinese.
- SKILL.md sub-steps use `X.Y` numbering (e.g., 1.1, 4.3, 5.2).
- VERSION file tracks releases. Bump on user-facing changes.

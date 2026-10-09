# novel-txt-reader (plugin)

English | [简体中文](README.zh-CN.md)

A portable agent skill, packaged as a Claude-compatible plugin, that turns a plain-text
`.txt` novel into a lightweight **offline HTML reader** — split by chapter, re-encoded as
UTF-8, with automatic and manual bookmarks. Usable with Claude, Codex, and DeepSeek
Harness (DSH), or directly with Python.

## Components

| Component | Name             | Purpose                                                        |
| --------- | ---------------- | -------------------------------------------------------------- |
| Skill     | novel-txt-reader | Decode strictly, split by chapter, generate the reader page.   |

## Usage

Ask your agent: "Use novel-txt-reader to turn this TXT into an offline reader; input:
your TXT path, output: your output folder" or "用 novel-txt-reader 把这个 TXT 按章节拆分成阅读器，
输入路径是……，输出到……". The host must be able to access those paths.

The skill runs `scripts/build_reader.py <input.txt> <output_folder>` (script path relative
to the directory containing `skills/novel-txt-reader/SKILL.md`, not the agent's working
directory) and produces a folder
with `开始阅读.html` (open in a browser), `使用说明.txt`, and per-chapter files under `data/`.

## Setup

Install the plugin through Claude or a compatible Codex marketplace, or copy the entire
`skills/novel-txt-reader` folder into a supported skill root. Codex and DSH can share
`~/.agents/skills/novel-txt-reader`; DSH also supports `~/.dsh/skills/novel-txt-reader`.
DSH discovers the skill rather than installing `.claude-plugin/plugin.json`.
Keep both Python and HTML files in `scripts/` with the skill.

See [COMPATIBILITY.md](../../COMPATIBILITY.md) in the full source checkout for exact setup,
official sources, and validation limits. Python 3, shell execution, input read access and output write access
are required to convert. The converter itself needs no credentials or third-party Python
packages; your agent host may have its own login requirements. Reading needs only a browser.

Ambiguous source encodings need an
explicit override, such as `--encoding big5`; invalid bytes stop conversion instead of
being silently replaced.

Version 0.1.2 validates progress imports, separates progress by book, preserves normal
prose and unrelated output files, and protects existing readers from ordinary failed
rebuilds. Back up progress before regenerating an old reader; legacy progress migration
requires confirmation. See the [repository README](../../README.md) for details and tests.

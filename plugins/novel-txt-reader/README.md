# novel-txt-reader (plugin)

A Cowork/Claude plugin that turns a plain-text `.txt` novel into a lightweight **offline
HTML reader** — split by chapter, re-encoded as UTF-8 (no 乱码), with automatic and manual
bookmarks.

## Components

| Component | Name             | Purpose                                                        |
| --------- | ---------------- | -------------------------------------------------------------- |
| Skill     | novel-txt-reader | Detect encoding, split by chapter, generate the reader page.   |

## Usage

Ask Cowork things like: "把这个 txt 小说按章节拆分成阅读器", "this .txt book shows 乱码, fix it
and make it readable with bookmarks", or drop in a `.txt` novel and ask to split it.

The skill runs `scripts/build_reader.py <input.txt> <output_folder>` and produces a folder
with `开始阅读.html` (open in a browser), `使用说明.txt`, and per-chapter files under `data/`.

## Setup

No credentials required. Optional: `pip install chardet` for better encoding detection.
Reading needs only a web browser.

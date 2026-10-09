---
name: novel-txt-reader
description: Convert a plain-text (.txt) novel or book into a lightweight offline HTML reader. Strictly handles UTF-8 / UTF-16 / GBK / GB18030 / Big5, with a manual encoding override when detection is ambiguous; splits chapters (第X章 / 第X回 / 第X节 / Chapter N, grouped by 卷/部/集, keeping 楔子/序/番外/外传) into small files and generates a reader page with a table of contents, chapter search, automatic reading progress, manual bookmarks, validated backups, themes and fonts. Use this when the user points to a .txt novel or book and wants to split it into chapters, fix garbled encoding, or read a long book with bookmarks.
license: MIT
---

# Novel TXT Reader

Turn a single (often huge) `.txt` novel into a folder you can read comfortably in any
browser — split by chapter, encoded as UTF-8, with automatic and manual bookmarks.

## When to use

Trigger this skill when the user:
- drops in / uploads / points to a `.txt` novel or book, or
- asks to split a long book "by chapter" into smaller files, or
- complains a Chinese text file shows 乱码 (garbled characters), or
- wants bookmarks / "remember where I left off" for a long book.

## How to run

```bash
python3 scripts/build_reader.py "<path/to/book.txt>" "<output_folder>"
```

- If `<output_folder>` is omitted, a folder named after the book is created next to the input.
- Output is written as UTF-8 (no BOM for the reader/data; BOM for the `.txt` guide).
- No third-party Python packages are required. UTF BOMs and strict UTF-8 are recognized;
  legacy encoding detection is conservative. If the encoding is ambiguous, conversion
  stops without replacing existing output. Inspect the source or ask which encoding to
  use, then pass `--encoding gb18030`, `--encoding big5`, or another known codec.
- Invalid input bytes are reported rather than replaced. Verify the first chapter's
  decoded text and the table of contents before treating a conversion as successful.
- Rebuilds stage managed files first and roll back ordinary replacement errors. Unrelated
  files are preserved. Keep backups for power loss or filesystem failure.

The end user needs **only a web browser** to read — no Python/Node required to read.

## What it produces

```
<output_folder>/
  开始阅读.html      ← open this in a browser (Chrome / Edge recommended)
  使用说明.txt        ← short usage notes (UTF-8 with BOM, opens cleanly in Notepad)
  .novel-txt-reader.json  ← generated-file ownership manifest; keep when moving
  data/
    catalog.js       ← book identity and table of contents (title, author, chapters)
    ch_0000.js       ← one small file per chapter (front-matter = ch_0000)
    ch_0001.js
    ...
```

The reader (`开始阅读.html`) lazy-loads **one chapter at a time** via a `<script>` tag, so it
stays fast and light even for multi-thousand-chapter books, and it works from `file://`
(no server needed). Bookmarks and settings are stored in the browser's `localStorage`.

## Reader features (what to tell the user)

- **Table of contents**: grouped by volume (卷/部/集), searchable by chapter title, jump anywhere.
- **Automatic bookmark**: reading position is saved continuously and on exit; reopening the
  page restores the chapter and scroll proportion. Failed chapter loads preserve the old
  text and position. Font or viewport changes can shift the exact visible sentence.
- **Manual bookmarks**: the 🔖 button (or the bookmarks panel) marks the current spot; jump
  back or delete anytime.
- **Prev/next + keyboard**: `←` previous chapter, `→` next chapter, `B` add bookmark.
- **Appearance**: day / eye-care(护眼) / night themes, sans/serif fonts, font size, line
  height and page width — all remembered.
- **Backup**: the bookmarks panel can export/import progress as a JSON file (useful before
  clearing browser data or moving to another device). Invalid and wrong-book backups are
  rejected before changing saved progress. The exported filename uses the actual title.

## Chapter detection

- Picks the **dominant unit** among `章 / 回 / 节 / Chapter N` (counts them and uses the most
  common) so a book with `章` + `节` sub-headings is not over-split.
- Groups chapters under volume headers `第X卷 / 第X部 / 第X集`.
- Keeps special sections: `楔子 / 序章 / 序言 / 引子 / 前言 / 尾声 / 终章 / 大结局 / 后记 /
  番外 / 外传` (grouped as 番外), with guards so mid-sentence occurrences (e.g. "厅外传来…")
  are not mistaken for headers.
- Recognizes headings conservatively. Ambiguous lines remain as text; prose containing
  URLs and separator lines are retained rather than silently removed as advertisements.
- If **no** chapter markers are found, it falls back to splitting into ~equal parts named
  「第N部分」 so the reader still works.

## Important notes for the user

- Keep `开始阅读.html` and the `data` folder **together** and unchanged; to move the book,
  move the whole folder.
- Progress lives in the browser's local storage — always open with the **same browser**, and
  use **导出进度 (export)** occasionally as a backup.
- Each book has a content-based identity. Re-encoding or moving the same text preserves
  the identity, but local-file browser storage can change when a folder moves; export
  first. Editing the text produces a different identity.
- Back up old progress before upgrading. Legacy 0.1.1 data has no book identity, so
  migration needs confirmation; its original storage is retained. Old chapter references
  that no longer match are rejected rather than silently pointed at a different chapter.
- Do **not** commit copyrighted book text to a public repo; this skill ships only the tooling
  and a tiny original sample.

## Verifying (optional, for developers)

`tests/` contains stdlib Python regression tests and real Playwright/Chromium browser
checks using synthetic books. From the repository root:

```bash
python -m unittest discover -s plugins/novel-txt-reader/skills/novel-txt-reader/tests -p "test_*.py" -v
npm ci
npx playwright install chromium
npm test
```

Use `PYTHON` and `CHROME_EXECUTABLE_PATH` to select existing runtimes. Tests compare
known Unicode text and saved positions, and cover bad backups, multiple books, failed
chapter loads, and output rollback. See the root README for the commands and limits.

---
name: novel-txt-reader
description: Convert a plain-text (.txt) novel or book into a lightweight offline HTML reader. Auto-detects the file encoding (UTF-8 / UTF-16 / GBK / GB18030 / Big5) so there is no 乱码 (garbled text), splits the book by its chapters (第X章 / 第X回 / 第X节 / Chapter N, grouped by 卷/部/集, keeping 楔子/序/番外/外传) into one small file per chapter, and generates a single self-contained reader page with a table of contents, chapter search, an automatic bookmark that resumes where the reader left off on reopen, manual bookmarks, and adjustable light/eye-care/dark themes and fonts. Use this whenever the user drops in or points to a .txt novel or book and wants to split it into chapters, fix a garbled-encoding text file, or make a very long book (especially a large Chinese web novel) easier to read with bookmarks.
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
- Optional but recommended: `pip install chardet` improves encoding auto-detection for
  unusual files. Without it, the script still handles UTF-8/UTF-16/GBK/GB18030/Big5 via a
  robust fallback ladder.

The end user needs **only a web browser** to read — no Python/Node required to read.

## What it produces

```
<output_folder>/
  开始阅读.html      ← open this in a browser (Chrome / Edge recommended)
  使用说明.txt        ← short usage notes (UTF-8 with BOM, opens cleanly in Notepad)
  data/
    catalog.js       ← table of contents (title, author, chapter list)
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
  page jumps back automatically.
- **Manual bookmarks**: the 🔖 button (or the bookmarks panel) marks the current spot; jump
  back or delete anytime.
- **Prev/next + keyboard**: `←` previous chapter, `→` next chapter, `B` add bookmark.
- **Appearance**: day / eye-care(护眼) / night themes, sans/serif fonts, font size, line
  height and page width — all remembered.
- **Backup**: the bookmarks panel can export/import progress as a JSON file (useful before
  clearing browser data or moving to another device).

## Chapter detection

- Picks the **dominant unit** among `章 / 回 / 节 / Chapter N` (counts them and uses the most
  common) so a book with `章` + `节` sub-headings is not over-split.
- Groups chapters under volume headers `第X卷 / 第X部 / 第X集`.
- Keeps special sections: `楔子 / 序章 / 序言 / 引子 / 前言 / 尾声 / 终章 / 大结局 / 后记 /
  番外 / 外传` (grouped as 番外), with guards so mid-sentence occurrences (e.g. "厅外传来…")
  are not mistaken for headers.
- If **no** chapter markers are found, it falls back to splitting into ~equal parts named
  「第N部分」 so the reader still works.

## Important notes for the user

- Keep `开始阅读.html` and the `data` folder **together** and unchanged; to move the book,
  move the whole folder.
- Progress lives in the browser's local storage — always open with the **same browser**, and
  use **导出进度 (export)** occasionally as a backup.
- Do **not** commit copyrighted book text to a public repo; this skill ships only the tooling
  and a tiny original sample.

## Verifying (optional, for developers)

`tests/` contains an automated check that builds several synthetic books (different encodings
and chapter styles) and runs the reader in a headless DOM to confirm chapters load, there is
no 乱码, and bookmarks/auto-resume work. Requires Node + `npm i jsdom`:

```bash
bash tests/run_tests.sh
```

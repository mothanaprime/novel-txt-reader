# novel-txt-reader

A reusable **Claude / Cowork skill** (and standalone Python script) that turns a single,
often huge `.txt` novel into a lightweight **offline HTML reader** — split by chapter,
re-encoded as UTF-8 (no more 乱码), with **automatic and manual bookmarks**.

Built for large Chinese web novels (thousands of chapters), but works for any `.txt` book.

## Why

A 10–20 MB novel in one `.txt` file is painful: it opens slowly, often shows garbled
characters (wrong encoding), and there's no way to remember where you stopped. This tool
fixes all three.

## Quick start

```bash
# 1) (optional) better encoding detection
pip install chardet

# 2) build a reader from any .txt book
python3 scripts/build_reader.py "path/to/your-book.txt" "path/to/output-folder"

# 3) open output-folder/开始阅读.html in Chrome / Edge and read
```

Try it on the included sample:

```bash
python3 scripts/build_reader.py examples/sample.txt out/
# then open out/开始阅读.html
```

## Features

- **Encoding auto-detect** → UTF-8 output: UTF-8, UTF-8-BOM, UTF-16, GBK, GB18030, Big5.
- **Smart chapter split**: dominant unit among `第X章 / 第X回 / 第X节 / Chapter N`, grouped by
  `卷/部/集`, keeping `楔子/序/番外/外传`; size-based fallback when a book has no markers.
- **One small file per chapter** → the reader lazy-loads a single chapter at a time and stays
  fast even for 2000+ chapters. Works from `file://`, no server needed.
- **Automatic bookmark**: resumes exactly where you left off when you reopen the page.
- **Manual bookmarks**: mark/jump/delete; plus export/import progress as JSON.
- **Comfort**: table of contents + search, day / eye-care / night themes, adjustable font,
  line height and width — all remembered.

## Output layout

```
output-folder/
  开始阅读.html      # the reader — open in a browser
  使用说明.txt        # short usage notes (Chinese)
  data/
    catalog.js       # table of contents
    ch_0000.js ...   # one file per chapter
```

## How it works

`scripts/build_reader.py` parses the book and writes each chapter as
`window.__CH__({...})` in its own `data/ch_XXXX.js`, plus a `catalog.js` index. The reader
(`scripts/reader_template.html`, copied to `开始阅读.html`) injects a `<script>` tag to load
just the current chapter, renders it, and persists reading position, bookmarks and settings
in `localStorage`.

## Development / tests

```bash
npm install jsdom          # dev dependency for the test harness
bash tests/run_tests.sh    # builds synthetic books and runs the reader headlessly
```

The tests cover GB18030 / UTF-16 / Big5 / UTF-8 and 章 / 回 / Chapter / no-marker layouts,
asserting correct chapter counts, no 乱码, working bookmarks and auto-resume.

## Install as a Cowork/Claude skill

Copy this folder into your skills directory, or package it:

```bash
# using the skill-creator packager, or simply zip the folder as <name>.skill
```

Then enable it in **Settings → Capabilities**.

## License

MIT — see [LICENSE](LICENSE). Ships only tooling and a tiny original sample; do not add
copyrighted book text to a public repository.

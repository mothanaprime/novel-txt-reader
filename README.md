# novel-txt-reader

An installable **Cowork/Claude plugin** (also usable as a standalone skill or script) that
turns a single, often huge `.txt` novel into a lightweight **offline HTML reader** — split by
chapter, re-encoded as UTF-8, with **automatic and manual bookmarks**.

Built for large Chinese web novels (thousands of chapters), but works for any `.txt` book.

This repo is a **plugin marketplace**: `/.claude-plugin/marketplace.json` lists one plugin,
`plugins/novel-txt-reader`, which contains the `novel-txt-reader` skill.

## Install

### A) As a plugin, from GitHub (recommended)

Add this repo as a marketplace, then install the plugin:

```
/plugin marketplace add mothanaprime/novel-txt-reader
/plugin install novel-txt-reader@novel-txt-reader
```

In **Cowork**: open **Settings → Capabilities**, add a plugin/marketplace by URL and point it
at `https://github.com/mothanaprime/novel-txt-reader`, then enable **novel-txt-reader**.

### B) Use the script directly (no install)

```bash
python3 plugins/novel-txt-reader/skills/novel-txt-reader/scripts/build_reader.py \
        "path/to/your-book.txt" "path/to/output-folder"
# then open output-folder/开始阅读.html in Chrome / Edge
```

Try it on the bundled sample:

```bash
cd plugins/novel-txt-reader/skills/novel-txt-reader
python3 scripts/build_reader.py examples/sample.txt out/
```

No Python packages are required. On Windows, use `python` in place of `python3`.
If encoding cannot be identified confidently, conversion stops before changing an
existing reader. Specify the source encoding explicitly, for example:

```bash
python3 scripts/build_reader.py book.txt out/ --encoding big5
```

中文快速开始：把 TXT 路径和输出文件夹传给脚本，再双击输出中的「开始阅读.html」。
遇到编码不确定的提示时，可用 `--encoding gb18030` 或 `--encoding big5` 指定编码。
转换后先核对前几章的文字和目录。正文中的网址及分隔行会保留，不再自动当作广告删除。

## Features

- **Strict encoding handling** → UTF-8 output: UTF-8, UTF-8-BOM, UTF-16 with BOM,
  GBK, GB18030, Big5. Ambiguous legacy text requires `--encoding`; invalid bytes are
  reported instead of silently replaced.
- **Smart chapter split**: dominant unit among `第X章 / 第X回 / 第X节 / Chapter N`, grouped by
  `卷/部/集`, keeping `楔子/序/番外/外传`; size-based fallback when a book has no markers.
- **One small file per chapter** → the reader lazy-loads a single chapter at a time and stays
  fast even for 2000+ chapters. Works from `file://`, no server needed.
- **Automatic bookmark**: resumes the chapter and scroll proportion on reopen;
  chapter-load failures preserve the previous text and reading position.
- **Manual bookmarks**: mark / jump / delete; validated JSON backups for each book.
  Invalid or wrong-book imports leave existing progress untouched.
- **Comfort**: table of contents + search, day / eye-care / night themes, adjustable font,
  line height and width — all remembered.

## Updating an existing reader

Re-run the new script on the same TXT and output folder to update the generated page.
The builder stages its managed files before replacing them, preserves unrelated files,
and rolls back ordinary write/replace errors. Keep an external backup for power loss
or disk failure; a multi-file replacement is not a filesystem-wide atomic transaction.

Progress is separated by a content-based book ID. Moving or re-encoding unchanged text
keeps that ID; editing the text creates a different book. Browser storage for local
files may change when a folder moves, so export progress first and import it afterwards.
Legacy 0.1.1 progress has no book ID and requires confirmation before migration.
Its original storage is preserved. Back up progress before upgrading; chapter parsing
changes can make an old bookmark incompatible and such data is rejected, not guessed.

Reading position uses a scroll proportion, so changing font size, viewport or device
may shift the exact visible sentence. No accounts or network service are needed to read.

## Output layout

```
output-folder/
  开始阅读.html      # the reader — open in a browser
  使用说明.txt        # short usage notes (Chinese)
  .novel-txt-reader.json  # generated-file ownership manifest; keep with the reader
  data/
    catalog.js       # book identity and table of contents
    ch_0000.js ...   # one file per chapter
```

## Repo layout

```
.
├── .claude-plugin/marketplace.json          # marketplace manifest (add by URL)
├── plugins/
│   └── novel-txt-reader/
│       ├── .claude-plugin/plugin.json        # plugin manifest
│       ├── README.md
│       └── skills/novel-txt-reader/
│           ├── SKILL.md
│           ├── scripts/{build_reader.py, reader_template.html}
│           ├── examples/sample.txt
│           └── tests/                      # Python and browser regressions
├── README.md
└── LICENSE
```

## Development / tests

Run the Python tests from the repository root without extra dependencies:

```bash
python -m unittest discover -s plugins/novel-txt-reader/skills/novel-txt-reader/tests -p "test_*.py" -v
```

Browser tests use pinned Playwright and a real Chromium browser. They exercise actual
`file://` loading plus isolated local HTTP fixtures for multi-book storage and load
failures. All books are synthetic; no copyrighted novel text is required.

```bash
npm ci
npx playwright install chromium
npm test
```

`npm run test:python` and `npm run test:browser` run the suites separately. Set `PYTHON`
to a Python executable when needed; set `CHROME_EXECUTABLE_PATH` to reuse an installed
Chrome instead of downloading Chromium. CI runs the suites on Linux and Windows.

Tests assert known Unicode text and expected chapter counts, valid progress round trips,
failed imports preserving stored state, exact saved chapter/scroll restoration under
unchanged layout, and rebuild rollback. See [CHANGELOG.md](CHANGELOG.md) for the 0.1.2 fixes.

## License

MIT — see [LICENSE](LICENSE). Ships only tooling and a tiny original sample; do not add
copyrighted book text to a public repository.

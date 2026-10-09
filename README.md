# novel-txt-reader

English | [简体中文](README.zh-CN.md)

A portable **agent skill and Python script**, packaged as a Claude-compatible plugin,
that turns a single, often huge `.txt` novel into a lightweight **offline HTML reader** —
split by chapter, re-encoded as UTF-8, with **automatic and manual bookmarks**.

Built for large Chinese web novels (thousands of chapters), but works for any `.txt` book.

Works with **Claude, Codex, and DeepSeek Harness (DSH)** when the host can run Python
and access the input/output folders. Conversion does not depend on a particular model.

| Host | How to use it |
| --- | --- |
| Claude Code / Cowork | Install the Claude-compatible plugin. |
| Codex | Use the compatible plugin marketplace, or install the standalone skill. |
| DeepSeek Harness (DSH) | Install the standalone skill in `.agents/skills` or `.dsh/skills`. |
| No agent | Run the Python script directly. |

See [COMPATIBILITY.md](COMPATIBILITY.md) for installation commands, shared Codex/DSH
skill setup, prerequisites, official sources, and what has actually been tested.

中文：Claude、Codex 和 DeepSeek 官方 DSH 都可使用。Codex 与 DSH 可共用一份完整的
skill 目录；DSH 不通过 Claude 的插件清单安装。生成阅读器需要 Python，阅读只需浏览器。

This repo is also a **plugin marketplace**: `.claude-plugin/marketplace.json` lists
`plugins/novel-txt-reader`, which contains the `novel-txt-reader` skill. This guide covers
**0.1.2**. Use the [v0.1.2 release](https://github.com/mothanaprime/novel-txt-reader/releases/tag/v0.1.2)
for versioned source; installing from `main` follows the repository's current default
branch, which can advance after a release.

## Install

### A) Claude Code / Cowork plugin

Add this repo as a marketplace, then install the plugin:

```
/plugin marketplace add mothanaprime/novel-txt-reader
/plugin install novel-txt-reader@novel-txt-reader
```

In Claude Code, finish the scope/install selection if the command opens a details page.
In **Cowork**, use the plugin management UI to add
`https://github.com/mothanaprime/novel-txt-reader`, then install and enable
**novel-txt-reader**. Menu names can vary by client version.

### B) Codex / DeepSeek Harness (DSH)

Both support the complete `plugins/novel-txt-reader/skills/novel-txt-reader` folder as
a standalone skill. Copy that folder to `~/.agents/skills/novel-txt-reader` to share it
between Codex and DSH. Keep `scripts/`, including `reader_template.html`, with `SKILL.md`.
Then ask the agent to use **novel-txt-reader** with your TXT and output paths.

Codex also supports the Claude-compatible marketplace packaging. See the
[installation guide](COMPATIBILITY.md) for that route, project-local setup, and DSH details.

### C) Use the script directly (no install)

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

These examples run from the repository root or the skill directory after the shown `cd`.
From elsewhere, use an absolute script path. No Python packages are required. On Windows,
use a working Python 3 command such as `python` or `py -3` in place of `python3`.
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
├── README.zh-CN.md                         # Chinese usage guide
├── COMPATIBILITY.md                       # Claude, Codex, and DSH installation
├── COMPATIBILITY.zh-CN.md                  # Chinese installation guide
├── CHANGELOG.md
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

## Branches and releases

Claude, Codex, and DSH use one shared codebase on `main`; they are installation routes,
not separate product branches. Merge short-lived fix/feature branches through a reviewed,
passing PR. Before publishing, synchronize the manifest versions and changelog, then tag
the chosen commit (for example `v0.1.2`) and create its Release. Git history and release
tags retain older versions. Merging to `main` and publishing a Release are separate steps.
Keep the English and Chinese documentation together and update both when behavior changes.

## License

MIT — see [LICENSE](LICENSE). Ships only tooling and a tiny original sample; do not add
copyrighted book text to a public repository.

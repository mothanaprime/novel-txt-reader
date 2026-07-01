# novel-txt-reader

An installable **Cowork/Claude plugin** (also usable as a standalone skill or script) that
turns a single, often huge `.txt` novel into a lightweight **offline HTML reader** — split by
chapter, re-encoded as UTF-8 (no more 乱码), with **automatic and manual bookmarks**.

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
pip install chardet   # optional, better encoding detection
python3 plugins/novel-txt-reader/skills/novel-txt-reader/scripts/build_reader.py \
        "path/to/your-book.txt" "path/to/output-folder"
# then open output-folder/开始阅读.html in Chrome / Edge
```

Try it on the bundled sample:

```bash
cd plugins/novel-txt-reader/skills/novel-txt-reader
python3 scripts/build_reader.py examples/sample.txt out/
```

## Features

- **Encoding auto-detect** → UTF-8 output: UTF-8, UTF-8-BOM, UTF-16, GBK, GB18030, Big5.
- **Smart chapter split**: dominant unit among `第X章 / 第X回 / 第X节 / Chapter N`, grouped by
  `卷/部/集`, keeping `楔子/序/番外/外传`; size-based fallback when a book has no markers.
- **One small file per chapter** → the reader lazy-loads a single chapter at a time and stays
  fast even for 2000+ chapters. Works from `file://`, no server needed.
- **Automatic bookmark**: resumes exactly where you left off when you reopen the page.
- **Manual bookmarks**: mark / jump / delete; export/import progress as JSON.
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
│           └── tests/{make_samples.py, test_reader.js, run_tests.sh}
├── README.md
└── LICENSE
```

## Development / tests

```bash
cd plugins/novel-txt-reader/skills/novel-txt-reader
npm install jsdom          # dev dependency for the headless test harness
bash tests/run_tests.sh    # builds synthetic books and verifies the reader
```

The tests cover GB18030 / UTF-16 / Big5 / UTF-8 and 章 / 回 / Chapter / no-marker layouts,
asserting correct chapter counts, no 乱码, working bookmarks and auto-resume.

## License

MIT — see [LICENSE](LICENSE). Ships only tooling and a tiny original sample; do not add
copyrighted book text to a public repository.

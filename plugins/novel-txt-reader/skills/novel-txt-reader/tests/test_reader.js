'use strict';

// Real Chromium regressions: synthetic/public-domain fixtures only, isolated browser
// contexts, no user profile. Most checks use file://; HTTP is local and used only
// where a shared origin or a controlled missing chapter is needed.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const {pathToFileURL} = require('node:url');
const {spawnSync} = require('node:child_process');
const {test, before, after} = require('node:test');
const {chromium} = require('playwright');

const skill = path.resolve(__dirname, '..');
const python = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
const fixtures = new Map();
let work, browser, server, origin;
const missingPaths = new Set();

function runPython(args) {
  const result = spawnSync(python, ['-S', ...args], {encoding: 'utf8',
    env: {...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1'}});
  if (result.error) throw result.error;
  assert.equal(result.status, 0, `Python failed: ${result.stdout}\n${result.stderr}`);
}

function build(name, input) {
  const dir = path.join(work, 'books', name);
  runPython([path.join(skill, 'scripts/build_reader.py'), input, dir]);
  const script = fs.readFileSync(path.join(dir, 'data/catalog.js'), 'utf8');
  const catalog = JSON.parse(script.slice(script.indexOf('=') + 1).trim().replace(/;$/, ''));
  assert.match(catalog.bookId, /^[a-f0-9]{64}$/, `${name}: stable content ID`);
  const book = {name, dir, catalog, key: `novel-txt-reader.v2.${catalog.bookId}`,
    fileUrl: pathToFileURL(path.join(dir, '开始阅读.html')).href};
  fixtures.set(name, book);
  return book;
}

function synthetic(name, chapterCount) {
  const input = path.join(work, `${name}.txt`);
  const paragraphs = Array.from({length: chapterCount === 1 ? 45 : 90}, (_, i) =>
    `段落${i + 1}：这是${name}的原创回归测试。窗外的海风吹过灯塔，旅人认真记录星空。`);
  const text = Array.from({length: chapterCount}, (_, i) =>
    `第${i + 1}章 测试${i + 1}\n${paragraphs.join('\n')}\n`).join('\n');
  fs.writeFileSync(input, text);
  return build(name, input);
}

before(async () => {
  work = fs.mkdtempSync(path.join(os.tmpdir(), 'novel-reader-test-'));
  runPython([path.join(__dirname, 'make_samples.py'), path.join(work, 'samples')]);
  for (const name of fs.readdirSync(path.join(work, 'samples'))) {
    build(path.basename(name, '.txt'), path.join(work, 'samples', name));
  }
  build('sample', path.join(skill, 'examples/sample.txt'));
  synthetic('测试甲', 3);
  synthetic('测试乙', 3);
  synthetic('单章测试', 1);
  browser = await chromium.launch({headless: true,
    ...(process.env.CHROME_EXECUTABLE_PATH ? {executablePath: process.env.CHROME_EXECUTABLE_PATH} : {})});
  server = http.createServer((req, res) => {
    const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    const root = path.join(work, 'books');
    const file = path.resolve(root, `.${pathname}`);
    if (missingPaths.has(pathname) || !file.startsWith(root + path.sep) || !fs.existsSync(file)) {
      res.writeHead(404).end('Fixture not found');
      return;
    }
    res.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript; charset=utf-8' : 'text/html; charset=utf-8');
    res.setHeader('Cache-Control', 'no-store');
    res.end(fs.readFileSync(file));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  origin = `http://127.0.0.1:${server.address().port}`;
});

after(async () => {
  if (browser) await browser.close();
  if (server) await new Promise(resolve => server.close(resolve));
  if (work) {
    const cleanupTarget = path.resolve(work);
    assert.equal(path.dirname(cleanupTarget), path.resolve(os.tmpdir()));
    assert.ok(path.basename(cleanupTarget).startsWith('novel-reader-test-'));
    fs.rmSync(cleanupTarget, {recursive: true, force: true});
  }
});

async function isolated(callback) {
  const context = await browser.newContext({viewport: {width: 1000, height: 700}, acceptDownloads: true});
  const errors = [];
  context.on('page', page => page.on('pageerror', error => errors.push(error.message)));
  try {
    await callback(context);
    assert.deepEqual(errors, [], 'No uncaught reader errors');
  } finally {
    await context.close();
  }
}

async function readState(page, book) {
  return page.evaluate(key => JSON.parse(localStorage.getItem(key)), book.key);
}

async function open(page, book, protocol = 'file') {
  const url = protocol === 'file' ? book.fileUrl : `${origin}/${encodeURIComponent(book.name)}/开始阅读.html`;
  await page.goto(url);
  await page.waitForFunction(key => {
    const state = JSON.parse(localStorage.getItem(key));
    return state && state.auto && document.querySelector('#article h1');
  }, book.key);
}

async function chapter(page, book, index) {
  await page.locator('#btnToc').click();
  await page.locator(`.tocItem[data-idx="${index}"]`).click();
  await page.waitForFunction(({key, index, title}) => {
    const state = JSON.parse(localStorage.getItem(key));
    return state.auto.i === index && document.querySelector('#article h1')?.textContent === title;
  }, {key: book.key, index, title: book.catalog.entries[index].t});
}

async function scroll(page, book, ratio) {
  // The UI throttles scroll saves; avoid making consecutive gestures inside that
  // throttle interval. Wait for the actual persisted ratio, not just a heading.
  await page.waitForTimeout(450);
  await page.evaluate(r => {
    const el = document.scrollingElement;
    window.scrollTo(0, (el.scrollHeight - el.clientHeight) * r);
  }, ratio);
  await page.waitForFunction(({key, ratio}) =>
    Math.abs(JSON.parse(localStorage.getItem(key)).auto.r - ratio) < 0.01,
  {key: book.key, ratio});
}

async function exportBackup(page) {
  if (!await page.locator('#marksPanel').evaluate(el => el.classList.contains('open'))) {
    await page.locator('#btnMarks').click();
  }
  const downloadEvent = page.waitForEvent('download');
  await page.locator('#exportBtn').click();
  const download = await downloadEvent;
  const data = JSON.parse(fs.readFileSync(await download.path(), 'utf8'));
  return {data, filename: download.suggestedFilename()};
}

async function importBackup(page, data, expected) {
  await page.locator('#importFile').setInputFiles({name: 'progress.json', mimeType: 'application/json',
    buffer: Buffer.from(typeof data === 'string' ? data : JSON.stringify(data))});
  await page.waitForFunction(expected => document.querySelector('#toast').textContent.includes(expected), expected);
}

test('file:// fixtures render exact Unicode text and expected chapter structure', async () => {
  const cases = [
    ['gbk_hui', ['内容简介', '第一回 楔子之前', '第二回 群雄并起', '第三回 风云再起'], 3, '又过了三年。'],
    ['utf8bom_zhang', ['内容简介', '第一章 起点', '第二章 成长', '番外 后日谈'], 1, '主角登场了。'],
    ['utf16_en', ['Chapter 1 The Beginning', 'Chapter 2 The Middle'], 1, 'Then came the dawn.'],
    ['big5', ['第一章 開始', '第二章 繼續'], 1, '主角繼續前進。'],
    ['tricky', ['第一章 相遇', '第二章 别离'], 0, '片刻后，厅外传来了脚步之声。'],
    ['sample', ['内容简介', '第一章 小镇的夜', '第二章 老人的地图', '第三章 灯塔之下', '番外 多年以后'],
      1, '林川坐在屋顶上，望着满天繁星。'],
  ];
  for (const [name, headings, index, paragraph] of cases) {
    await isolated(async context => {
      const book = fixtures.get(name), page = await context.newPage();
      assert.deepEqual(book.catalog.entries.map(e => e.t), headings, `${name}: complete chapter list`);
      await open(page, book);
      assert.equal(await page.locator('#bookTitle').textContent(), book.catalog.title);
      await chapter(page, book, index);
      assert.equal(await page.locator('#article p').first().textContent(), paragraph, `${name}: exact decoded text`);
    });
  }
  await isolated(async context => {
    const page = await context.newPage(), book = fixtures.get('nomarker');
    await open(page, book);
    const expected = '这是没有章节标记的长文本段落。'.repeat(3);
    let totalParagraphs = 0;
    for (let i = 0; i < book.catalog.entries.length; i++) {
      await chapter(page, book, i);
      const paragraphs = await page.locator('#article p').allTextContents();
      assert.ok(paragraphs.every(p => p === expected), 'Fallback split preserves every paragraph');
      totalParagraphs += paragraphs.length;
    }
    assert.equal(totalParagraphs, 400);
  });
});

test('file:// reopens the saved chapter and scroll position with marks and theme', async () => {
  await isolated(async context => {
    const book = fixtures.get('测试甲');
    let page = await context.newPage();
    await open(page, book);
    await chapter(page, book, 1);
    await scroll(page, book, 0.47);
    await page.locator('#fabMark').click();
    await page.locator('#btnSettings').click();
    await page.locator('#themeSeg [data-theme="night"]').click();
    const before = await readState(page, book);
    assert.equal(before.auto.i, 1);
    assert.equal(before.marks.length, 1);
    await page.close();
    page = await context.newPage();
    await open(page, book);
    const after = await readState(page, book);
    assert.equal(await page.locator('#article h1').textContent(), book.catalog.entries[1].t);
    assert.equal(after.auto.i, 1, 'Resume must restore saved chapter, not merely any heading');
    assert.ok(Math.abs(after.auto.r - before.auto.r) < 0.01, 'Saved scroll position restored');
    assert.deepEqual(after.marks, before.marks);
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'night');
    assert.ok(await page.locator('script[src*="data/ch_"]').count() <= 1, 'Chapter scripts do not accumulate');
  });
});

test('invalid imports preserve existing marks/settings and reject every unsafe field shape', async () => {
  await isolated(async context => {
    const book = fixtures.get('测试甲'), page = await context.newPage();
    await open(page, book);
    await page.locator('#fabMark').click();
    const {data: backup} = await exportBackup(page);
    const mutations = [
      d => { d.app = 'unknown-reader'; },
      d => { d.v = 1; },
      d => { d.bookId = '0'.repeat(64); },
      d => { delete d.auto; },
      d => { d.auto.i = -1; },
      d => { d.auto.i = book.catalog.entries.length; },
      d => { d.auto.i = '1'; },
      d => { d.auto.r = 1.01; },
      d => { d.auto.r = 'half'; },
      d => { d.auto.t = -1; },
      d => { d.auto.title = 'Wrong chapter title'; },
      d => { d.marks = [{}]; },
      d => { d.marks[0].id = 'not-a-timestamp'; },
      d => { d.marks[0].i = 'chapter-one'; },
      d => { d.marks[0].r = 'position'; },
      d => { d.marks[0].title = {}; },
      d => { d.marks[0].snip = []; },
      d => { d.marks.push({...d.marks[0]}); },
      d => { d.settings.theme = 'unknown'; },
      d => { d.settings.fs = 500; },
      d => { delete d.settings.font; },
      d => { d.exported = 'today'; },
      d => { d.unexpected = true; },
    ];
    const baseline = await readState(page, book);
    for (const mutate of mutations) {
      const data = structuredClone(backup);
      mutate(data);
      await page.evaluate(() => { document.querySelector('#toast').textContent = ''; });
      await importBackup(page, data, '导入失败');
      const after = await readState(page, book);
      assert.deepEqual(after.marks, baseline.marks, `Rejected mutation: ${mutate}`);
      assert.deepEqual(after.settings, baseline.settings);
      assert.equal(after.auto.i, baseline.auto.i);
      assert.equal(after.auto.r, baseline.auto.r);
      assert.equal(await page.locator('.markCard').count(), 1);
    }
    await page.evaluate(() => { document.querySelector('#toast').textContent = ''; });
    await importBackup(page, '{invalid JSON', '导入失败');
    assert.deepEqual((await readState(page, book)).marks, baseline.marks);
  });
});

test('backup roundtrip uses actual title, restores full state, and blocks a foreign book', async () => {
  let backup;
  const book = fixtures.get('测试甲');
  await isolated(async context => {
    const page = await context.newPage();
    await open(page, book);
    await chapter(page, book, 1);
    await scroll(page, book, 0.42);
    await page.locator('#fabMark').click();
    await page.locator('#btnSettings').click();
    await page.locator('#themeSeg [data-theme="eye"]').click();
    await page.locator('#setPanel [data-close]').click();
    const result = await exportBackup(page);
    backup = result.data;
    assert.equal(result.filename, `${book.catalog.title}-阅读进度.json`);
    assert.equal(backup.app, 'novel-txt-reader');
    assert.equal(backup.v, 2);
    assert.equal(backup.bookId, book.catalog.bookId);
    assert.equal(backup.auto.i, 1);
  });
  await isolated(async context => {
    const page = await context.newPage();
    await open(page, book);
    await importBackup(page, backup, '已导入');
    await page.waitForFunction(title => document.querySelector('#article h1').textContent === title,
      book.catalog.entries[1].t);
    await page.waitForFunction(({key, ratio}) =>
      Math.abs(JSON.parse(localStorage.getItem(key)).auto.r - ratio) < 0.01,
    {key: book.key, ratio: backup.auto.r});
    const state = await readState(page, book);
    assert.deepEqual(state.marks, backup.marks);
    assert.deepEqual(state.settings, backup.settings);
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'eye');
  });
  await isolated(async context => {
    const other = fixtures.get('测试乙'), page = await context.newPage();
    await open(page, other);
    await page.locator('#fabMark').click();
    const before = await readState(page, other);
    await importBackup(page, backup, '导入失败');
    assert.deepEqual((await readState(page, other)).marks, before.marks);
    assert.equal((await readState(page, other)).auto.i, 0);
  });
});

test('same-origin books have separate progress, bookmarks and settings', async () => {
  await isolated(async context => {
    const first = fixtures.get('测试甲'), second = fixtures.get('测试乙');
    const page = await context.newPage();
    await open(page, first, 'http');
    await chapter(page, first, 2);
    await page.locator('#fabMark').click();
    await page.locator('#btnSettings').click();
    await page.locator('#themeSeg [data-theme="night"]').click();
    const saved = await readState(page, first);
    await open(page, second, 'http');
    const fresh = await readState(page, second);
    assert.notEqual(first.key, second.key);
    assert.equal(fresh.auto.i, 0);
    assert.deepEqual(fresh.marks, []);
    assert.equal(fresh.settings.theme, 'day');
    await page.locator('#fabMark').click();
    await open(page, first, 'http');
    assert.equal((await readState(page, first)).auto.i, 2);
    assert.deepEqual((await readState(page, first)).marks, saved.marks);
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'night');
  });
});

test('storage failure during import preserves persisted data and the current page', async () => {
  await isolated(async context => {
    const book = fixtures.get('测试甲'), page = await context.newPage();
    await open(page, book);
    await page.locator('#fabMark').click();
    const {data: backup} = await exportBackup(page);
    backup.auto = {...backup.auto, i: 1, title: book.catalog.entries[1].t, r: 0.4};
    backup.settings.theme = 'night';
    const before = await page.evaluate(key => localStorage.getItem(key), book.key);
    const article = await page.locator('#article').innerHTML();
    await page.evaluate(() => {
      Storage.prototype.setItem = function() { throw new DOMException('Synthetic quota failure', 'QuotaExceededError'); };
    });
    await importBackup(page, backup, '保存失败');
    assert.equal(await page.evaluate(key => localStorage.getItem(key), book.key), before);
    assert.equal(await page.locator('#article').innerHTML(), article);
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'day');
    assert.equal(await page.locator('.markCard').count(), 1);
    const {data: after} = await exportBackup(page);
    assert.deepEqual(after.marks, JSON.parse(before).marks, 'In-memory marks remain unchanged too');
    assert.equal(after.auto.i, 0);
  });
});

test('corrupt stored records survive boot and autosave until a valid backup replaces them', async () => {
  await isolated(async context => {
    const book = fixtures.get('测试甲'), page = await context.newPage();
    await open(page, book);
    await page.locator('#fabMark').click();
    const {data: backup} = await exportBackup(page);
    const corrupt = {...backup, marks: [{}]};
    delete corrupt.exported;
    const raw = JSON.stringify(corrupt);
    await page.addInitScript(({key, raw}) => localStorage.setItem(key, raw), {key: book.key, raw});
    await page.reload();
    await page.waitForSelector('#article h1');
    await page.waitForTimeout(5200);
    assert.equal(await page.evaluate(key => localStorage.getItem(key), book.key), raw,
      'Boot and periodic saves must not erase recoverable corrupt data');
    await importBackup(page, backup, '已导入');
    assert.deepEqual((await readState(page, book)).marks, backup.marks);
  });
});

test('legacy backups require an explicit confirmation before replacing progress', async () => {
  let backup;
  const book = fixtures.get('测试甲');
  await isolated(async context => {
    const page = await context.newPage();
    await open(page, book);
    await chapter(page, book, 1);
    await page.locator('#fabMark').click();
    backup = (await exportBackup(page)).data;
    backup.app = 'fanren-reader';
    backup.v = 1;
    delete backup.bookId;
  });
  await isolated(async context => {
    const page = await context.newPage();
    await open(page, book);
    const before = await readState(page, book);
    let prompts = 0;
    page.once('dialog', async dialog => { prompts++; await dialog.dismiss(); });
    await importBackup(page, backup, '已取消');
    assert.equal(prompts, 1);
    assert.deepEqual((await readState(page, book)).marks, before.marks);
    assert.equal((await readState(page, book)).auto.i, 0);
    page.once('dialog', async dialog => { prompts++; await dialog.accept(); });
    await importBackup(page, backup, '已导入');
    assert.equal(prompts, 2);
    assert.deepEqual((await readState(page, book)).marks, backup.marks);
    assert.equal((await readState(page, book)).auto.i, 1);
  });
});

test('accepted bookmark snippets render as literal text, never markup', async () => {
  await isolated(async context => {
    const book = fixtures.get('测试甲'), page = await context.newPage();
    await open(page, book);
    await page.locator('#fabMark').click();
    const {data: backup} = await exportBackup(page);
    const snippet = '<em data-regression="literal">只是文字</em> & "引号"';
    backup.marks[0].snip = snippet;
    await importBackup(page, backup, '已导入');
    assert.ok((await page.locator('.markCard .ms').textContent()).includes(snippet));
    assert.equal(await page.locator('[data-regression="literal"]').count(), 0);
  });
});

test('legacy localStorage migration preserves original records on accept and dismiss', async () => {
  const book = fixtures.get('测试甲');
  let legacy;
  await isolated(async context => {
    const page = await context.newPage();
    await open(page, book);
    await chapter(page, book, 1);
    await page.locator('#fabMark').click();
    const saved = await readState(page, book);
    legacy = {
      'fanren.v1.auto': JSON.stringify(saved.auto, null, 2),
      'fanren.v1.marks': JSON.stringify(saved.marks, null, 2),
      'fanren.v1.settings': JSON.stringify(saved.settings, null, 2),
    };
  });
  for (const accept of [false, true]) {
    await isolated(async context => {
      const page = await context.newPage();
      await page.addInitScript(records => {
        for (const [key, raw] of Object.entries(records)) localStorage.setItem(key, raw);
      }, legacy);
      let prompts = 0;
      page.once('dialog', async dialog => {
        prompts++;
        if (accept) await dialog.accept(); else await dialog.dismiss();
      });
      await open(page, book);
      assert.equal(prompts, 1, 'Matching chapter names still require confirmation');
      const state = await readState(page, book);
      assert.equal(state.auto.i, accept ? 1 : 0);
      assert.deepEqual(state.marks, accept ? JSON.parse(legacy['fanren.v1.marks']) : []);
      for (const [key, raw] of Object.entries(legacy)) {
        assert.equal(await page.evaluate(key => localStorage.getItem(key), key), raw);
      }
    });
  }
});

test('a valid backup larger than 2 MiB survives export and reimport', async () => {
  const book = fixtures.get('测试甲');
  let backup;
  await isolated(async context => {
    const page = await context.newPage();
    await open(page, book);
    await page.locator('#fabMark').click();
    backup = (await exportBackup(page)).data;
    const seed = backup.marks[0];
    backup.marks = Array.from({length: 800}, (_, i) => ({...seed,
      id: seed.id + i, snip: '星'.repeat(950)}));
    assert.ok(Buffer.byteLength(JSON.stringify(backup)) > 2 * 1024 * 1024);
    await importBackup(page, backup, '已导入');
    backup = (await exportBackup(page)).data;
    assert.equal(backup.marks.length, 800);
    assert.ok(Buffer.byteLength(JSON.stringify(backup)) > 2 * 1024 * 1024);
  });
  await isolated(async context => {
    const page = await context.newPage();
    await open(page, book);
    await importBackup(page, backup, '已导入');
    assert.deepEqual((await readState(page, book)).marks, backup.marks);
  });
});

test('a missing next chapter preserves readable content and persisted scroll position', async () => {
  await isolated(async context => {
    const book = fixtures.get('测试甲'), page = await context.newPage();
    await open(page, book, 'http');
    await scroll(page, book, 0.53);
    const before = await readState(page, book);
    const article = await page.locator('#article').innerHTML();
    const missing = `/${book.name}/data/ch_0001.js`;
    missingPaths.add(missing);
    try {
      // Keyboard keeps scroll position unchanged; clicking the bottom pager would
      // first scroll the current chapter to its end as a real browser must do.
      await page.keyboard.press('ArrowRight');
      await page.waitForFunction(() => document.body.textContent.includes('加载失败'));
      await page.waitForTimeout(5200); // exercise interval auto-save after failure
      const after = await readState(page, book);
      assert.equal(await page.locator('#article').innerHTML(), article);
      assert.equal(after.auto.i, before.auto.i);
      assert.ok(Math.abs(after.auto.r - before.auto.r) < 0.005, 'Failure must preserve original position');
    } finally {
      missingPaths.delete(missing);
    }
    await page.keyboard.press('ArrowRight');
    await page.waitForFunction(title => document.querySelector('#article h1').textContent === title,
      book.catalog.entries[1].t);
  });
});

test('single and multiple chapter progress spans 0–100% without early completion', async () => {
  for (const name of ['单章测试', '测试甲']) {
    await isolated(async context => {
      const book = fixtures.get(name), page = await context.newPage();
      if (name === '单章测试') assert.equal(book.catalog.entries.length, 1);
      await open(page, book);
      const percent = () => page.locator('#progressfill').evaluate(el => parseFloat(el.style.width));
      assert.equal(await percent(), 0);
      await chapter(page, book, book.catalog.entries.length - 1);
      assert.ok(await percent() < 100, 'Opening the final chapter does not finish the book');
      await scroll(page, book, 0.5);
      const middle = await percent();
      assert.ok(middle > 0 && middle < 100);
      await scroll(page, book, 1);
      assert.equal(await percent(), 100);
    });
  }
});

test('closed panels stay out of Tab order and TOC entries work with the keyboard', async () => {
  await isolated(async context => {
    const book = fixtures.get('测试甲'), page = await context.newPage();
    await open(page, book);
    await page.locator('#btnToc').focus();
    for (let i = 0; i < 16; i++) {
      await page.keyboard.press('Tab');
      assert.equal(await page.evaluate(() => Boolean(document.activeElement.closest('.panel'))), false,
        'Tab must not enter a closed offscreen panel');
    }
    await page.locator('#btnToc').focus();
    await page.keyboard.press('Enter');
    await page.waitForFunction(() => document.querySelector('#tocPanel').classList.contains('open'));
    const item = page.locator('.tocItem[data-idx="1"]');
    assert.equal(await item.evaluate(el => el.tagName), 'BUTTON');
    await item.focus();
    await page.keyboard.press('Enter');
    await page.waitForFunction(({key}) => JSON.parse(localStorage.getItem(key)).auto.i === 1, {key: book.key});
    assert.equal(await page.locator('#article h1').textContent(), book.catalog.entries[1].t);
    assert.equal(await page.locator('#tocPanel').getAttribute('aria-hidden'), 'true');
    await page.locator('#btnSettings').click();
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#setPanel').getAttribute('aria-hidden'), 'true');
  });
});

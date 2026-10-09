#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_reader.py — Turn a .txt novel into a lightweight offline HTML reader.

Usage:
    python build_reader.py <input.txt> [output_dir] [--encoding big5]

- Detects UTF-8/UTF-16 and common Chinese encodings; ambiguous input requires
  --encoding. Decoding is strict, never silently replacing damaged characters.
- Splits the book by its dominant chapter unit (章 / 回 / 节 / Chapter), groups by
  volume (卷 / 部 / 集), and keeps special sections (楔子 / 序 / 番外 / 外传 …).
- Writes one small file per chapter so the reader loads only one chapter at a time.
- Copies a single-page reader (开始阅读.html) with table of contents, auto-bookmark
  (resume on reopen), manual bookmarks, search, themes and font settings.

If no chapter markers are found, the text is split into ~equal parts as a fallback.
"""
import argparse
import codecs
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile

CJK_NUM = '〇零一二三四五六七八九十百千万亿兩两0-9０-９'
CHAP_UNITS = [
    ('章', re.compile(r'^第\s*[' + CJK_NUM + r']+\s*章')),
    ('回', re.compile(r'^第\s*[' + CJK_NUM + r']+\s*回')),
    ('节', re.compile(r'^第\s*[' + CJK_NUM + r']+\s*节')),
    ('EN', re.compile(r'^chapter\s+(?:[0-9]+|[IVXLC]+)(?=$|[\s:：.、\-—])', re.I)),
]
HEADER_BOUNDARY = r'(?=$|[\s:：·・.、\-—])'
VOL_RE = re.compile(r'^第\s*[' + CJK_NUM + r']+\s*[卷部集]' + HEADER_BOUNDARY)
SPECIAL_PREFIX = ('楔子', '序章', '序言', '序幕', '引子', '前言', '尾声', '终章',
                  '大结局', '后记', '後記', '作者的话', '番外', '外传', '外傳')
# 番外/外传 that follow a short book-name prefix, e.g. "凡人外传·仙界篇 一".
# Requires the marker within the first few chars AND followed by a separator,
# so narrative lines like "厅外传来了脚步声" are NOT matched.
FANWAI_RE = re.compile(r'^.{1,4}(?:番外|外传|外傳)(?:[·・.、\s0-9〇零一二三四五六七八九十]|$)')
SPECIAL_RE = re.compile(r'^(?:' + '|'.join(SPECIAL_PREFIX) + r')' + HEADER_BOUNDARY)
NUMBERED_SPECIAL_RE = re.compile(r'^(?:番外|外传|外傳)[' + CJK_NUM + r']+' + HEADER_BOUNDARY)
MANIFEST = '.novel-txt-reader.json'
CHAPTER_FILE_RE = re.compile(r'data/ch_[0-9]{4,}\.js\Z')


def _decode_strict(raw, encoding):
    text = raw.decode(encoding, errors='strict')
    if text.startswith('\ufeff'):
        text = text[1:]
    if any((ord(c) < 32 and c not in '\t\n\r\f') or 127 <= ord(c) < 160
           for c in text):
        raise ValueError('Input contains unexpected control characters; check its encoding.')
    return text


def _heading_score(text):
    return sum(1 for line in text.splitlines()
               if any(is_heading(line.strip(), pat) for _, pat in CHAP_UNITS)
               or is_heading(line.strip(), VOL_RE) or is_special(line.strip()))


def detect_decode(raw, encoding=None):
    """Return (text, encoding_label), requiring an override when undecidable.

    GB18030 and Big5 have overlapping byte ranges: successful decoding alone is
    not evidence of the correct encoding. Clear heading evidence can distinguish
    common novels; arbitrary short prose must be selected explicitly.
    """
    if encoding:
        label = codecs.lookup(encoding).name
        return _decode_strict(raw, label), label
    for bom, codec, label in (
        (codecs.BOM_UTF32_LE, 'utf-32', 'utf-32-le'),
        (codecs.BOM_UTF32_BE, 'utf-32', 'utf-32-be'),
        (codecs.BOM_UTF8, 'utf-8-sig', 'utf-8-sig'),
        (codecs.BOM_UTF16_LE, 'utf-16', 'utf-16-le'),
        (codecs.BOM_UTF16_BE, 'utf-16', 'utf-16-be'),
    ):
        if raw.startswith(bom):
            return _decode_strict(raw, codec), label

    # BOM-less UTF-16 is only inferred from consistent ASCII/newline NUL pairs.
    if b'\x00' in raw and len(raw) % 2 == 0:
        even, odd = raw[::2].count(0), raw[1::2].count(0)
        le_lines = sum(a in (10, 13) and b == 0 for a, b in zip(raw[::2], raw[1::2]))
        be_lines = sum(a == 0 and b in (10, 13) for a, b in zip(raw[::2], raw[1::2]))
        if (le_lines and not be_lines) or (odd >= 2 and odd > even * 4):
            return _decode_strict(raw, 'utf-16-le'), 'utf-16-le'
        if (be_lines and not le_lines) or (even >= 2 and even > odd * 4):
            return _decode_strict(raw, 'utf-16-be'), 'utf-16-be'
    try:
        return _decode_strict(raw, 'utf-8'), 'utf-8'
    except (UnicodeError, ValueError):
        pass
    candidates = []
    for codec in ('gb18030', 'big5hkscs'):
        try:
            candidates.append((_decode_strict(raw, codec), codec))
        except (UnicodeError, ValueError):
            pass
    if len(candidates) == 1 or (len(candidates) == 2 and candidates[0][0] == candidates[1][0]):
        return candidates[0]
    if candidates:
        scores = [_heading_score(text) for text, _ in candidates]
        winner = max(range(len(scores)), key=scores.__getitem__)
        if scores[winner] >= 2 and all(score == 0 for i, score in enumerate(scores) if i != winner):
            return candidates[winner]
        raise ValueError('Ambiguous text encoding (GB18030 or Big5). '
                         'Retry with --encoding gb18030 or --encoding big5.')
    raise ValueError('Cannot decode input without data loss. Check the source file '
                     'and specify its encoding with --encoding.')


def is_heading(s, pattern):
    # Compact numbered chapter titles remain supported, but ordinary sentences
    # are not headings. Question marks are valid in titles (e.g. 为什么？).
    return bool(s and len(s) <= 40 and not re.search(r'[。；;，,]', s)
                and pattern.match(s))


def is_special(s):
    return any(is_heading(s, pat) for pat in (SPECIAL_RE, NUMBERED_SPECIAL_RE, FANWAI_RE))


def is_junk(s):
    """Only blank lines are omitted; URLs and separators are legitimate text."""
    return not s


def derive_title_author(path, text):
    base = os.path.splitext(os.path.basename(path))[0]
    author = ''
    m = re.search(r'作者[：: 　]+([^\s，,。（(【\[/\\]{1,20})', base) \
        or re.search(r'作者[：: 　]+([^\s，,。（(【\[/\\]{1,20})', text[:3000])
    if m:
        author = m.group(1).strip()
    title = re.sub(r'作者[：: 　].*$', '', base)
    title = re.sub(r'[（(【\[].*?[）)】\]]', '', title)
    title = title.strip(' 《》「」[]【】()-_、—　\t')
    if not title:
        title = base
    return title, author


def pick_unit(lines):
    counts = {k: 0 for k, _ in CHAP_UNITS}
    for ln in lines:
        s = ln.strip()
        if not s or len(s) > 40:
            continue
        for k, pat in CHAP_UNITS:
            if is_heading(s, pat):
                counts[k] += 1
                break
    best = max(counts, key=counts.get)
    return best if counts[best] >= 2 else None


def split_chapters(lines, unit):
    unit_pat = dict(CHAP_UNITS).get(unit)

    def is_chapter(s):
        if len(s) > 40:
            return False
        if unit_pat and is_heading(s, unit_pat):
            return True
        return is_special(s)

    # Only consume a volume heading when a numbered chapter will actually use
    # it. A final volume line or a superseded heading stays in its original place.
    volumes, next_numbered = set(), False
    for index in range(len(lines) - 1, -1, -1):
        s = lines[index].strip()
        if unit_pat and is_heading(s, unit_pat):
            next_numbered = True
        elif is_heading(s, VOL_RE):
            if next_numbered:
                volumes.add(index)
            next_numbered = False

    chapters, cur, cur_vol, front, started = [], None, '', [], False
    for index, ln in enumerate(lines):
        s = ln.strip()
        if index in volumes:
            cur_vol = s
            continue
        if is_chapter(s):
            if cur:
                chapters.append(cur)
            vol = '番外' if is_special(s) else (cur_vol or '正文')
            cur = {'title': s, 'vol': vol, 'body': []}
            started = True
            continue
        if is_junk(s):
            continue
        if not started:
            if s:
                front.append(s)
        elif s:
            cur['body'].append(s)
    if cur:
        chapters.append(cur)
    return chapters, front


def split_by_size(lines, target=4000):
    chapters, buf, size, n = [], [], 0, 0
    for ln in lines:
        s = ln.strip()
        if is_junk(s) or not s:
            continue
        buf.append(s)
        size += len(s)
        if size >= target:
            n += 1
            chapters.append({'title': '第%d部分' % n, 'vol': '正文', 'body': buf})
            buf, size = [], 0
    if buf:
        n += 1
        chapters.append({'title': '第%d部分' % n, 'vol': '正文', 'body': buf})
    return chapters, []


def safe(s):
    return s.replace(' ', '\n').replace(' ', '\n')


def _assert_safe_path(path):
    """Reject symlinks and Windows junction/reparse points, including ancestors."""
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or (getattr(info, 'st_file_attributes', 0)
                                        & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024)):
            raise ValueError('Refusing to write through a symlink or reparse point: %s' % part)


def _managed_name(name):
    return isinstance(name, str) and (name in ('data/catalog.js', '开始阅读.html', '使用说明.txt')
                                     or bool(CHAPTER_FILE_RE.fullmatch(name)))


def _generated_json(path, prefix, suffix):
    _assert_safe_path(path)
    data = path.read_text(encoding='utf-8')
    if not data.startswith(prefix) or not data.endswith(suffix):
        raise ValueError('Unrecognized existing generated file: %s' % path)
    return json.loads(data[len(prefix):-len(suffix)])


def _owned_files(out):
    manifest = out / MANIFEST
    _assert_safe_path(manifest)
    if manifest.exists():
        metadata = json.loads(manifest.read_text(encoding='utf-8'))
        names = metadata.get('files') if isinstance(metadata, dict) else None
        if (not isinstance(metadata, dict) or metadata.get('generator') != 'novel-txt-reader' or metadata.get('version') != 1
                or not isinstance(names, list) or not all(_managed_name(name) for name in names)
                or len(names) != len(set(names))):
            raise ValueError('Invalid reader output manifest: %s' % manifest)
        return set(names) | {MANIFEST}

    # Migrate pre-manifest readers only by validating their catalog and referenced
    # chapter payloads. Merely starting with "ch_" never makes a file ours.
    catalog_path = out / 'data' / 'catalog.js'
    if not catalog_path.exists():
        return set()
    catalog = _generated_json(catalog_path, 'window.__CATALOG__=', ';')
    entries = catalog.get('entries') if isinstance(catalog, dict) else None
    if not isinstance(entries, list) or not entries:
        raise ValueError('Cannot safely identify the existing reader catalog.')
    owned = {'data/catalog.js'}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or type(entry.get('i')) is not int or entry['i'] != index:
            raise ValueError('Cannot safely identify the existing reader chapters.')
        name = 'data/ch_%04d.js' % index
        path = out / name
        _assert_safe_path(path)
        if path.exists():
            chapter = _generated_json(path, 'window.__CH__(', ');')
            if (not isinstance(chapter, dict) or chapter.get('i') != index
                    or chapter.get('t') != entry.get('t') or not isinstance(chapter.get('p'), list)):
                raise ValueError('Unrecognized existing chapter: %s' % path)
            owned.add(name)
    for name in ('开始阅读.html', '使用说明.txt'):
        path = out / name
        _assert_safe_path(path)
        if path.exists():
            data = path.read_text(encoding='utf-8-sig')
            recognized = ('window.__CATALOG__' in data and 'data/catalog.js' in data
                          if name.endswith('.html') else '离线阅读器使用说明' in data)
            if not recognized:
                raise ValueError('Refusing to overwrite unrelated file: %s' % path)
            owned.add(name)
    return owned


def _promote(stage, out, new_files):
    old_files = _owned_files(out)
    affected = old_files | new_files
    for name in sorted(affected):
        path = out / name
        _assert_safe_path(path)
        if path.exists() and (not path.is_file() or name not in old_files):
            raise ValueError('Refusing to overwrite unrelated file: %s' % path)
    data_dir = out / 'data'
    _assert_safe_path(data_dir)
    data_was_present = data_dir.exists()
    backup = stage / 'previous'
    moved, installed = [], []
    created_data = False
    try:
        data_dir.mkdir(exist_ok=True)
        created_data = not data_was_present
        for name in sorted(affected):
            path = out / name
            _assert_safe_path(path)
            if path.exists():
                destination = backup / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.replace(path, destination)
                moved.append(name)
        for name in sorted(new_files):
            _assert_safe_path(out / name)
            os.replace(stage / name, out / name)
            installed.append(name)
    except BaseException:
        # Keep the backup directory if even rollback fails (e.g. hardware loss).
        # The caller must not remove the only remaining copy of previous output.
        try:
            for name in reversed(installed):
                _assert_safe_path(out / name)
                (out / name).unlink()
            for name in reversed(moved):
                _assert_safe_path(out / name)
                os.replace(backup / name, out / name)
            if created_data:
                data_dir.rmdir()
        except BaseException as rollback_error:
            raise RuntimeError('Output rollback failed; previous files are preserved in %s'
                               % backup) from rollback_error
        raise


def build(input_path, out_dir, encoding=None):
    raw = Path(input_path).read_bytes()
    text, enc = detect_decode(raw, encoding)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = text.split('\n')
    title, author = derive_title_author(input_path, text)

    unit = pick_unit(lines)
    if unit:
        chapters, front = split_chapters(lines, unit)
    else:
        chapters, front = split_by_size(lines)
    if not chapters:
        raise SystemExit('No content found in %s' % input_path)

    entries = [{'i': 0, 't': '内容简介', 'v': '简介', 'p': front}] if front else []
    start = len(entries)
    for k, c in enumerate(chapters, start=start):
        entries.append({'i': k, 't': c['title'], 'v': c['vol'], 'p': c['body']})
    # re-index sequentially
    for idx, e in enumerate(entries):
        e['i'] = idx

    catalog = {'title': title, 'author': author,
               'bookId': hashlib.sha256(text.encode('utf-8')).hexdigest(),
               'entries': [{'i': e['i'], 't': e['t'], 'v': e['v'],
                            'n': sum(len(p) for p in e['p'])} for e in entries]}

    guide = (
        '%s — 离线阅读器使用说明\n'
        '==============================\n\n'
        '【开始阅读】双击「开始阅读.html」，用浏览器打开即可（推荐 Chrome / Edge）。\n'
        '本书共 %d 章（含特殊篇章），每次只加载当前一章，翻页轻快。\n\n'
        '【自动书签】随时自动保存进度；关闭后重新打开会自动跳回上次位置。\n'
        '【手动书签】点右下角 🔖，或「书签」面板里的按钮，标记当前位置；随时跳回。\n'
        '【目录/翻页】顶部「目录」可按卷浏览、搜索、跳转；← 上一章，→ 下一章，B 加书签。\n'
        '【设置】顶部「Aa」可调主题（日间/护眼/夜间）、字体、字号、行距、宽度。\n'
        '【备份进度】进度存在浏览器本地；「书签」面板底部可「导出/导入进度」。\n\n'
        '【重要】请保持「开始阅读.html」与「data」文件夹在一起、不要改名；\n'
        '移动时请整个文件夹一起移动。全部文件为 UTF-8 编码，无乱码。\n'
    ) % (title, len(entries))
    out = Path(os.path.abspath(out_dir))
    _assert_safe_path(out)
    _assert_safe_path(out / 'data')
    out.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.reader-build-', dir=out))
    keep_backup = False
    try:
        (stage / 'data').mkdir()
        files = {'data/catalog.js', '开始阅读.html', '使用说明.txt'}
        for e in entries:
            obj = {'i': e['i'], 't': e['t'], 'v': e['v'], 'p': [safe(p) for p in e['p']]}
            name = 'data/ch_%04d.js' % e['i']
            (stage / name).write_text('window.__CH__(' + json.dumps(obj, ensure_ascii=False) + ');',
                                      encoding='utf-8')
            files.add(name)
        (stage / 'data/catalog.js').write_text('window.__CATALOG__='
                                             + json.dumps(catalog, ensure_ascii=False) + ';',
                                             encoding='utf-8')
        here = Path(__file__).resolve().parent
        shutil.copyfile(here / 'reader_template.html', stage / '开始阅读.html')
        (stage / '使用说明.txt').write_text(guide, encoding='utf-8-sig')
        (stage / MANIFEST).write_text(json.dumps({'generator': 'novel-txt-reader', 'version': 1,
                                                'files': sorted(files)}, ensure_ascii=False),
                                     encoding='utf-8')
        try:
            _promote(stage, out, files | {MANIFEST})
        except RuntimeError:
            keep_backup = True
            raise
    finally:
        if not keep_backup:
            shutil.rmtree(stage)

    total = sum(sum(len(p) for p in e['p']) for e in entries)
    print('  book       : %s%s' % (title, ('  作者:' + author) if author else ''))
    print('  encoding   : %s' % enc)
    print('  unit       : %s' % (unit or 'size-fallback'))
    print('  entries    : %d (含简介/番外)' % len(entries))
    print('  characters : %d' % total)
    print('  output dir : %s' % out_dir)
    return len(entries)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('input_path', help='Input TXT file')
    parser.add_argument('output_dir', nargs='?', help='Output reader directory')
    parser.add_argument('--encoding', help='Explicit strict input codec, e.g. big5, gb18030, utf-16-le')
    args = parser.parse_args()
    input_path = args.input_path
    if not os.path.isfile(input_path):
        raise SystemExit('File not found: %s' % input_path)
    if args.output_dir:
        out_dir = args.output_dir
    else:
        base = os.path.splitext(os.path.basename(input_path))[0]
        title, _ = derive_title_author(input_path, '')
        out_dir = os.path.join(os.path.dirname(os.path.abspath(input_path)), title or base)
    print('Building reader...')
    try:
        build(input_path, out_dir, args.encoding)
    except (OSError, ValueError, LookupError) as error:
        parser.exit(1, 'Build failed: %s\n' % error)
    print('Done. Open %s/开始阅读.html in your browser.' % out_dir)


if __name__ == '__main__':
    main()

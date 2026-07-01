#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_reader.py — Turn a .txt novel into a lightweight offline HTML reader.

Usage:
    python build_reader.py <input.txt> [output_dir]

- Auto-detects encoding (UTF-8/UTF-16/GBK/GB18030/Big5) and outputs UTF-8 (no 乱码).
- Splits the book by its dominant chapter unit (章 / 回 / 节 / Chapter), groups by
  volume (卷 / 部 / 集), and keeps special sections (楔子 / 序 / 番外 / 外传 …).
- Writes one small file per chapter so the reader loads only one chapter at a time.
- Copies a single-page reader (开始阅读.html) with table of contents, auto-bookmark
  (resume on reopen), manual bookmarks, search, themes and font settings.

If no chapter markers are found, the text is split into ~equal parts as a fallback.
"""
import os, re, sys, json, shutil

CJK_NUM = '〇零一二三四五六七八九十百千万亿兩两0-9０-９'
CHAP_UNITS = [
    ('章', re.compile(r'^第\s*[' + CJK_NUM + r']+\s*章')),
    ('回', re.compile(r'^第\s*[' + CJK_NUM + r']+\s*回')),
    ('节', re.compile(r'^第\s*[' + CJK_NUM + r']+\s*节')),
    ('EN', re.compile(r'^(?:chapter|Chapter|CHAPTER)\s+[0-9IVXLCivxlc]+')),
]
VOL_RE = re.compile(r'^第\s*[' + CJK_NUM + r']+\s*[卷部集]')
SPECIAL_PREFIX = ('楔子', '序章', '序言', '序幕', '引子', '前言', '尾声', '终章',
                  '大结局', '后记', '後記', '作者的话', '番外', '外传', '外傳')
# 番外/外传 that follow a short book-name prefix, e.g. "凡人外传·仙界篇 一".
# Requires the marker within the first few chars AND followed by a separator,
# so narrative lines like "厅外传来了脚步声" are NOT matched.
FANWAI_RE = re.compile(r'^.{1,4}(?:番外|外传|外傳)(?:[·・.、\s0-9〇零一二三四五六七八九十]|$)')
AD_KEYWORDS = ('http://', 'https://', 'www.', '.com', '.net', '.cn', '.org')
SEP_CHARS = set('=＝-—–_～~*·. 　\t')


def detect_decode(raw):
    """Return (text, encoding_label)."""
    if raw[:3] == b'\xef\xbb\xbf':
        return raw[3:].decode('utf-8', 'replace'), 'utf-8-sig'
    if raw[:2] == b'\xff\xfe':
        return raw.decode('utf-16', 'replace'), 'utf-16-le'
    if raw[:2] == b'\xfe\xff':
        return raw.decode('utf-16', 'replace'), 'utf-16-be'
    guess = None
    try:
        import chardet
        g = chardet.detect(raw[:400000])
        if g and g.get('encoding') and (g.get('confidence') or 0) >= 0.7:
            guess = g['encoding']
    except Exception:
        pass
    order = []
    if guess:
        gl = guess.lower()
        if gl in ('gb2312', 'gbk', 'gb18030'):
            order.append('gb18030')
        elif gl in ('big5', 'big5-hkscs'):
            order.append('big5hkscs')
        else:
            order.append(guess)
    order += ['utf-8', 'gb18030', 'big5hkscs', 'utf-16']
    seen = set()
    for enc in order:
        if not enc or enc in seen:
            continue
        seen.add(enc)
        try:
            return raw.decode(enc), enc
        except Exception:
            continue
    return raw.decode('gb18030', 'replace'), 'gb18030(replace)'


def is_special(s):
    if len(s) > 16:
        return False
    if any(s.startswith(t) for t in SPECIAL_PREFIX):
        return True
    return bool(FANWAI_RE.match(s))


def is_junk(s):
    if not s:
        return True
    if set(s) <= SEP_CHARS:
        return True
    if len(s) < 60 and any(k in s for k in AD_KEYWORDS):
        return True
    return False


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
            if pat.match(s):
                counts[k] += 1
                break
    best = max(counts, key=counts.get)
    return best if counts[best] >= 2 else None


def split_chapters(lines, unit):
    unit_pat = dict(CHAP_UNITS).get(unit)

    def is_chapter(s):
        if len(s) > 40:
            return False
        if unit_pat and unit_pat.match(s):
            return True
        return is_special(s)

    chapters, cur, cur_vol, front, started = [], None, '', [], False
    for ln in lines:
        s = ln.strip()
        if VOL_RE.match(s) and len(s) <= 40:
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


def build(input_path, out_dir):
    raw = open(input_path, 'rb').read()
    text, enc = detect_decode(raw)
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

    data_dir = os.path.join(out_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    for f in os.listdir(data_dir):
        if f.startswith('ch_') or f == 'catalog.js':
            os.remove(os.path.join(data_dir, f))

    for e in entries:
        obj = {'i': e['i'], 't': e['t'], 'v': e['v'], 'p': [safe(p) for p in e['p']]}
        with open(os.path.join(data_dir, 'ch_%04d.js' % e['i']), 'w', encoding='utf-8') as f:
            f.write('window.__CH__(' + json.dumps(obj, ensure_ascii=False) + ');')

    catalog = {'title': title, 'author': author,
               'entries': [{'i': e['i'], 't': e['t'], 'v': e['v'],
                            'n': sum(len(p) for p in e['p'])} for e in entries]}
    with open(os.path.join(data_dir, 'catalog.js'), 'w', encoding='utf-8') as f:
        f.write('window.__CATALOG__=' + json.dumps(catalog, ensure_ascii=False) + ';')

    here = os.path.dirname(os.path.abspath(__file__))
    shutil.copyfile(os.path.join(here, 'reader_template.html'),
                    os.path.join(out_dir, '开始阅读.html'))

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
    with open(os.path.join(out_dir, '使用说明.txt'), 'w', encoding='utf-8-sig') as f:
        f.write(guide)

    total = sum(sum(len(p) for p in e['p']) for e in entries)
    print('  book       : %s%s' % (title, ('  作者:' + author) if author else ''))
    print('  encoding   : %s' % enc)
    print('  unit       : %s' % (unit or 'size-fallback'))
    print('  entries    : %d (含简介/番外)' % len(entries))
    print('  characters : %d' % total)
    print('  output dir : %s' % out_dir)
    return len(entries)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    input_path = sys.argv[1]
    if not os.path.isfile(input_path):
        raise SystemExit('File not found: %s' % input_path)
    if len(sys.argv) >= 3:
        out_dir = sys.argv[2]
    else:
        base = os.path.splitext(os.path.basename(input_path))[0]
        title, _ = derive_title_author(input_path, '')
        out_dir = os.path.join(os.path.dirname(os.path.abspath(input_path)), title or base)
    os.makedirs(out_dir, exist_ok=True)
    print('Building reader...')
    build(input_path, out_dir)
    print('Done. Open %s/开始阅读.html in your browser.' % out_dir)


if __name__ == '__main__':
    main()

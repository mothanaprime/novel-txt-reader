#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate synthetic novels in several encodings / chapter styles for testing."""
import os, sys
out = sys.argv[1] if len(sys.argv) > 1 else '/tmp/nreader_samples'
os.makedirs(out, exist_ok=True)

a = "书名：测试演义 作者：某某\n\n第一卷 开篇\n\n第一回 楔子之前\n" + "　　话说天下大势，分久必合。\n" * 20
a += "\n第二回 群雄并起\n" + "　　却说那英雄豪杰。\n" * 20
a += "\n第二卷 中盘\n\n第三回 风云再起\n" + "　　又过了三年。\n" * 20
open(os.path.join(out, 'gbk_hui.txt'), 'wb').write(a.encode('gbk'))

b = "内容简介：这是一个测试。\n\n第一章 起点\n" + "　　主角登场了。\n" * 15
b += "\n第二章 成长\n" + "　　主角变强了。\n" * 15 + "\n番外 后日谈\n" + "　　多年以后。\n" * 10
open(os.path.join(out, 'utf8bom_zhang.txt'), 'wb').write(b'\xef\xbb\xbf' + b.encode('utf-8'))

c = "Chapter 1 The Beginning\n" + "It was a dark night.\n" * 15 + "\nChapter 2 The Middle\n" + "Then came the dawn.\n" * 15
open(os.path.join(out, 'utf16_en.txt'), 'wb').write(c.encode('utf-16'))

d = "".join("这是没有章节标记的长文本段落。" * 3 + "\n" for _ in range(400))
open(os.path.join(out, 'nomarker.txt'), 'wb').write(d.encode('utf-8'))

e = "第一章 開始\n" + "　　這是繁體中文測試。\n" * 15 + "\n第二章 繼續\n" + "　　主角繼續前進。\n" * 15
open(os.path.join(out, 'big5.txt'), 'wb').write(e.encode('big5'))

# tricky: line containing 外传 mid-sentence must NOT become a 番外 chapter
f = "第一章 相遇\n" + "　　片刻后，厅外传来了脚步之声。\n" * 5 + "　　意外传闻不断。\n" * 5
f += "\n第二章 别离\n" + "　　号外传遍全城。\n" * 5
open(os.path.join(out, 'tricky.txt'), 'wb').write(f.encode('utf-8'))

print("samples ->", out)
for n in sorted(os.listdir(out)):
    print("  ", n)

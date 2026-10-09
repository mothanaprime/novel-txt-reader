"""Deterministic, dependency-free regression tests; all novels are synthetic."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'build_reader.py'
SPEC = importlib.util.spec_from_file_location('build_reader', SCRIPT)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)

TRADITIONAL = ('第一章 開始\n這是繁體中文測試。\n'
               '第二章 繼續\n主角繼續前進。\n')
SIMPLIFIED = ('第一章 开始\n这是简体中文测试。\n'
              '第二章 继续\n主角继续前进。\n')


class EncodingTests(unittest.TestCase):
    def test_big5_fixture_decodes_to_exact_unicode_without_chardet(self):
        raw = TRADITIONAL.encode('big5')
        # This previously decoded successfully as GB18030, but to wrong text.
        self.assertNotEqual(raw.decode('gb18030'), TRADITIONAL)
        with patch.dict(sys.modules, {'chardet': None}):
            text, encoding = builder.detect_decode(raw)
        self.assertEqual(text, TRADITIONAL)
        self.assertEqual(encoding, 'big5hkscs')

    def test_supported_encodings_preserve_exact_text(self):
        for encoding in ('utf-8', 'utf-8-sig', 'utf-16', 'utf-16-le', 'utf-16-be', 'gbk'):
            with self.subTest(encoding=encoding):
                self.assertEqual(builder.detect_decode(SIMPLIFIED.encode(encoding))[0], SIMPLIFIED)

    def test_gb18030_four_byte_character(self):
        text = SIMPLIFIED + '罕见文字：𠀀。\n'
        self.assertEqual(len('𠀀'.encode('gb18030')), 4)
        self.assertEqual(builder.detect_decode(text.encode('gb18030'))[0], text)

    def test_ambiguous_legacy_text_requires_explicit_encoding(self):
        raw = '中文'.encode('gbk')
        self.assertNotEqual(raw.decode('gb18030'), raw.decode('big5hkscs'))
        with self.assertRaisesRegex(ValueError, 'Ambiguous.*--encoding'):
            builder.detect_decode(raw)
        self.assertEqual(builder.detect_decode(raw, 'gbk')[0], '中文')
        self.assertEqual(builder.detect_decode(raw, 'big5')[0], raw.decode('big5'))

    def test_damaged_bom_and_explicit_codec_fail_without_replacement(self):
        for raw, encoding in ((b'\xef\xbb\xbf\xff', None), (b'\xff\xfeA', None),
                              (b'\xff', None), (b'\xc3', 'utf-8')):
            with self.subTest(raw=raw, encoding=encoding):
                with self.assertRaises((UnicodeError, ValueError)):
                    builder.detect_decode(raw, encoding)

    def test_explicit_utf8_and_utf16_endian_strip_bom(self):
        self.assertEqual(builder.detect_decode(SIMPLIFIED.encode('utf-8-sig'), 'utf-8')[0], SIMPLIFIED)
        self.assertEqual(builder.detect_decode(b'\xff\xfe' + SIMPLIFIED.encode('utf-16-le'),
                                              'utf-16-le')[0], SIMPLIFIED)


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='reader-regression-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / '合成小说.txt'
        self.out = self.root / 'reader'

    def build(self, text=SIMPLIFIED, encoding='utf-8', override=None, source=None, out=None):
        source = source or self.source
        out = out or self.out
        source.write_bytes(text.encode(encoding))
        with contextlib.redirect_stdout(io.StringIO()):
            builder.build(source, out, encoding=override)
        catalog = builder._generated_json(out / 'data/catalog.js', 'window.__CATALOG__=', ';')
        chapters = [builder._generated_json(out / ('data/ch_%04d.js' % e['i']),
                                             'window.__CH__(', ');') for e in catalog['entries']]
        return catalog, chapters

    def snapshot(self):
        return {str(path.relative_to(self.out)): path.read_bytes()
                for path in self.out.rglob('*') if path.is_file()}

    def test_big5_chapter_titles_and_bodies_are_correct(self):
        catalog, chapters = self.build(TRADITIONAL, 'big5')
        self.assertEqual([e['t'] for e in catalog['entries']], ['第一章 開始', '第二章 繼續'])
        self.assertEqual([c['p'] for c in chapters], [['這是繁體中文測試。'], ['主角繼續前進。']])

    def test_normal_prose_urls_and_separators_are_preserved(self):
        first = ['他打开了 https://example.com 查看档案。', '第一部分计划已完成。',
                 '前言不搭后语，他觉得奇怪。', '第一章的故事还在继续。', '====', '---', '* * *']
        second = ['服务器地址是 www.example.org，请抄下来。', '第三集的故事到这里就结束了。',
                  '尾声还在回荡。', '片刻后，厅外传来了脚步之声。', '意外传闻不断。', '号外传遍全城。']
        text = '第一章 开始\n' + '\n'.join(first) + '\n第二章 继续\n' + '\n'.join(second)
        catalog, chapters = self.build(text)
        self.assertEqual(len(catalog['entries']), 2)
        self.assertEqual(chapters[0]['p'], first)
        self.assertEqual(chapters[1]['p'], second)

    def test_size_fallback_preserves_all_nonempty_lines(self):
        lines = ['https://example.com', '第一部分计划已完成。', '=====', '---', '正文。']
        _, chapters = self.build('\n\n'.join(lines))
        self.assertEqual([p for c in chapters for p in c['p']], lines)

    def test_volumes_compact_chapters_and_specials(self):
        text = ('内容简介\n第一卷 启程\n楔子\n初见。\n第一章山边小村\n甲。\n'
                '第二卷 远行\n第二章 为什么？\n乙。\n番外一\n多年以后。\n'
                '星海外传·仙界篇 一\n终。\n')
        catalog, chapters = self.build(text)
        self.assertEqual([e['t'] for e in catalog['entries']],
                         ['内容简介', '楔子', '第一章山边小村', '第二章 为什么？', '番外一', '星海外传·仙界篇 一'])
        self.assertEqual(chapters[0]['p'], ['内容简介'])
        self.assertEqual(chapters[2]['v'], '第一卷 启程')
        self.assertEqual(chapters[3]['v'], '第二卷 远行')
        self.assertEqual(chapters[-1]['p'], ['终。'])

    def test_conventional_volume_grouping(self):
        _, chapters = self.build('第一卷 开篇\n第一回 初见\n甲。\n第二回 再会\n乙。\n'
                                 '第二卷 终篇\n第三回 归来\n丙。\n')
        self.assertEqual([c['v'] for c in chapters], ['第一卷 开篇', '第一卷 开篇', '第二卷 终篇'])

    def test_terminal_and_superseded_volumes_preserve_original_order(self):
        _, chapters = self.build('第一章 开始\n甲。\n第一卷 旧名\n第二卷 新名\n'
                                 '第二章 继续\n乙。\n第三卷 待续\n尚有后话。\n')
        self.assertEqual(chapters[0]['p'], ['甲。', '第一卷 旧名'])
        self.assertEqual(chapters[1]['v'], '第二卷 新名')
        self.assertEqual(chapters[1]['p'], ['乙。', '第三卷 待续', '尚有后话。'])

    def test_english_heading_number_requires_boundary(self):
        _, chapters = self.build('Chapter 1 Start\nChapter 1st is a prose fragment.\n'
                                 'Chapter II Return\nChapter IIIology is not a title.\n')
        self.assertEqual([c['t'] for c in chapters], ['Chapter 1 Start', 'Chapter II Return'])
        self.assertEqual(chapters[0]['p'], ['Chapter 1st is a prose fragment.'])
        self.assertEqual(chapters[1]['p'], ['Chapter IIIology is not a title.'])

    def test_book_id_is_source_based_and_stable_across_path_encoding_and_newlines(self):
        expected = hashlib.sha256(SIMPLIFIED.encode('utf-8')).hexdigest()
        for index, encoding in enumerate(('utf-8', 'utf-8-sig', 'utf-16', 'gb18030')):
            with self.subTest(encoding=encoding):
                text = SIMPLIFIED.replace('\n', '\r\n' if index % 2 else '\r')
                catalog, _ = self.build(text, encoding, source=self.root / ('moved-%d.txt' % index))
                self.assertRegex(catalog['bookId'], r'\A[0-9a-f]{64}\Z')
                self.assertEqual(catalog['bookId'], expected)
        changed, _ = self.build(SIMPLIFIED + '不同文字。')
        self.assertNotEqual(changed['bookId'], expected)

    def test_rebuild_preserves_unrelated_files_and_removes_only_stale_owned_chapters(self):
        self.build(SIMPLIFIED + '第三章 结尾\n丙。\n')
        extras = {'data/ch_notes.txt': b'notes', 'data/ch_9999.js': b'unrelated javascript',
                  'notes.txt': b'personal notes'}
        for name, contents in extras.items():
            (self.out / name).write_bytes(contents)
        self.build()
        self.assertFalse((self.out / 'data/ch_0002.js').exists())
        for name, contents in extras.items():
            self.assertEqual((self.out / name).read_bytes(), contents)

    def test_legacy_rebuild_adopts_only_validated_catalog_chapters(self):
        self.build(SIMPLIFIED + '第三章 结尾\n丙。\n')
        (self.out / builder.MANIFEST).unlink()
        (self.out / 'data/ch_notes.txt').write_text('notes', encoding='utf-8')
        self.build()
        self.assertTrue((self.out / builder.MANIFEST).is_file())
        self.assertFalse((self.out / 'data/ch_0002.js').exists())
        self.assertEqual((self.out / 'data/ch_notes.txt').read_text(encoding='utf-8'), 'notes')

    def test_staging_failure_keeps_previous_output_byte_identical(self):
        self.build()
        before = self.snapshot()
        real_write = Path.write_text

        def fail_chapter(path, *args, **kwargs):
            if path.name == 'ch_0000.js':
                raise OSError('Injected staging failure')
            return real_write(path, *args, **kwargs)

        with patch.object(Path, 'write_text', fail_chapter):
            with self.assertRaisesRegex(OSError, 'Injected staging'):
                self.build(SIMPLIFIED + '第三章 新内容\n丙。\n')
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(list(self.out.glob('.reader-build-*')))

    def test_partial_promotion_failure_rolls_back_all_previous_bytes(self):
        self.build()
        before = self.snapshot()
        real_replace = os.replace
        failed = False

        def fail_once(source, target):
            nonlocal failed
            source = Path(source)
            if (not failed and source.name == 'ch_0001.js' and 'previous' not in source.parts
                    and any(part.startswith('.reader-build-') for part in source.parts)):
                failed = True
                raise OSError('Injected promotion failure')
            return real_replace(source, target)

        with patch.object(builder.os, 'replace', fail_once):
            with self.assertRaisesRegex(OSError, 'Injected promotion'):
                self.build(SIMPLIFIED + '第三章 新内容\n丙。\n')
        self.assertTrue(failed)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(list(self.out.glob('.reader-build-*')))

    def test_unrelated_generated_filename_collision_is_not_overwritten(self):
        self.out.mkdir()
        (self.out / '开始阅读.html').write_bytes(b'User-owned HTML')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'unrelated file'):
            self.build()
        self.assertEqual(self.snapshot(), before)

    def test_malformed_or_traversing_manifest_leaves_output_untouched(self):
        self.build()
        for invalid in (None, [], {'generator': 'novel-txt-reader', 'version': 1,
                                   'files': ['../outside.txt']}):
            with self.subTest(invalid=invalid):
                (self.out / builder.MANIFEST).write_text(json.dumps(invalid), encoding='utf-8')
                before = self.snapshot()
                with self.assertRaisesRegex(ValueError, 'Invalid reader output manifest'):
                    self.build()
                self.assertEqual(self.snapshot(), before)

    def test_damaged_input_leaves_previous_output_untouched(self):
        self.build()
        before = self.snapshot()
        self.source.write_bytes(b'\xef\xbb\xbf\xff')
        with self.assertRaises(UnicodeError):
            builder.build(self.source, self.out)
        self.assertEqual(self.snapshot(), before)

    def test_symlink_output_directory_is_rejected(self):
        elsewhere = self.root / 'elsewhere'
        elsewhere.mkdir()
        try:
            self.out.symlink_to(elsewhere, target_is_directory=True)
        except OSError as error:
            self.skipTest('Symlink creation unavailable: %s' % error)
        with self.assertRaisesRegex(ValueError, 'symlink or reparse point'):
            self.build()
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_symlink_data_directory_is_rejected(self):
        self.out.mkdir()
        elsewhere = self.root / 'elsewhere'
        elsewhere.mkdir()
        try:
            (self.out / 'data').symlink_to(elsewhere, target_is_directory=True)
        except OSError as error:
            self.skipTest('Symlink creation unavailable: %s' % error)
        with self.assertRaisesRegex(ValueError, 'symlink or reparse point'):
            self.build()
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_cli_encoding_override_and_diagnostic_exit(self):
        self.source.write_bytes('中文'.encode('gbk'))
        result = subprocess.run([sys.executable, '-S', str(SCRIPT), str(self.source), str(self.out)],
                                capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'--encoding', result.stderr)
        result = subprocess.run([sys.executable, '-S', str(SCRIPT), str(self.source), str(self.out),
                                 '--encoding', 'gbk'], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        chapter = builder._generated_json(self.out / 'data/ch_0000.js', 'window.__CH__(', ');')
        self.assertEqual(chapter['p'], ['中文'])


if __name__ == '__main__':
    unittest.main()

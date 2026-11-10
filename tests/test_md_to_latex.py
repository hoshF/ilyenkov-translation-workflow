"""转换完整性与 CLI 输出边界的回归测试。"""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/md_to_latex.py'
spec = importlib.util.spec_from_file_location('md_to_latex', SCRIPT)
converter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(converter)


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'chapter.md'

    def convert(self, text, **options):
        self.path.write_text(text, encoding='utf-8')
        return converter.convert(self.path, **options)

    def cli(self, *options):
        return subprocess.run([sys.executable, '-B', str(SCRIPT), str(self.path), *map(str, options)],
                              capture_output=True, text=True)

    def test_normal_notes_and_translator_note_in_same_block(self):
        latex, report, errors = self.convert(
            '正文[^fn-a]，译注[^zh-1]。\n\n[^fn-a]: 原注。\n[^zh-1]: 译注。')
        self.assertEqual(latex, '正文\\footnote{原注。}，译注\\footnote{译注。}。\n')
        self.assertEqual((report, errors), ([], []))

    def test_duplicate_definitions_across_and_within_blocks(self):
        for separator in ('\n', '\n\n'):
            with self.subTest(separator=separator):
                latex, _, errors = self.convert(
                    '正文[^a]。\n\n[^a]: 第一条。' + separator + '[^a]: 第二条。')
                self.assertTrue(any('[阻断错误]' in e and '重复定义' in e for e in errors))
                self.assertIn(str(self.path) + ':', errors[0])
                self.assertIn('[^a]', errors[0])
                self.assertIn('首次定义', errors[0])
                self.assertIn('% [^a]: 第一条。', latex)
                self.assertIn('% [^a]: 第二条。', latex)
                self.assertLess(latex.index('% [^a]: 第一条。'), latex.index('% [^a]: 第二条。'))
                self.assertNotIn('\\footnote{', latex)
                self.assertIn('正文[^a]', latex)

    def test_unused_definition_pending_and_retained_in_source_order(self):
        latex, _, errors = self.convert('甲。\n\n[^a]: 待核注文。\n\n乙。')
        self.assertTrue(any('[待人工确认]' in e and '未使用定义' in e for e in errors))
        self.assertIn('[^a]', errors[0])
        self.assertIn(str(self.path) + ':3', errors[0])
        self.assertLess(latex.index('甲'), latex.index('% [^a]'))
        self.assertLess(latex.index('% [^a]'), latex.index('乙'))

    def test_repeated_reference_not_duplicated(self):
        latex, _, errors = self.convert('甲[^a]。\n\n乙[^a]。\n\n[^a]: 同一注文。')
        self.assertTrue(any('[待人工确认]' in e and '重复引用' in e for e in errors))
        self.assertEqual(latex.count('\\footnote{'), 1)
        self.assertIn('乙[^a]', latex)

    def test_missing_reference_has_block_and_line(self):
        _, _, errors = self.convert('<!-- block-id: b000001 -->\n正文[^missing]。')
        self.assertIn(str(self.path) + ':2 (b000001)', errors[0])
        self.assertIn('[^missing]', errors[0])

    def test_reference_at_start_is_not_discarded_as_definition(self):
        latex, _, errors = self.convert('[^a]正文。\n\n[^a]: 注文。')
        self.assertFalse(errors)
        self.assertEqual(latex, '\\footnote{注文。}正文。\n')

    def test_title_note_remains_manual(self):
        latex, report, errors = self.convert('### 题名[^title]\n\n正文。')
        self.assertIn(r'[\textasciicircum{}title]', latex)
        self.assertTrue(any('[^title]' in r and str(self.path) in r for r in report))
        self.assertFalse(errors)
        self.assertTrue(any('[警告]' in r for r in report))
        latex, _, errors = self.convert('### 题名[^title]\n\n正文。\n\n[^title]: 标题注文。')
        self.assertTrue(any('仅在标题引用' in e for e in errors))
        self.assertIn('% [^title]: 标题注文。', latex)
        self.assertNotIn('\\footnote{', latex)

    def test_numeric_note_continuation_and_title(self):
        latex, report, errors = self.convert(
            '### 题名 1\n\n正文 2。\n\n1 首注。\n\n续段。\n\n2 次注。', numeric_notes=True)
        self.assertFalse(errors)
        self.assertIn('\\section*{题名\\footnote{首注。\\par 续段。}}', latex)
        self.assertEqual(latex.count('\\footnote{'), 2)
        self.assertTrue(any('续段' in r for r in report))

    def test_numeric_and_explicit_definition_collision(self):
        _, _, errors = self.convert('正文 1。\n\n[^num-1]: 显式定义。\n\n1 数字定义。', numeric_notes=True)
        self.assertTrue(any('重复定义' in e and '[^num-1]' in e for e in errors))

    def test_numeric_gap_and_missing_reference_block(self):
        for text in ('正文 1。\n\n1 甲。\n\n3 丙。', '正文。\n\n1 注文。'):
            with self.subTest(text=text):
                _, _, errors = self.convert(text, numeric_notes=True)
                self.assertTrue(errors)

    def test_literal_and_confirmed_underscore_runs(self):
        for count in (1, 2, 4, 5, 12, 33):
            rule = '_' * count
            for text in (rule, '句内' + rule + '文字。'):
                with self.subTest(text=text):
                    latex, _, errors = self.convert(text)
                    self.assertFalse(errors)
                    self.assertEqual(latex, text.replace('_', '\\_') + '\n')
                    latex, _, errors = self.convert(text, inline_rules=(rule,))
                    self.assertFalse(errors)
                    self.assertIn('\\bookinlinerule ', latex)

    def test_confirmation_matches_whole_run_only_and_keeps_escapes_links(self):
        text = '____ _____ ______ \\_ [网址](https://example.org/_____)'
        latex, _, _ = self.convert(text, inline_rules=('_____',))
        self.assertEqual(latex.count('\\bookinlinerule'), 1)
        self.assertIn('\\_' * 4, latex)
        self.assertIn('\\_' * 6, latex)
        self.assertIn('https://example.org/' + r'\_' * 5, latex)

    def test_escaped_underscore_cannot_expose_shorter_confirmed_run(self):
        for text in (r'\_____', r'_____\_', r'__\___'):
            with self.subTest(text=text):
                literal = converter.convert_styles(text)
                for rule in ('_', '__', '____', '_____'):
                    self.assertEqual(converter.convert_styles(text, inline_rules=(rule,)), literal)
        self.assertIn(r'\bookinlinerule',
                      converter.convert_styles(r'\\_____', inline_rules=('_____',)))

    def test_duplicate_confirmations_are_idempotent(self):
        text = '____ _____ ______'
        self.assertEqual(converter.convert_styles(text, inline_rules=('____', '_____')),
                         converter.convert_styles(text, inline_rules=('____', '_____', '____')))

    def test_same_length_mixed_meanings_require_work_level_positioning(self):
        text = '原文字段_____；图形横线_____。'
        self.assertEqual(converter.convert_styles(text), text.replace('_', r'\_'))
        # 此选项确认的是单元内全部同长位置；混用时维持默认，交作品 TeX 定位。
        self.assertEqual(converter.convert_styles(text, inline_rules=('_____',)).count(r'\bookinlinerule'), 2)

    def test_confirmation_reaches_notes_titles_and_tables(self):
        latex, _, errors = self.convert(
            '### 题名___\n\n| 列 |\n| --- |\n| 甲___[^a] |\n\n[^a]: 注___。', inline_rules=('___',))
        self.assertFalse(errors)
        self.assertEqual(latex.count('\\bookinlinerule'), 3)

    def test_incomplete_numeric_draft_retains_original_notes(self):
        latex, _, errors = self.convert('正文。\n\n1 注文。\n\n续段。', numeric_notes=True)
        self.assertTrue(errors)
        self.assertIn('% 1 注文。', latex)
        self.assertIn('% 续段。', latex)

    def test_html_styles_and_footnote_semantics(self):
        latex, _, errors = self.convert(
            '<em>正文强调</em>与<strong>粗体</strong>[^a]。\n\n'
            '[^a]: *真强调*，署名*埃·伊*。<br>续行。')
        self.assertFalse(errors)
        self.assertIn(r'\bookemph{正文强调}', latex)
        self.assertIn(r'\bookstrong{粗体}', latex)
        self.assertIn(r'\footnote{\bookemph{真强调}，署名\bookapparatus{埃·伊}。\newline 续行。}', latex)

    def test_autolinks_and_bare_links(self):
        latex, _, errors = self.convert(
            '<https://example.org/a_b> 与 https://example.org/path. 和 www.example.org/page')
        self.assertFalse(errors)
        self.assertIn(r'\url{https://example.org/a_b}', latex)
        self.assertIn(r'\url{https://example.org/path}.', latex)
        self.assertIn(r'\url{www.example.org/page}', latex)
        self.assertEqual(latex.count(r'\url{'), 3)

    def test_table_cells_line_breaks_notes_and_invalid_width(self):
        latex, _, errors = self.convert(
            '| 列一 | 列二 |\n| --- | --- |\n| 内容<br>续行 | 注[^a] |\n\n[^a]: 注文。')
        self.assertFalse(errors)
        self.assertIn(r'\begin{booktable}{2}', latex)
        self.assertIn(r'\bookstrong{列一} & \bookstrong{列二}', latex)
        self.assertIn(r'内容\newline 续行 & 注\footnote{注文。}', latex)
        self.assertIn(r'\end{booktable}', latex)
        _, _, errors = self.convert('| 列一 | 列二 |\n| --- | --- |\n| 少一列 |')
        self.assertTrue(any('表格列数不一致' in error for error in errors))

    def test_cli_preserves_existing_output_for_errors_and_pending(self):
        output = Path(self.temp.name) / 'chapter.tex'
        for text in ('正文[^a]。', '正文。\n\n[^a]: 注文。',
                     '甲[^a]乙[^a]。\n\n[^a]: 注文。',
                     '正文[^a]。\n\n[^a]: 一。\n\n[^a]: 二。'):
            with self.subTest(text=text):
                self.path.write_text(text)
                output.write_text('已确认的手工排版')
                result = self.cli('-o', output)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(output.read_text(), '已确认的手工排版')
                result = self.cli()
                self.assertEqual(result.stdout, '')
                self.assertNotEqual(result.returncode, 0)

    def test_draft_new_file_only_and_nonzero(self):
        self.path.write_text('正文。\n\n[^a]: 注文。')
        draft = Path(self.temp.name) / 'chapter.draft.tex'
        result = self.cli('--draft-output', draft)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('% [^a]: 注文。', draft.read_text())
        result = self.cli('--draft-output', draft)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('拒绝覆盖', result.stderr)
        self.assertNotEqual(self.cli('--draft-output', draft.with_suffix('.txt')).returncode, 0)

    def test_complete_draft_still_nonzero_and_cli_outputs_exclusive(self):
        self.path.write_text('正文[^a]。\n\n[^a]: 注文。')
        draft = Path(self.temp.name) / 'complete.draft.tex'
        result = self.cli('--draft-output', draft)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('\\footnote{注文。}', draft.read_text())
        self.assertNotEqual(self.cli('-o', Path(self.temp.name) / 'out.tex',
                                     '--draft-output', draft).returncode, 0)

    def test_draft_protected_directories_including_alias(self):
        self.path.write_text('正文。')
        alias = Path(self.temp.name) / 'alias'
        alias.symlink_to(ROOT / 'book/templates', target_is_directory=True)
        draft = alias / 'p1-test.draft.tex'
        self.assertNotEqual(self.cli('--draft-output', draft).returncode, 0)
        self.assertFalse(draft.exists())

    def test_cli_normal_and_explicit_confirmation(self):
        self.path.write_text('正文___。')
        output = Path(self.temp.name) / 'chapter.tex'
        result = self.cli('-o', output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output.read_text(), '正文\\_\\_\\_。\n')
        result = self.cli('--inline-rule', '___', '-o', output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('\\bookinlinerule', output.read_text())
        self.assertNotEqual(self.cli('--inline-rule', 'not-a-rule').returncode, 0)


if __name__ == '__main__':
    unittest.main()

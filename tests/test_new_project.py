"""项目初始化：建立的结构、规范入口与不覆盖行为。"""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/new_project.py'
ARTICLE = ROOT / 'examples/article/sravnenie-i-razlichie.md'
LINK = re.compile(r'\]\(([^)\s]+)\)')


def snapshot(directory):
    return {p.relative_to(directory): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.rglob('*')) if p.is_file()}


def broken_links(directory):
    bad = []
    for md in directory.rglob('*.md'):
        text = re.sub(r'```.*?```', '', md.read_text(encoding='utf-8'), flags=re.S)
        text = re.sub(r'`[^`\n]*`', '', text)
        for target in LINK.findall(text):
            path = target.partition('#')[0]
            if path and not target.startswith(('http://', 'https://')) and not (md.parent / path).exists():
                bad.append(f'{md.relative_to(directory)} -> {target}')
    return bad


class NewProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def run_tool(self, *args, cwd=None):
        return subprocess.run([sys.executable, '-B', str(SCRIPT), *map(str, args)],
                              capture_output=True, text=True, cwd=cwd)

    def article(self, project, *extra):
        return self.run_tool('article', project, '--work-id', 'sravnenie-i-razlichie',
                             '--title', 'Сравнение и различие', '--title-zh', '比较与区别',
                             '--source', ARTICLE, *extra)

    def outside_workflow(self, project):
        return {p for p in snapshot(project) if p.parts[0] != 'workflow'}

    def test_article_project_structure(self):
        project = self.base / 'proj'
        result = self.article(project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.outside_workflow(project), {
            Path('AGENTS.md'), Path('CLAUDE.md'), Path('.gitignore'),
            Path('glossary/glossary.json'), Path('glossary/terms.json'),
            Path('source/sravnenie-i-razlichie.md'),
            Path('translation/sravnenie-i-razlichie/work.json'),
        })
        work = json.loads((project / 'translation/sravnenie-i-razlichie/work.json').read_text())
        self.assertEqual(work, {'work_id': 'sravnenie-i-razlichie', 'title': 'Сравнение и различие',
                                'title_zh': '比较与区别'})
        self.assertEqual((project / 'source/sravnenie-i-razlichie.md').read_bytes(), ARTICLE.read_bytes())
        for name in ('glossary.json', 'terms.json'):
            self.assertEqual(json.loads((project / 'glossary' / name).read_text()), [])

    def test_book_project_structure(self):
        project = self.base / 'proj'
        result = self.run_tool('book', project, '--work-id', 'example-book', '--title', 'Наблюдение',
                               '--year', '2026', '--source-edition', '教学示例')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.outside_workflow(project), {
            Path('AGENTS.md'), Path('CLAUDE.md'), Path('.gitignore'),
            Path('glossary/glossary.json'), Path('glossary/terms.json'),
            Path('source/example-book/work.json'),
        })
        work = json.loads((project / 'source/example-book/work.json').read_text())
        self.assertEqual(work, {'work_id': 'example-book', 'title': 'Наблюдение', 'year': 2026,
                                'source_edition': '教学示例'})

    def test_no_work_records_or_git_history(self):
        project = self.base / 'proj'
        self.assertEqual(self.article(project).returncode, 0)
        self.assertEqual(self.run_tool('book', project, '--work-id', 'b', '--title', 'B').returncode, 0)
        names = {p.name for p in project.rglob('*') if 'workflow' not in p.relative_to(project).parts}
        for name in ('index.json', 'status.json', 'handoff.md', 'comments.md', 'source-issues.json',
                     'review-notes.json', '.git'):
            self.assertNotIn(name, names)
        self.assertFalse(list(project.glob('translation/*/*-reports.md')))
        self.assertFalse((project / 'translation/b').exists())

    def test_agent_entry_points_to_bundled_workflow(self):
        project = self.base / 'proj'
        self.assertEqual(self.article(project).returncode, 0)
        self.assertEqual((project / 'CLAUDE.md').read_text(), '@AGENTS.md\n')
        agents = (project / 'AGENTS.md').read_text()
        self.assertIn('workflow/AGENTS.md', agents)
        for rel in ('AGENTS.md', 'STRUCTURE.md', 'AGENT_TASKS.md', 'LICENSE',
                    'translation/TRANSLATION_WORKFLOW.md', 'translation/ARTICLE_TRANSLATION_WORKFLOW.md',
                    'glossary/GLOSSARY_RULES.md', 'scripts/md_to_latex.py', 'scripts/new_project.py',
                    'WORKFLOW_VERSION.txt'):
            self.assertTrue((project / 'workflow' / rel).is_file(), rel)
        self.assertFalse((project / 'workflow/tests').exists())
        self.assertFalse(list((project / 'workflow').rglob('__pycache__')))
        self.assertEqual(broken_links(project), [])
        self.assertNotIn(str(ROOT), ''.join(p.read_text(encoding='utf-8', errors='ignore')
                                            for p in project.rglob('*') if p.is_file()))

    def test_bundled_workflow_matches_repository(self):
        project = self.base / 'proj'
        self.assertEqual(self.article(project).returncode, 0)
        for rel in ('AGENTS.md', 'translation/TRANSLATION_WORKFLOW.md', 'scripts/md_to_latex.py'):
            self.assertEqual((project / 'workflow' / rel).read_bytes(), (ROOT / rel).read_bytes())

    def test_add_work_keeps_existing_files(self):
        project = self.base / 'proj'
        self.assertEqual(self.article(project).returncode, 0)
        (project / 'translation/sravnenie-i-razlichie/handoff.md').write_text('用户已有的交接\n')
        before = snapshot(project)
        result = self.run_tool('article', project, '--work-id', 'second', '--title', 'Второй')
        self.assertEqual(result.returncode, 0, result.stderr)
        after = snapshot(project)
        self.assertEqual({k: v for k, v in after.items() if k in before}, before)
        self.assertEqual(set(after) - set(before), {Path('translation/second/work.json')})

    def test_existing_work_is_refused_without_changes(self):
        project = self.base / 'proj'
        self.assertEqual(self.article(project).returncode, 0)
        before = snapshot(project)
        for kind, extra in (('article', ['--source', ARTICLE]), ('book', [])):
            result = self.run_tool(kind, project, '--work-id', 'sravnenie-i-razlichie', '--title', 'X', *extra)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('已存在', result.stderr)
        self.assertEqual(snapshot(project), before)

    def test_foreign_directory_is_refused(self):
        project = self.base / 'proj'
        project.mkdir()
        (project / 'notes.txt').write_text('已有文件\n')
        before = snapshot(project)
        result = self.article(project)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(snapshot(project), before)

    def test_empty_directory_becomes_project(self):
        project = self.base / 'proj'
        project.mkdir()
        self.assertEqual(self.article(project).returncode, 0)
        self.assertTrue((project / 'workflow/AGENTS.md').is_file())

    def test_project_inside_workflow_repository_is_refused(self):
        result = self.run_tool('article', ROOT / 'tmp-project', '--work-id', 'x', '--title', 'X')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((ROOT / 'tmp-project').exists())

    def test_success_is_silent(self):
        result = self.article(self.base / 'proj')
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '', ''))

    def test_dry_run_writes_nothing(self):
        project = self.base / 'proj'
        result = self.article(project, '--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('translation/sravnenie-i-razlichie/work.json', result.stdout)
        self.assertFalse(project.exists())

    def test_invalid_input_is_refused(self):
        project = self.base / 'proj'
        cases = [
            ('article', project, '--work-id', 'Bad_ID', '--title', 'X'),
            ('article', project, '--work-id', 'x', '--title', 'X', '--source', self.base / 'missing.md'),
            ('book', project, '--work-id', 'x', '--title', 'X', '--source', ARTICLE),
        ]
        for args in cases:
            self.assertNotEqual(self.run_tool(*args).returncode, 0, args)
        self.assertFalse(project.exists())

    def test_bundled_tool_adds_work_from_project_root(self):
        project = self.base / 'proj'
        self.assertEqual(self.article(project).returncode, 0)
        result = subprocess.run([sys.executable, '-B', 'workflow/scripts/new_project.py', 'book', '.',
                                 '--work-id', 'later-book', '--title', 'Книга'],
                                capture_output=True, text=True, cwd=project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((project / 'source/later-book/work.json').is_file())


if __name__ == '__main__':
    unittest.main()

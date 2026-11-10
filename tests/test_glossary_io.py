"""术语表导出与导入：交换格式、状态、冲突与校验。"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/glossary_io.py'

PERSON = {'id': 'example-person', 'type': 'person', 'canonical': 'Иван Примеров', 'forms': ['Примеров'],
          'zh_preferred': '伊万·普里梅罗夫', 'zh_alternatives': ['普里梅罗夫'], 'status': 'approved',
          'notes': '虚构人物。'}
TERM = {'id': 'example-term', 'canonical': 'сопоставление', 'forms': [], 'zh_preferred': '比较',
        'zh_alternatives': [], 'status': 'approved', 'notes': ''}
DRAFT = {'id': 'example-draft', 'canonical': 'наблюдение', 'forms': [], 'zh_preferred': '观察',
         'zh_alternatives': [], 'status': 'provisional', 'notes': ''}


class GlossaryIOTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / 'source'
        self.source.mkdir()
        self.write(self.source / 'glossary.json', [PERSON])
        self.write(self.source / 'terms.json', [TERM, DRAFT])
        self.write(self.source / 'author.json', [dict(TERM, id='example-concept')])

    def write(self, path, data):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def run_tool(self, *args, stdin=None):
        return subprocess.run([sys.executable, '-B', str(SCRIPT), *map(str, args)],
                              capture_output=True, text=True, input=stdin)

    def export(self, *paths):
        result = self.run_tool('export', *paths)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_export_format_and_order(self):
        data = self.export(self.source)
        self.assertEqual([(e['collection'], e['id']) for e in data],
                         [('glossary', 'example-person'), ('terms', 'example-term'),
                          ('author', 'example-concept')])
        self.assertEqual(list(data[0]), ['collection', 'id', 'canonical', 'forms', 'zh_preferred',
                                         'zh_alternatives', 'notes', 'type'])
        self.assertNotIn('type', data[1])
        self.assertTrue(all('status' not in e for e in data))

    def test_export_selected_files_keeps_given_order(self):
        data = self.export(self.source / 'author.json', self.source / 'glossary.json')
        self.assertEqual([e['collection'] for e in data], ['author', 'glossary'])

    def test_export_rejects_invalid_approved_entry(self):
        self.write(self.source / 'glossary.json', [dict(PERSON, type='place')])
        result = self.run_tool('export', self.source)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
        self.assertIn('type', result.stderr)

    def test_export_ignores_invalid_non_approved_entry(self):
        self.write(self.source / 'terms.json', [TERM, dict(DRAFT, zh_preferred='')])
        self.assertEqual(len(self.export(self.source / 'terms.json')), 1)

    def test_round_trip_as_provisional_by_default(self):
        exchange = self.base / 'exchange.json'
        exchange.write_text(json.dumps(self.export(self.source), ensure_ascii=False), encoding='utf-8')
        target = self.base / 'target'
        target.mkdir()
        result = self.run_tool('import', exchange, target)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '', ''))
        person = json.loads((target / 'glossary.json').read_text())
        self.assertEqual(person, [dict(PERSON, status='provisional')])
        self.assertEqual(list(person[0]), list(PERSON))
        self.assertEqual(json.loads((target / 'terms.json').read_text()), [dict(TERM, status='provisional')])

    def test_import_approved_and_stdin(self):
        target = self.base / 'target'
        target.mkdir()
        result = self.run_tool('import', '-', target, '--approved',
                               stdin=json.dumps(self.export(self.source / 'terms.json')))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((target / 'terms.json').read_text()), [TERM])

    def test_existing_entries_block_import_without_changes(self):
        exchange = self.base / 'exchange.json'
        exchange.write_text(json.dumps(self.export(self.source)), encoding='utf-8')
        before = {p.name: p.read_bytes() for p in self.source.iterdir()}
        result = self.run_tool('import', exchange, self.source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('terms/example-term', result.stderr)
        self.assertEqual({p.name: p.read_bytes() for p in self.source.iterdir()}, before)

    def test_skip_existing_appends_only_new_entries(self):
        new = {'collection': 'terms', 'id': 'example-new', 'canonical': 'различие', 'forms': [],
               'zh_preferred': '区别', 'zh_alternatives': [], 'notes': ''}
        exchange = self.base / 'exchange.json'
        exchange.write_text(json.dumps(self.export(self.source) + [new]), encoding='utf-8')
        dry = self.run_tool('import', exchange, self.source, '--skip-existing', '-n')
        self.assertEqual(dry.stdout, 'terms/example-new\n')
        self.assertEqual(len(json.loads((self.source / 'terms.json').read_text())), 2)
        result = self.run_tool('import', exchange, self.source, '--skip-existing')
        self.assertEqual(result.returncode, 0, result.stderr)
        terms = json.loads((self.source / 'terms.json').read_text())
        self.assertEqual([e['id'] for e in terms], ['example-term', 'example-draft', 'example-new'])
        self.assertEqual(terms[-1]['status'], 'provisional')
        self.assertEqual(json.loads((self.source / 'glossary.json').read_text()), [PERSON])

    def test_invalid_input_is_refused(self):
        target = self.base / 'target'
        target.mkdir()
        base = {'collection': 'terms', 'id': 'x', 'canonical': 'a', 'forms': [], 'zh_preferred': '甲',
                'zh_alternatives': [], 'notes': ''}
        cases = [
            [dict(base, zh_preferred='')],
            [dict(base, collection='Bad Name')],
            [dict(base, status='approved')],
            [dict(base, type='person')],
            [dict(base, collection='glossary')],
            [dict(base, forms=[''])],
            [base, base],
        ]
        for entries in cases:
            result = self.run_tool('import', '-', target, stdin=json.dumps(entries, ensure_ascii=False))
            self.assertNotEqual(result.returncode, 0, entries)
        self.assertEqual(list(target.iterdir()), [])


if __name__ == '__main__':
    unittest.main()

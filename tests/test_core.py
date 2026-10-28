import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from impact_trail import AnalysisError, analyze
from impact_trail.cli import main
from impact_trail.render import render_html, render_markdown, render_text


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, path, text=""):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8")

    def paths(self, result):
        return {x['path'] for x in result['impacts']}

    def test_transitive_evidence(self):
        self.put('app/prices.py', 'RATE=1')
        self.put('app/cart.py', 'from .prices import RATE')
        self.put('tests/test_cart.py', 'from app.cart import total')
        result = analyze(self.root, ['app/prices.py'])
        self.assertEqual(result['candidate_tests'], ['tests/test_cart.py'])
        trail = result['impacts'][-1]['trail']
        self.assertEqual([x['dependency'] for x in trail], ['app/prices.py', 'app/cart.py'])
        self.assertEqual(trail[0]['line'], 1)

    def test_cycle_terminates(self):
        self.put('a.py', 'import b')
        self.put('b.py', 'import a')
        self.assertEqual(self.paths(analyze(self.root, ['a.py'])), {'a.py', 'b.py'})

    def test_src_and_alias(self):
        self.put('src/pkg/value.py', 'VALUE=1')
        self.put('tests/test_value.py', 'import pkg.value as value')
        self.assertEqual(analyze(self.root, ['src/pkg/value.py'])['candidate_tests'], ['tests/test_value.py'])

    def test_from_submodule(self):
        self.put('pkg/value.py', '')
        self.put('use.py', 'from pkg import value')
        self.assertIn('use.py', self.paths(analyze(self.root, ['pkg/value.py'])))

    def test_parent_init(self):
        self.put('pkg/__init__.py')
        self.put('pkg/value.py')
        self.put('use.py', 'import pkg.value')
        self.assertIn('use.py', self.paths(analyze(self.root, ['pkg/__init__.py'])))

    def test_relative_init(self):
        self.put('pkg/__init__.py', 'from .value import VALUE')
        self.put('pkg/value.py', 'VALUE=1')
        self.put('use.py', 'import pkg')
        self.assertEqual(len(analyze(self.root, ['pkg/value.py'])['impacts']), 3)

    def test_parent_relative(self):
        self.put('pkg/value.py')
        self.put('pkg/sub/use.py', 'from .. import value')
        self.assertIn('pkg/sub/use.py', self.paths(analyze(self.root, ['pkg/value.py'])))

    def test_star_import(self):
        self.put('a.py')
        self.put('b.py', 'from a import *')
        self.assertIn('b.py', self.paths(analyze(self.root, ['a.py'])))

    def test_type_checking_is_conservative(self):
        self.put('a.py')
        self.put('b.py', 'if False:\n import a')
        self.assertIn('b.py', self.paths(analyze(self.root, ['a.py'])))

    def test_conftest_scope_and_helper(self):
        self.put('helper.py')
        self.put('tests/conftest.py', 'import helper')
        self.put('tests/sub/test_a.py')
        self.put('other/test_b.py')
        self.assertEqual(analyze(self.root, ['helper.py'])['candidate_tests'], ['tests/sub/test_a.py'])

    def test_syntax_warning(self):
        self.put('bad.py', 'invalid syntax here!')
        self.assertTrue(analyze(self.root, ['bad.py'])['full_suite_recommended'])

    def test_dynamic_import_warning(self):
        self.put('a.py', '__import__("thing")')
        self.assertTrue(analyze(self.root, ['a.py'])['warnings'])

    def test_unknown_file_warning(self):
        self.put('test_a.py')
        result = analyze(self.root, ['pyproject.toml'])
        self.assertTrue(result['full_suite_recommended'])
        self.assertEqual(result['candidate_tests'], [])

    def test_multiple_origins_shortest_path(self):
        self.put('a.py')
        self.put('b.py', 'import a')
        self.put('c.py', 'import b')
        result = analyze(self.root, ['a.py', 'b.py'])
        self.assertEqual(next(x for x in result['impacts'] if x['path']=='c.py')['origin'], 'b.py')

    def test_deterministic(self):
        self.put('b.py', 'import a')
        self.put('a.py')
        self.assertEqual(analyze(self.root, ['b.py','a.py']), analyze(self.root, ['a.py','b.py']))

    def test_path_escape_rejected(self):
        for path in ['../secret.py', '/etc/a.py', 'C:\\secret.py']:
            with self.assertRaises(AnalysisError):
                analyze(self.root, [path])

    def test_symlink_not_read(self):
        with tempfile.TemporaryDirectory() as outside:
            p = Path(outside) / 'bad.py'
            p.write_text('import secret')
            try:
                (self.root / 'bad.py').symlink_to(p)
            except OSError:
                self.skipTest('symlinks unavailable')
            self.assertEqual(analyze(self.root, ['bad.py'])['files_analyzed'], 0)

    def test_xss_escaped(self):
        self.put('a.py')
        result = analyze(self.root, ['<img src=x onerror=alert(1)>.py'])
        self.assertNotIn('<img src=x', render_html(result))
        self.assertNotIn('<img src=x', render_markdown(result))

    def test_terminal_escape(self):
        result = analyze(self.root, ['\x1b[31m.py'])
        self.assertNotIn('\x1b', render_text(result))

    def test_cli_json(self):
        self.put('a.py')
        target = self.root / 'report.json'
        self.assertEqual(main(['--root', str(self.root), '--changed', 'a.py', '--format', 'json', '--output', str(target)]), 0)
        self.assertEqual(json.loads(target.read_text())['schema_version'], 1)

    def test_strict_warnings(self):
        self.assertEqual(main(['--root', str(self.root), '--changed', 'unknown', '--strict', '--output', str(self.root / 'report')]), 2)

    def test_ambiguous_modules(self):
        self.put('one/app.py')
        self.put('two/app.py')
        self.put('test_app.py', 'import app')
        result = analyze(self.root, ['one/app.py'], source_roots=['one','two','.'])
        self.assertTrue(result['warnings'])
        self.assertIn('test_app.py', result['candidate_tests'])


class GitTests(AnalysisTests):
    # Inherits the analysis tests as well: both plain and initialized Git trees.
    def setUp(self):
        super().setUp()
        self.git('init', '-q')
        self.git('config', 'user.email', 'tests@example.invalid')
        self.git('config', 'user.name', 'Test Fixture')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.STDOUT)

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')

    def test_deleted_file_preserves_imports(self):
        self.put('a.py')
        self.put('b.py', 'import a')
        self.put('test_b.py', 'import b')
        self.commit()
        (self.root / 'a.py').unlink()
        result = analyze(self.root)
        self.assertEqual(result['candidate_tests'], ['test_b.py'])
        self.assertIn('a.py', result['changed'])

    def test_removed_import_kept_from_base(self):
        self.put('a.py')
        self.put('b.py', 'import a')
        self.put('test_b.py', 'import b')
        self.commit()
        self.put('b.py', '# import removed')
        result = analyze(self.root, ['a.py'], base='HEAD')
        self.assertIn('test_b.py', result['candidate_tests'])
        self.assertEqual(next(x for x in result['impacts'] if x['path']=='b.py')['trail'][0]['snapshot'], 'base')

    def test_rename_both_paths(self):
        self.put('a.py')
        self.put('test_a.py', 'import a')
        self.commit()
        self.git('mv', 'a.py', 'renamed.py')
        result = analyze(self.root)
        self.assertEqual(result['changed'], ['a.py', 'renamed.py'])
        self.assertIn('test_a.py', result['candidate_tests'])

    def test_spaces_and_newlines(self):
        if os.name == 'nt':
            self.skipTest('Windows disallows newline characters in filenames')
        self.put('odd name\nfile.py')
        self.commit()
        self.put('odd name\nfile.py', 'x=1')
        self.assertEqual(analyze(self.root)['changed'], ['odd name\nfile.py'])

    def test_untracked_and_ignored(self):
        self.put('.gitignore', 'ignored.py\n')
        self.put('a.py')
        self.commit()
        self.put('ignored.py', 'invalid syntax!')
        self.put('new.py')
        self.assertEqual(analyze(self.root)['changed'], ['new.py'])

    def test_clean_repo(self):
        self.put('a.py')
        self.commit()
        self.assertEqual(analyze(self.root)['impacts'], [])

    def test_invalid_base(self):
        self.put('a.py')
        self.commit()
        with self.assertRaises(AnalysisError):
            analyze(self.root, base='--help')


if __name__ == '__main__':
    unittest.main()

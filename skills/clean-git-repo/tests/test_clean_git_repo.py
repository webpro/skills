import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'clean-git-repo.sh'
BASH = os.environ.get('BASH_BIN', '/bin/bash')


class IgnoredWorktreeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='clean-git-repo-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / 'repo'
        self.worktree = self.root / 'linked'
        self.env = dict(
            os.environ,
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_CONFIG_SYSTEM=os.devnull,
            PATH=os.path.dirname(BASH) + os.pathsep + os.environ['PATH'],
        )
        self.git('init', '-q', '-b', 'main', str(self.repo), cwd=self.root)
        self.git('config', 'user.name', 'Cleanup Test')
        self.git('config', 'user.email', 'cleanup@example.com')
        (self.repo / '.gitignore').write_text('node_modules/\ndist/\n.env\ncache/\n')
        (self.repo / 'source.txt').write_text('source\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'Base')
        self.git('worktree', 'add', '-qb', 'merged', str(self.worktree))

    def git(self, *args, cwd=None):
        result = subprocess.run(
            ['git', *args], cwd=cwd or self.repo, env=self.env,
            text=True, capture_output=True, check=True, stdin=subprocess.DEVNULL,
        )
        return result.stdout

    def write(self, name, content='generated\n'):
        path = self.worktree / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def run_cleanup(self, *args):
        result = subprocess.run(
            [BASH, str(SCRIPT), '--no-fetch', '--no-gh', *args],
            cwd=self.repo, env=self.env, text=True, capture_output=True,
            check=True, stdin=subprocess.DEVNULL,
        )
        self.assertIn('Repo: ' + str(self.repo), result.stdout)
        return result.stdout

    def assert_preserved(self):
        self.assertTrue(self.worktree.is_dir())
        self.assertEqual(self.git('branch', '--list', 'merged').strip(), '+ merged')

    def test_dependency_and_build_directories_are_removable(self):
        self.write('node_modules/dependency/index.js')
        self.write('packages/has space/dist/bundle.js')
        self.write('packages/has\nnewline/node_modules/dependency/index.js')
        report = self.run_cleanup()
        self.assertIn('SAFE TO DELETE', report)
        self.assertIn('merged into main; worktree ' + str(self.worktree), report)
        self.assert_preserved()
        self.assertTrue((self.worktree / 'node_modules/dependency/index.js').exists())
        result = self.run_cleanup('--apply')
        self.assertIn('removed worktree ' + str(self.worktree), result)
        self.assertFalse(self.worktree.exists())
        self.assertEqual(self.git('branch', '--list', 'merged'), '')

    def test_ignored_output_beside_tracked_files_is_removable(self):
        self.write('dist/README.md', 'tracked\n')
        self.git('add', '-f', 'dist/README.md', cwd=self.worktree)
        self.git('commit', '-qm', 'Tracked dist file', cwd=self.worktree)
        self.git('merge', '--ff-only', 'merged')
        self.write('dist/bundle.js')
        self.assertIn('SAFE TO DELETE', self.run_cleanup())
        self.run_cleanup('--apply')
        self.assertFalse(self.worktree.exists())

    def test_other_ignored_files_still_protect_the_worktree(self):
        self.write('node_modules/dependency/index.js')
        self.write('.env', 'local settings\n')
        self.run_cleanup('--apply')
        self.assert_preserved()
        self.assertEqual((self.worktree / '.env').read_text(), 'local settings\n')

    def test_unknown_ignored_parent_is_not_disposable(self):
        self.write('cache/dist/bundle.js')
        self.run_cleanup('--apply')
        self.assert_preserved()

    def test_ignored_file_named_dist_is_not_a_build_directory(self):
        self.git('config', 'core.excludesFile', str(self.root / 'global-ignore'))
        (self.root / 'global-ignore').write_text('dist\n')
        self.write('dist', 'local data\n')
        self.run_cleanup('--apply')
        self.assert_preserved()

    def test_dirty_and_untracked_content_still_protect_the_worktree(self):
        self.write('node_modules/dependency/index.js')
        self.write('source.txt', 'edited\n')
        self.write('notes.txt', 'untracked\n')
        self.assertIn('dirty worktree', self.run_cleanup('--apply'))
        self.assert_preserved()
        self.assertEqual((self.worktree / 'source.txt').read_text(), 'edited\n')

    def test_untracked_content_still_protects_the_worktree(self):
        self.write('dist/bundle.js')
        self.write('notes.txt', 'untracked\n')
        self.assertIn('dirty worktree', self.run_cleanup('--apply'))
        self.assert_preserved()

    def test_tracked_edit_inside_dist_is_not_disposable(self):
        self.write('dist/README.md', 'tracked\n')
        self.git('add', '-f', 'dist/README.md', cwd=self.worktree)
        self.git('commit', '-qm', 'Tracked dist file', cwd=self.worktree)
        self.git('merge', '--ff-only', 'merged')
        self.write('dist/README.md', 'edited\n')
        self.assertIn('dirty worktree', self.run_cleanup('--apply'))
        self.assert_preserved()

    def test_submodule_worktree_with_generated_files_is_preserved(self):
        oid = self.git('rev-parse', 'HEAD').strip()
        self.write('.gitmodules', '[submodule "vendor"]\n\tpath = vendor\n\turl = ../repo\n')
        self.git('add', '.gitmodules', cwd=self.worktree)
        self.git('update-index', '--add', '--cacheinfo', '160000', oid, 'vendor', cwd=self.worktree)
        self.git('commit', '-qm', 'Add submodule', cwd=self.worktree)
        self.git('merge', '--ff-only', 'merged')
        (self.worktree / 'vendor').mkdir()
        self.write('dist/bundle.js')
        self.assertIn('worktree contains submodules', self.run_cleanup('--apply'))
        self.assert_preserved()

    def test_locked_worktree_with_generated_files_is_preserved(self):
        self.write('dist/bundle.js')
        self.git('worktree', 'lock', str(self.worktree))
        self.assertIn('locked worktree', self.run_cleanup('--apply'))
        self.assert_preserved()

    def test_detached_worktree_with_generated_files_is_preserved(self):
        self.git('checkout', '--detach', cwd=self.worktree)
        self.write('dist/bundle.js')
        self.assertIn('detached HEAD', self.run_cleanup('--apply'))
        self.assertTrue(self.worktree.is_dir())


if __name__ == '__main__':
    unittest.main()

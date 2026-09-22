import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(shutil.which('node'), 'Node is required for the Codex launcher')
class LauncherTest(unittest.TestCase):
    def test_registered_binary_launch_and_hash_rejection(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            project = base / 'project with spaces'
            problem = base / 'problem.md'
            problem.write_text('Fixture task')
            init = subprocess.run([sys.executable, str(ROOT / '.agents/skills/mathmodel-workflow/scripts/workflow.py'),
                                   'init', '--project', str(project), '--problem', str(problem)], capture_output=True, text=True)
            self.assertEqual(init.returncode, 0, init.stderr)
            binary = base / 'fake-codex'
            binary.write_text('#!/usr/bin/env node\nconsole.log(JSON.stringify({cwd:process.cwd(),args:process.argv.slice(2)}));\n')
            binary.chmod(0o700)
            registration = base / 'runtime.json'
            registration.write_text(json.dumps({'kind': 'source-build', 'binary': str(binary),
                                    'sha256': hashlib.sha256(binary.read_bytes()).hexdigest()}))
            args = ['node', str(ROOT / 'scripts/start-modeling.mjs'), '--project', str(project), '--registration', str(registration)]
            check = subprocess.run([*args, '--check'], capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertTrue(json.loads(check.stdout)['sha256_verified'])
            launched = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(launched.returncode, 0, launched.stderr)
            result = json.loads(launched.stdout)
            self.assertEqual(Path(result['cwd']).resolve(), project.resolve())
            self.assertEqual(result['args'][:6], ['-C', str(project.resolve()), '-s', 'workspace-write', '-a', 'on-request'])
            self.assertIn('SKILL.md', result['args'][6])
            binary.write_text(binary.read_text() + '\n// changed\n')
            rejected = subprocess.run(args, capture_output=True, text=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn('SHA-256 mismatch', rejected.stderr)


if __name__ == '__main__':
    unittest.main()

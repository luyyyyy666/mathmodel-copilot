import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
WF = ROOT / '.agents/skills/mathmodel-workflow/scripts/workflow.py'


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / 'project'
        self.problem = self.base / 'problem.md'
        self.problem.write_text('Find a feasible and reproducible solution.')
        self.call('init', '--problem', str(self.problem))

    def call(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(WF), args[0], '--project', str(self.project), *args[1:]],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return json.loads(result.stdout or result.stderr)

    def write(self, name, text='Substantive task evidence.'):
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def baseline_ready(self):
        self.write('problem.md')
        self.call('complete', '--stage', 'understand')
        self.write('data-report.md')
        self.call('complete', '--stage', 'data')
        self.write('baseline.md')

    def execute(self, stage='baseline', name='result.json', code=None, ok=True, timeout=10):
        self.write('compute.py', code or f'from pathlib import Path\nPath({name!r}).write_text("42")\n')
        return self.call('run', '--stage', stage, '--input', 'compute.py', '--output', name,
                         '--timeout', str(timeout), '--', sys.executable, 'compute.py', ok=ok)

    def test_dependency_and_required_execution(self):
        self.call('complete', '--stage', 'baseline', ok=False)
        self.baseline_ready()
        self.call('complete', '--stage', 'baseline', ok=False)
        record = self.execute()
        self.call('complete', '--stage', 'baseline', '--execution', record['id'])
        self.assertEqual(self.call('next')['next']['id'], 'improve')

    def test_failed_command_and_missing_output_do_not_unlock(self):
        self.baseline_ready()
        record = self.execute(code='raise SystemExit(7)', ok=False)
        self.assertEqual(record['exit_code'], 7)
        self.call('complete', '--stage', 'baseline', '--execution', record['id'], ok=False)
        record = self.execute(code='print("no output")', ok=False)
        self.assertIn('Missing file', record['error'])
        self.assertEqual(self.call('next')['next']['id'], 'baseline')

    def test_timeout_is_failure(self):
        self.baseline_ready()
        record = self.execute(code='import time\ntime.sleep(5)', timeout=0.05, ok=False)
        self.assertEqual(record['status'], 'failed')
        self.assertIn('timeout', record['error'])
        self.assertEqual(self.call('status')['unresolved_executions'], [])

    def test_input_and_output_drift_invalidate_progress(self):
        self.baseline_ready()
        record = self.execute()
        self.write('result.json', 'tampered')
        self.call('complete', '--stage', 'baseline', '--execution', record['id'], ok=False)
        self.write('inputs/00-problem.md', 'User changed the task')
        self.call('check', ok=False)
        self.call('refresh-inputs', '--reason', 'User supplied corrected problem')
        self.assertEqual(self.call('next')['next']['id'], 'understand')
        self.call('check')

    def test_reopen_preserves_history_and_prevents_stale_execution(self):
        self.baseline_ready()
        record = self.execute()
        self.call('complete', '--stage', 'baseline', '--execution', record['id'])
        self.call('skip', '--stage', 'improve', '--reason', 'Baseline is sufficient')
        self.call('reopen', '--stage', 'baseline', '--reason', 'Correct model')
        self.call('complete', '--stage', 'baseline', '--execution', record['id'], ok=False)
        state = json.loads((self.project / '.workflow/state.json').read_text())
        self.assertIn('baseline', state['history'][-1]['stages'])
        self.assertNotIn('improve', state['stages'])

    def test_only_improvement_is_optional(self):
        self.call('skip', '--stage', 'understand', '--reason', 'skip all', ok=False)
        self.baseline_ready()
        record = self.execute()
        self.call('complete', '--stage', 'baseline', '--execution', record['id'])
        self.call('skip', '--stage', 'improve', '--reason', '   ', ok=False)
        self.call('skip', '--stage', 'improve', '--reason', 'Already sufficient')
        self.call('skip', '--stage', 'verify', '--reason', 'No time', ok=False)

    def test_symlink_and_escape_rejected(self):
        self.write('problem.md')
        (self.project / 'outside.md').symlink_to(self.problem)
        self.call('complete', '--stage', 'understand', '--artifact', 'outside.md', ok=False)
        self.call('complete', '--stage', 'understand', '--artifact', '../problem.md', ok=False)

    def test_stale_output_and_run_budget(self):
        other = self.base / 'limited'
        self.project = other
        self.call('init', '--problem', str(self.problem), '--max-runs', '1')
        self.baseline_ready()
        self.write('result.json', 'old')
        self.execute(ok=False)
        (self.project / 'result.json').unlink()
        self.execute()
        self.execute(name='new.json', ok=False)
        self.assertEqual(self.call('status')['runs_remaining'], 0)

    def test_verification_must_be_generated_by_recorded_command(self):
        self.baseline_ready()
        record = self.execute()
        self.call('complete', '--stage', 'baseline', '--execution', record['id'])
        self.call('skip', '--stage', 'improve', '--reason', 'Enough')
        # Do not mutate previously registered compute.py.
        report = {'verdict': 'pass', 'checks': [{'name': 'check', 'status': 'pass',
                   'detail': 'Evidence checked', 'evidence': ['proof.txt']}], 'limitations': []}
        self.write('verification.json', json.dumps(report))
        self.write('proof.txt')
        self.call('complete', '--stage', 'verify', ok=False)
        report['verdict'] = 'fail'
        self.write('verification.json', json.dumps(report))
        self.call('complete', '--stage', 'verify', ok=False)

    def test_interrupted_record_blocks_automatic_rerun(self):
        self.baseline_ready()
        ident = 'a' * 32
        receipt = {'id': ident, 'status': 'running', 'pid': None}
        self.write(f'.workflow/executions/{ident}.json', json.dumps(receipt))
        self.call('check', ok=False)
        self.execute(ok=False)
        self.call('abandon', '--execution', ident, '--reason', 'Confirmed no process or external effect remains')
        self.execute()

    def test_theory_and_requested_pdf_are_not_silently_skipped(self):
        self.project = self.base / 'theory'
        self.call('init', '--problem', str(self.problem), '--kind', 'theory', '--pdf')
        self.baseline_ready()
        self.call('complete', '--stage', 'baseline')
        self.call('skip', '--stage', 'improve', '--reason', 'Proof is complete')
        report = {'verdict': 'pass', 'checks': [{'name': 'proof review', 'status': 'pass',
                   'detail': 'Agent reviewed assumptions and boundary; not a formal proof',
                   'evidence': ['proof.md']}], 'limitations': ['No formal prover']}
        self.write('proof.md', 'Review evidence for the fixture.')
        self.write('verification.json', json.dumps(report))
        self.call('complete', '--stage', 'verify')
        self.write('report.md')
        self.call('complete', '--stage', 'report', ok=False)
        self.write('report.pdf', 'Not a real PDF')
        self.write('render-review.md')
        self.call('complete', '--stage', 'report', ok=False)

    def test_init_never_overwrites_existing_project(self):
        before = (self.project / '.workflow/state.json').read_bytes()
        self.call('init', '--problem', str(self.problem), ok=False)
        self.assertEqual(before, (self.project / '.workflow/state.json').read_bytes())

    def test_bundle_works_after_original_repository_is_absent(self):
        bundled = self.project / '.agents/skills/mathmodel-workflow/scripts/workflow.py'
        result = subprocess.run([sys.executable, str(bundled), 'next', '--project', str(self.project)],
                                cwd=self.base, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['next']['id'], 'understand')

    def test_end_to_end_export_and_independent_reproduction(self):
        project, delivery = self.base / 'demo', self.base / 'delivery'
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/demo-workflow.py'),
                                '--project', str(project), '--destination', str(delivery)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['model_calls'], 0)
        manifest = json.loads((delivery / 'delivery-manifest.json').read_text())
        for ref in manifest['files']:
            self.assertEqual(hashlib.sha256((delivery / ref['path']).read_bytes()).hexdigest(), ref['sha256'])
        replay = subprocess.run([sys.executable, 'reproduce.py', 'new-replay.json'], cwd=delivery, capture_output=True, text=True)
        self.assertEqual(replay.returncode, 0, replay.stderr)
        candidate = json.loads((delivery / 'results/candidate.json').read_text())
        self.assertEqual(candidate['objective'], 16)  # A,C: 2*1 + 1*3 + 3*1 + 2*4
        self.project = project
        self.assertTrue(self.call('status')['complete'])
        self.write('report.md', 'changed result')
        self.call('export', '--destination', str(self.base / 'bad-export'), ok=False)
        self.assertFalse((self.base / 'bad-export').exists())


if __name__ == '__main__':
    unittest.main()

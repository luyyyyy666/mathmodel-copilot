import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import types
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / '.agents/skills/mathmodel-workflow/scripts'
sys.path.insert(0, str(SCRIPTS))
import publication as pub
from publication_contract import publication_files


class PublicationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.state = {'format': 2, 'require_pdf': True}

    def write(self, name, content):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content if isinstance(content, bytes) else content.encode())
        return {'path': name, 'sha256': pub.sha(p)}

    def gate(self, stage, executions=()):
        return publication_files(self.root, self.state, stage, executions, pub.local)

    def test_figures_require_execution_and_current_visual_review(self):
        inputs = [self.write('plot.py', 'plot'), self.write('data.json', '[16]')]
        outputs = [self.write('plot.png', b'\x89PNG\r\n\x1a\nfixture'), self.write('plot.pdf', b'%PDF-fixture')]
        self.write('figure-manifest.json', json.dumps({'figures': [{'id': 'a', 'question': 'Compare?', 'caption': 'Comparison',
                   'script': 'plot.py', 'data': ['data.json'], 'outputs': ['plot.png', 'plot.pdf']}]}))
        review = {'figures': [{'id': 'a', 'status': 'pass', 'sha256': outputs[0]['sha256'], 'observations': 'Test fixture review'}]}
        self.write('figure-review.json', json.dumps(review))
        with self.assertRaisesRegex(ValueError, 'execution input'):
            self.gate('figures')
        runs = [{'inputs': inputs, 'outputs': outputs}]
        self.assertIn('plot.pdf', self.gate('figures', runs))
        review['figures'][0]['sha256'] = 'stale'
        self.write('figure-review.json', json.dumps(review))
        with self.assertRaisesRegex(ValueError, 'current PNG'):
            self.gate('figures', runs)
        self.write('figure-review.json', json.dumps({'figures': []}))
        with self.assertRaisesRegex(ValueError, 'every figure'):
            self.gate('figures', runs)

    def test_no_figures_requires_reason(self):
        self.write('figure-manifest.json', '{"figures":[]}')
        with self.assertRaisesRegex(ValueError, 'reason'):
            self.gate('figures')
        self.write('figure-manifest.json', '{"figures":[],"reason":"Pure symbolic proof"}')
        self.gate('figures')

    def test_paper_requires_claim_evidence_and_vector_sources(self):
        self.write('main.tex', 'source')
        self.write('result.json', '16')
        self.write('figure-manifest.json', '{"figures":[{"id":"a","outputs":["plot.pdf"]}]}')
        manifest = {'main': 'main.tex', 'files': ['main.tex'], 'bibliography': 'none',
                    'claims': [{'text': '16', 'evidence': 'result.json'}]}
        self.write('paper-manifest.json', json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'omits figure'):
            self.gate('report')
        self.write('plot.pdf', b'%PDF-fixture')
        manifest['files'].append('plot.pdf')
        self.write('paper-manifest.json', json.dumps(manifest))
        self.gate('report')
        (self.root / 'result.json').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing/empty'):
            self.gate('report')

    def test_render_review_covers_all_pages_and_pdf_version(self):
        pdf = self.write('report.pdf', b'%PDF-fixture')
        png = self.write('page.png', b'\x89PNG\r\n\x1a\nfixture')
        manifest = {'pdf': pdf, 'pages': [{'number': 1, **png}]}
        output = self.write('render-manifest.json', json.dumps(manifest))
        review = {'status': 'pass', 'pdf_sha256': pdf['sha256'], 'pages': []}
        self.write('render-review.json', json.dumps(review))
        runs = [{'inputs': [pdf], 'outputs': [output]}]
        with self.assertRaisesRegex(ValueError, 'every page'):
            self.gate('inspect', runs)
        review['pages'] = [{'number': 1, 'sha256': png['sha256'], 'status': 'pass', 'observations': 'Test fixture'}]
        self.write('render-review.json', json.dumps(review))
        self.gate('inspect', runs)
        self.write('report.pdf', b'%PDF-changed')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            self.gate('inspect', runs)

    def compile_args(self):
        self.write('main.tex', 'original source')
        self.write('paper-manifest.json', json.dumps({'main': 'main.tex', 'files': ['main.tex'], 'bibliography': 'bibtex'}))
        return argparse.Namespace(manifest='paper-manifest.json', output='report.pdf', report='compile-report.json',
                                  build='build/test', engine='xelatex', timeout=2)

    def test_compile_routes_bibliography_and_preserves_sources(self):
        args = self.compile_args()
        calls = []
        def run(argv, **kw):
            calls.append(argv[0])
            (kw['cwd'] / 'main.log').write_text('Clean compilation')
            (kw['cwd'] / 'main.pdf').write_bytes(b'%PDF-test fixture')
            return subprocess.CompletedProcess(argv, 0, b'log')
        with patch.object(pub.shutil, 'which', return_value='/fake/tool'), patch.object(pub.subprocess, 'run', side_effect=run):
            result = pub.compile_paper(args, self.root)
        self.assertEqual(result['status'], 'succeeded')
        self.assertEqual(calls, ['xelatex', 'bibtex', 'xelatex', 'xelatex'])
        self.assertEqual((self.root / 'main.tex').read_text(), 'original source')
        with self.assertRaisesRegex(ValueError, 'new build'):
            pub.compile_paper(args, self.root)

    def test_failed_engine_does_not_publish_existing_generated_pdf(self):
        args = self.compile_args()
        def run(argv, **kw):
            (kw['cwd'] / 'main.pdf').write_bytes(b'%PDF-incomplete')
            return subprocess.CompletedProcess(argv, 1, b'failure')
        with patch.object(pub.shutil, 'which', return_value='/fake/tool'), patch.object(pub.subprocess, 'run', side_effect=run):
            result = pub.compile_paper(args, self.root)
        self.assertEqual(result['status'], 'failed')
        self.assertFalse((self.root / 'report.pdf').exists())
        self.assertTrue((self.root / 'compile-report.json').exists())

    def test_compile_gate_rejects_changed_sources_and_failed_receipts(self):
        source = self.write('main.tex', 'original source')
        pdf = self.write('report.pdf', b'%PDF-fixture')
        self.write('paper-manifest.json', '{"files":["main.tex"]}')
        self.write('compile.log', 'log')
        report = {'status': 'succeeded', 'errors': [], 'pdf': pdf, 'sources': [source],
                  'commands': [{'returncode': 0, 'log': 'compile.log'}], 'latex_log': 'compile.log'}
        self.state['stages'] = {'report': {'files': [source]}}
        def runs():
            output = self.write('compile-report.json', json.dumps(report))
            return [{'inputs': [source], 'outputs': [output, pdf]}]
        self.gate('compile', runs())
        report['commands'][0]['returncode'] = 1
        with self.assertRaisesRegex(ValueError, 'command failed'):
            self.gate('compile', runs())
        report['commands'][0]['returncode'] = 0
        report['sources'] = [self.write('main.tex', 'modified source')]
        with self.assertRaisesRegex(ValueError, 'frozen paper'):
            self.gate('compile', runs())

    def test_unicode_check_rejects_missing_chinese_body(self):
        page = types.SimpleNamespace(extract_text=lambda: 'Latin text only')
        reader = types.SimpleNamespace(pages=[page])
        fake = types.SimpleNamespace(PdfReader=lambda _: reader)
        with patch.dict(sys.modules, {'pypdf': fake}):
            with self.assertRaisesRegex(ValueError, 'Unicode text missing'):
                pub.verify_pdf_unicode(self.root/'report.pdf', ['中文正文'])

    def test_unicode_check_rejects_unmapped_composite_font(self):
        class Ref(dict):
            def get_object(self): return self
        class Page(dict):
            def extract_text(self): return '中文正文'
        font = Ref({'/Subtype': '/Type0', '/BaseFont': 'CJK'})
        page = Page({'/Resources': {'/Font': {'/F1': font}}})
        fake = types.SimpleNamespace(PdfReader=lambda _: types.SimpleNamespace(pages=[page]))
        with patch.dict(sys.modules, {'pypdf': fake}):
            with self.assertRaisesRegex(ValueError, 'Unicode mapping'):
                pub.verify_pdf_unicode(self.root/'report.pdf', ['中文正文'])
            font['/ToUnicode'] = 'embedded map'
            font['/DescendantFonts'] = [Ref({'/FontDescriptor': Ref({})})]
            with self.assertRaisesRegex(ValueError, 'not embedded'):
                pub.verify_pdf_unicode(self.root/'report.pdf', ['中文正文'])
            font['/DescendantFonts'][0]['/FontDescriptor']['/FontFile2'] = 'embedded font'
            self.assertEqual(pub.verify_pdf_unicode(self.root/'report.pdf', ['中文正文'])['status'], 'pass')

    def test_missing_engine_and_diagnostics(self):
        args = self.compile_args()
        with patch.object(pub.shutil, 'which', return_value=None):
            self.assertEqual(pub.compile_paper(args, self.root)['status'], 'failed')
        findings = pub.diagnostics("LaTeX Warning: Reference `x' undefined\nMissing character: x\nOverfull box\n! Undefined control sequence")
        self.assertEqual(len(findings['errors']), 3)
        self.assertEqual(len(findings['warnings']), 1)

    def test_poppler_zero_exit_with_font_errors_is_rejected(self):
        self.write('report.pdf', b'%PDF-fixture')
        args = argparse.Namespace(pdf='report.pdf', output_dir='pages', report='render.json', dpi=100,
                                  renderer='poppler', max_pages=10, timeout=2)
        def run(argv, **kw):
            if argv[0] == 'pdfinfo':
                return subprocess.CompletedProcess(argv, 0, 'Pages: 1', '')
            return subprocess.CompletedProcess(argv, 0, b'', b"Syntax Error: Missing language pack for Adobe-GB1")
        with patch.object(pub.shutil, 'which', return_value='/fake/tool'), patch.object(pub.subprocess, 'run', side_effect=run):
            with self.assertRaisesRegex(ValueError, 'PDF rendering errors'):
                pub.render(args, self.root)
        self.assertFalse((self.root / 'render.json').exists())
        self.assertIn('Adobe-GB1', (self.root / 'pages/renderer.log').read_text())

    def test_legacy_upgrade_preserves_math_and_invalidates_delivery(self):
        project = self.root / 'legacy'
        result = subprocess.run([sys.executable, str(ROOT/'scripts/demo-workflow.py'), '--project', str(project),
                                 '--destination', str(self.root/'delivery')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        old = json.loads((project/'.workflow/state.json').read_text())
        result = subprocess.run([sys.executable, str(SCRIPTS/'workflow.py'), 'upgrade', '--project', str(project),
                                 '--reason', 'Publication integration'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((project/'.workflow/state.json').read_text())
        self.assertEqual(state['format'], 2)
        self.assertEqual(state['stages']['verify'], old['stages']['verify'])
        self.assertNotIn('report', state['stages'])
        self.assertNotIn('deliver', state['stages'])
        self.assertTrue((project/'.agents/skills/mathmodel-workflow/references/latex.md').exists())


if __name__ == '__main__':
    unittest.main()

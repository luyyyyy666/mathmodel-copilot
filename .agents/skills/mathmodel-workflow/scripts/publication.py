#!/usr/bin/env python3
"""Build declared LaTeX sources and render actual PDF pages; never rewrite paper text."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def need(test, message):
    if not test:
        raise ValueError(message)


def local(root, value):
    p = Path(value)
    need(not p.is_absolute() and '..' not in p.parts and p.parts, f'Expected project-relative path: {value}')
    target = root / p
    need(target.resolve().is_relative_to(root), f'Path escapes project: {value}')
    need(not any(x.is_symlink() for x in [target, *target.parents]), f'Symlink is not supported: {value}')
    return target


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def diagnostics(log):
    errors, warnings = [], []
    for line in log.splitlines():
        if re.search(r'^!|Undefined control sequence|LaTeX Error|Emergency stop|Fatal error|Missing character:|There were undefined (references|citations)|(?:Reference|Citation).*undefined', line, re.I):
            errors.append(line.strip())
        elif re.search(r'Overfull|Underfull|(?:LaTeX|Package .*|Class .*) Warning:|Rerun to get', line, re.I):
            warnings.append(line.strip())
    return {'errors': errors, 'warnings': warnings}


def verify_pdf_unicode(pdf, probes):
    if not probes:
        return None
    need(isinstance(probes, list) and all(isinstance(p, str) and p.strip() for p in probes),
         'unicode_probes must contain nonempty strings')
    from pypdf import PdfReader
    reader = PdfReader(str(pdf))
    text = re.sub(r'\s+', '', '\n'.join(page.extract_text() or '' for page in reader.pages))
    for probe in probes:
        need(re.sub(r'\s+', '', probe) in text, f'PDF Unicode text missing or unreadable: {probe}')
    fonts = []
    for page in reader.pages:
        for ref in page.get('/Resources', {}).get('/Font', {}).values():
            font = ref.get_object()
            if font.get('/Subtype') == '/Type0':
                need(bool(font.get('/ToUnicode')), f'Composite font lacks embedded Unicode mapping: {font.get("/BaseFont")}')
                for descendant in font.get('/DescendantFonts', []):
                    descriptor = descendant.get_object()['/FontDescriptor'].get_object()
                    need(any(k in descriptor for k in ['/FontFile', '/FontFile2', '/FontFile3']), 'Font program is not embedded')
                fonts.append(str(font.get('/BaseFont')))
    return {'status': 'pass', 'probes': probes, 'embedded_fonts': sorted(set(fonts))}


def compile_paper(args, root):
    manifest_path = local(root, args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    need(isinstance(manifest, dict) and isinstance(manifest.get('files'), list), 'Invalid paper manifest')
    need(manifest.get('main') in manifest['files'], 'Main source not declared')
    need(manifest.get('bibliography') in ['none', 'bibtex', 'biber'], 'Choose bibliography backend')
    output, report_path, build = [local(root, p) for p in [args.output, args.report, args.build]]
    need(not any(p.exists() for p in [output, report_path, build]), 'Use new build/output/report paths; preserve earlier attempts')
    source_files = []
    for name in dict.fromkeys(manifest['files']):
        p = local(root, name)
        need(p.is_file(), f'Missing declared source: {name}')
        need(not p.is_relative_to(build), 'Build directory overlaps source')
        source_files.append({'path': name, 'sha256': sha(p)})
    need(args.timeout > 0 and math.isfinite(args.timeout), 'Timeout must be positive and finite')
    engine = args.engine
    if engine == 'auto':
        engine = next((e for e in ['xelatex', 'tectonic', 'pdflatex'] if shutil.which(e)), None)
    report = {'status': 'failed', 'engine': engine, 'sources': source_files, 'commands': [], 'errors': [], 'warnings': []}
    build.mkdir(parents=True)
    try:
        need(engine is not None and shutil.which(engine), 'No LaTeX engine found; configure xelatex, pdflatex or tectonic on PATH')
        need(not (engine == 'tectonic' and manifest['bibliography'] == 'biber'), 'This adapter supports Biber with xelatex/pdflatex; select that engine')
        mirror = build / 'source'
        for ref in source_files:
            dst = mirror / ref['path']
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / ref['path'], dst)
        main = mirror / manifest['main']
        cwd = main.parent
        # Build in the source mirror so .aux, .bib, .tex and relative figure paths agree.
        stem = main.stem
        env = dict(os.environ)

        def execute(argv):
            log = build / f'command-{len(report["commands"]) + 1}.log'
            try:
                result = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, timeout=args.timeout)
                log.write_bytes(result.stdout)
                report['commands'].append({'argv': argv, 'returncode': result.returncode,
                                           'log': str(log.relative_to(root))})
                need(result.returncode == 0, f'Compiler command exited {result.returncode}; see {log.relative_to(root)}')
            except subprocess.TimeoutExpired as exc:
                log.write_bytes(exc.stdout or b'')
                report['commands'].append({'argv': argv, 'returncode': -1, 'log': str(log.relative_to(root))})
                raise ValueError('Compiler timeout; inspect command log') from exc

        if engine == 'tectonic':
            execute([engine, '--untrusted', '--keep-logs', '--keep-intermediates', main.name])
        else:
            argv = [engine, '-no-shell-escape', '-halt-on-error', '-file-line-error', '-interaction=nonstopmode', main.name]
            execute(argv)
            if manifest['bibliography'] != 'none':
                bib = manifest['bibliography']
                need(shutil.which(bib), f'Missing bibliography tool: {bib}')
                execute([bib, stem])
            execute(argv)
            execute(argv)
        latex_log = cwd / f'{stem}.log'
        need(latex_log.is_file(), 'No LaTeX log produced')
        report['latex_log'] = str(latex_log.relative_to(root))
        report.update(diagnostics(latex_log.read_text(errors='replace')))
        need(not report['errors'], 'Unresolved LaTeX errors, citations, references or missing glyphs')
        pdf = cwd / f'{stem}.pdf'
        need(pdf.is_file() and pdf.read_bytes().startswith(b'%PDF-'), 'No valid PDF output')
        report['unicode_check'] = verify_pdf_unicode(pdf, manifest.get('unicode_probes'))
        for ref in source_files:
            need(sha(root / ref['path']) == ref['sha256'], 'Original source changed during compilation')
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pdf, output)
        report['pdf'] = {'path': args.output, 'sha256': sha(output)}
        report['status'] = 'succeeded'
    except (ValueError, OSError, ImportError) as exc:
        report['errors'].append(str(exc))
    write(report_path, report)
    return report


def render(args, root):
    pdf, output, report_path = [local(root, p) for p in [args.pdf, args.output_dir, args.report]]
    need(pdf.is_file(), 'PDF missing')
    need(not output.exists() and not report_path.exists(), 'Use new render output paths')
    need(40 <= args.dpi <= 300, 'DPI must be between 40 and 300')
    if args.renderer == 'pdfium':
        import pypdfium2 as pdfium
        with pdfium.PdfDocument(str(pdf)) as document:
            count = len(document)
            need(0 < count <= args.max_pages, 'Page count exceeds declared rendering limit')
            output.mkdir(parents=True)
            for i in range(count):
                page = document[i]
                bitmap = page.render(scale=args.dpi / 72)
                bitmap.to_pil().save(output / f'page-{i + 1}.png')
                bitmap.close()
                page.close()
    else:
        need(shutil.which('pdfinfo') and shutil.which('pdftoppm'), 'Poppler pdfinfo and pdftoppm are required')
        info = subprocess.run(['pdfinfo', str(pdf)], capture_output=True, text=True, timeout=30, check=True)
        match = re.search(r'^Pages:\s+(\d+)', info.stdout, re.M)
        need(match is not None, 'Cannot determine PDF page count')
        count = int(match.group(1))
        need(0 < count <= args.max_pages, 'Page count exceeds declared rendering limit')
        output.mkdir(parents=True)
        result = subprocess.run(['pdftoppm', '-png', '-r', str(args.dpi), str(pdf), str(output / 'page')],
                                capture_output=True, timeout=args.timeout, check=True)
        diagnostic = result.stderr.decode(errors='replace')
        (output / 'renderer.log').write_text(diagnostic, encoding='utf-8')
        need(not re.search(r'Syntax Error|Missing language pack|Unknown font|No font in', diagnostic, re.I),
             'PDF rendering errors; inspect renderer.log and configure Poppler language data or use --renderer pdfium')
    images = sorted(output.glob('page-*.png'), key=lambda p: int(p.stem.rsplit('-', 1)[1]))
    need(len(images) == count, 'Rendered page count mismatch')
    for image in images:
        need(image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'), 'Invalid rendered PNG')
    report = {'renderer': args.renderer, 'pdf': {'path': args.pdf, 'sha256': sha(pdf)}, 'dpi': args.dpi,
              'pages': [{'number': i + 1, 'path': str(p.relative_to(root)), 'sha256': sha(p)} for i, p in enumerate(images)]}
    write(report_path, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor')
    comp = sub.add_parser('compile')
    comp.add_argument('--project', default='.')
    comp.add_argument('--manifest', default='paper-manifest.json')
    comp.add_argument('--engine', choices=['auto', 'xelatex', 'pdflatex', 'tectonic'], default='auto')
    comp.add_argument('--build', default='build/latex-1')
    comp.add_argument('--output', default='report.pdf')
    comp.add_argument('--report', default='compile-report.json')
    comp.add_argument('--timeout', type=float, default=180)
    rend = sub.add_parser('render')
    rend.add_argument('--project', default='.')
    rend.add_argument('--pdf', default='report.pdf')
    rend.add_argument('--output-dir', default='render/pages')
    rend.add_argument('--report', default='render-manifest.json')
    rend.add_argument('--renderer', choices=['poppler', 'pdfium'], default='poppler')
    rend.add_argument('--dpi', type=int, default=110)
    rend.add_argument('--max-pages', type=int, default=100)
    rend.add_argument('--timeout', type=float, default=180)
    args = parser.parse_args()
    try:
        if args.command == 'doctor':
            result = {'tools': {t: shutil.which(t) for t in ['xelatex', 'pdflatex', 'tectonic', 'bibtex', 'biber', 'pdfinfo', 'pdftoppm']},
                      'python': {p: bool(importlib.util.find_spec(p)) for p in ['numpy', 'matplotlib', 'scipy', 'pypdfium2']}}
        else:
            root = Path(args.project).resolve()
            result = compile_paper(args, root) if args.command == 'compile' else render(args, root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return int(result.get('status') == 'failed')
    except (ValueError, OSError, KeyError, TypeError, ImportError, subprocess.SubprocessError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

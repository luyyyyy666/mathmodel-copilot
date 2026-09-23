"""Structural and provenance gates for publication artifacts; not a quality oracle."""
import hashlib
import json


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def publication_files(root, state, stage, executions, local):
    if state['format'] == 1:
        return []
    paths = []
    produced = {r['path']: r['sha256'] for e in executions for r in e['outputs']}
    supplied = {r['path']: r['sha256'] for e in executions for r in e['inputs']}

    def load(name):
        value = json.loads(local(root, name).read_text(encoding='utf-8'))
        need(isinstance(value, dict), f'{name} must be an object')
        paths.append(name)
        return value

    def file(name, expected=None):
        p = local(root, name)
        need(p.is_file() and p.stat().st_size, f'Missing/empty publication file: {name}')
        if expected:
            need(sha(p) == expected, f'Publication hash mismatch: {name}')
        paths.append(name)
        return p

    def generated(name):
        need(name in produced, f'No recorded execution produced {name}')
        return file(name, produced[name])

    if stage == 'figures':
        manifest = load('figure-manifest.json')
        figures = manifest.get('figures')
        need(isinstance(figures, list), 'figures must be a list')
        if not figures:
            need(isinstance(manifest.get('reason'), str) and manifest['reason'].strip(), 'No figures requires a reason')
        reviews = load('figure-review.json').get('figures', []) if figures else []
        need(isinstance(reviews, list) and len(reviews) == len(figures), 'Review must cover every figure')
        seen = set()
        for fig in figures:
            need(isinstance(fig, dict), 'Figure entry must be an object')
            for key in ['id', 'question', 'caption', 'script']:
                need(isinstance(fig.get(key), str) and fig[key].strip(), f'Figure needs {key}')
            need(fig['id'] not in seen, 'Duplicate figure id')
            seen.add(fig['id'])
            need(isinstance(fig.get('data'), list) and fig['data'], 'Figure needs actual data sources')
            need(fig['script'] in supplied, 'Figure script must be a recorded execution input')
            for name in [fig['script'], *fig['data']]:
                evidence = {**supplied, **produced}
                need(name in evidence, f'Figure source not recorded in execution: {name}')
                file(name, evidence[name])
            outputs = fig.get('outputs')
            need(isinstance(outputs, list) and outputs, 'Figure outputs are required')
            need(any(p.endswith('.png') for p in outputs), 'Figure needs a PNG preview')
            need(any(p.endswith(('.pdf', '.svg')) for p in outputs), 'Figure needs a vector export')
            for name in outputs:
                p = generated(name)
                header = p.read_bytes()[:8]
                if name.endswith('.png'):
                    need(header == b'\x89PNG\r\n\x1a\n', f'Not PNG: {name}')
                if name.endswith('.pdf'):
                    need(header.startswith(b'%PDF-'), f'Not PDF: {name}')
            matches = [r for r in reviews if r.get('id') == fig['id']]
            need(len(matches) == 1, 'Missing or duplicate figure review')
            review = matches[0]
            need(isinstance(review, dict) and review.get('status') == 'pass'
                 and isinstance(review.get('observations'), str) and review['observations'].strip(),
                 'Figure needs actual visual-review observations')
            need(review.get('sha256') == sha(file(next(p for p in outputs if p.endswith('.png')))),
                 'Figure review must bind the current PNG hash')
    elif stage == 'report' and state['require_pdf']:
        manifest = load('paper-manifest.json')
        need(isinstance(manifest.get('files'), list) and manifest['files'], 'Paper needs source files')
        need(manifest.get('main') in manifest['files'] and manifest['main'].endswith('.tex'), 'Paper needs a .tex entry point')
        need(manifest.get('bibliography') in ['none', 'bibtex', 'biber'], 'Choose bibliography backend explicitly')
        for name in manifest['files']:
            file(name)
        need(isinstance(manifest.get('claims'), list) and manifest['claims'], 'Paper needs result-to-claim references')
        for claim in manifest['claims']:
            need(isinstance(claim.get('text'), str) and claim['text'].strip(), 'Claim needs text')
            file(claim['evidence'])
        # All intended figure exports must travel with the paper sources.
        figures = load('figure-manifest.json')['figures']
        for fig in figures:
            need(any(p in manifest['files'] for p in fig['outputs'] if p.endswith(('.pdf', '.svg'))),
                 f'Paper manifest omits figure {fig["id"]}')
    elif stage == 'compile':
        generated('compile-report.json')
        generated('report.pdf')
        report = load('compile-report.json')
        need(report.get('status') == 'succeeded', 'Compilation did not succeed')
        need(not report.get('errors'), 'Unresolved compilation errors')
        file('report.pdf', report['pdf']['sha256'])
        need(report['pdf']['path'] == 'report.pdf', 'Unexpected compiled PDF path')
        need(report.get('commands') and all(c['returncode'] == 0 for c in report['commands']), 'Compilation command failed')
        frozen = {r['path']: r['sha256'] for r in state['stages']['report']['files']}
        paper = load('paper-manifest.json')
        sources = {r['path']: r['sha256'] for r in report['sources']}
        need(set(sources) == set(paper['files']), 'Compiled sources differ from paper manifest')
        for name, value in sources.items():
            need(frozen.get(name) == value, f'Compiled source was not the frozen paper: {name}')
            file(name, value)
        for command in report['commands']:
            file(command['log'])
        file(report['latex_log'])
    elif stage == 'inspect':
        generated('render-manifest.json')
        manifest = load('render-manifest.json')
        file('report.pdf', manifest['pdf']['sha256'])
        need(manifest['pdf']['path'] == 'report.pdf', 'Unexpected render source')
        pages = manifest.get('pages')
        need(isinstance(pages, list) and pages, 'No rendered pages')
        need([p['number'] for p in pages] == list(range(1, len(pages) + 1)), 'Incomplete page numbering')
        review = load('render-review.json')
        need(review.get('status') == 'pass' and review.get('pdf_sha256') == manifest['pdf']['sha256'], 'Review is failed or stale')
        reviews = review.get('pages', [])
        need(len(reviews) == len(pages), 'Review must cover every page')
        for page, item in zip(pages, reviews):
            file(page['path'], page['sha256'])
            need(item.get('number') == page['number'] and item.get('sha256') == page['sha256']
                 and item.get('status') == 'pass' and isinstance(item.get('observations'), str)
                 and item['observations'].strip(), 'Missing, failed or stale page review')
    return list(dict.fromkeys(paths))

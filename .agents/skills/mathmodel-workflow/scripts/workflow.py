#!/usr/bin/env python3
"""Local, single-writer modeling workflow. Python 3.10+, macOS/Linux; no model API."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import uuid
from publication_contract import publication_files

BUNDLE = Path(__file__).resolve().parents[1]
STAGES = json.loads((BUNDLE / 'assets/stages.json').read_text())
LEGACY_STAGES = json.loads((BUNDLE / 'assets/stages-v1.json').read_text())
IDS = [s['id'] for s in STAGES]


def stages(state):
    definitions = LEGACY_STAGES if state['format'] == 1 else STAGES
    return [s for s in definitions if not s.get('pdf_only') or state['require_pdf']]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.pending-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(value, out, ensure_ascii=False, indent=2, allow_nan=False)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def local(root, name, internal=False):
    p = Path(name)
    require(not p.is_absolute() and '..' not in p.parts, f'Expected relative project path: {name}')
    require(p.parts and (internal or p.parts[0] not in {'.workflow', '.agents', '.git', 'delivery-manifest.json'}),
            f'Reserved path: {name}')
    candidate = root / p
    require(candidate.resolve().is_relative_to(root), f'Path escapes project: {name}')
    # Reject aliases even when the symlink currently points inside the workspace.
    require(not any(x.is_symlink() for x in [candidate, *candidate.parents] if x != root.parent),
            f'Symlink path is not supported: {name}')
    return candidate


def snapshot(root, name, internal=False, nonempty=True):
    p = local(root, name, internal)
    require(p.is_file(), f'Missing file: {name}')
    require(not nonempty or p.stat().st_size > 0, f'Empty artifact: {name}')
    sha = digest(p)
    blob = root / '.workflow/blobs' / sha
    blob.parent.mkdir(parents=True, exist_ok=True)
    if not blob.exists():
        shutil.copyfile(p, blob)
    require(digest(blob) == sha, f'Corrupt snapshot: {sha}')
    return {'path': str(Path(name)), 'sha256': sha, 'bytes': p.stat().st_size}


def references(state):
    refs = list(state['inputs'])
    for record in state['stages'].values():
        refs.extend(record.get('files', []))
    return refs


def problems(root, state):
    issues = []
    for ref in references(state):
        try:
            p = local(root, ref['path'], internal=True)
            require(p.is_file() and digest(p) == ref['sha256'], 'missing or changed')
            blob = root / '.workflow/blobs' / ref['sha256']
            require(blob.is_file() and digest(blob) == ref['sha256'], 'snapshot missing or changed')
        except (ValueError, OSError) as error:
            issues.append(f"{ref['path']}: {error}")
    return sorted(set(issues))


def pending(root):
    return [r for p in sorted((root / '.workflow/executions').glob('*.json'))
            if (r := read(p))['status'] == 'running']


def current(state):
    return next((s for s in stages(state) if s['id'] not in state['stages']), None)


def ready(root, state, stage):
    require(not problems(root, state), 'Inputs/artifacts changed; use check, then reopen or refresh-inputs.')
    require(not pending(root), 'Unresolved execution; inspect it and use abandon only after it has stopped.')
    step = current(state)
    require(step is not None and step['id'] == stage, f'Next stage is {step["id"] if step else "none"}.')
    return step


@contextmanager
def locked(root):
    local(root, '.workflow/state.json', internal=True)
    require((root / '.workflow/state.json').is_file(), 'Not initialized; run init first.')
    with local(root, '.workflow/lock', internal=True).open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('Another workflow command is active.') from exc
        yield read(root / '.workflow/state.json')


def save(root, state):
    atomic(root / '.workflow/state.json', state)


def init(args, root):
    sources = [Path(args.problem).resolve(), *[Path(p).resolve() for p in args.data]]
    require(all(p.is_file() for p in sources), 'Problem/data must be existing files.')
    require(args.max_runs > 0, '--max-runs must be positive.')
    require(not root.exists() or not any(root.iterdir()), 'init requires a new or empty project directory.')
    root.mkdir(parents=True, exist_ok=True)
    bundle_target = root / '.agents/skills/mathmodel-workflow'
    shutil.copytree(BUNDLE, bundle_target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    (root / 'inputs').mkdir()
    (root / '.workflow/executions').mkdir(parents=True)
    refs = []
    for i, p in enumerate(sources):
        name = f'inputs/{i:02d}-{p.name}'
        shutil.copyfile(p, root / name)
        refs.append(snapshot(root, name))
    (root / 'AGENTS.md').write_text(
        '# 建模任务工作区\n\n读取 `.agents/skills/mathmodel-workflow/SKILL.md`。\n'
        '先运行 `python3 .agents/skills/mathmodel-workflow/scripts/workflow.py status --project .`\n'
        '和 `next --project .`，从当前阶段继续。实际执行计算、验证和交付，不只写计划。\n'
        '阶段登记不是用户验收；沿用用户授权与宿主权限，不修改原始 inputs 或状态文件绕过检查。\n', encoding='utf-8')
    state = {'format': args.workflow_version, 'title': args.title or sources[0].stem, 'created_at': now(),
             'kind': args.kind, 'require_pdf': args.pdf, 'max_runs': args.max_runs,
             'revision': 1, 'inputs': refs, 'stages': {}, 'history': []}
    save(root, state)
    return {'project': str(root), 'next': 'understand', 'skill': str(bundle_target / 'SKILL.md')}


def run(args, root, state):
    ready(root, state, args.stage)
    argv = args.argv[1:] if args.argv[:1] == ['--'] else args.argv
    require(argv, 'Supply a command after --.')
    require(math.isfinite(args.timeout) and args.timeout > 0, 'Timeout must be finite and positive.')
    require(len(list((root / '.workflow/executions').glob('*.json'))) < state['max_runs'],
            'Execution budget exhausted. Deliver partial results; do not erase history.')
    inputs = [snapshot(root, p) for p in args.input]
    for p in args.output:
        target = local(root, p)
        require(not target.exists(), f'Output already exists; use a new output path: {p}')
        target.parent.mkdir(parents=True, exist_ok=True)
    ident = uuid.uuid4().hex
    prefix = f'.workflow/executions/{ident}'
    receipt_path = root / (prefix + '.json')
    receipt = {'id': ident, 'stage': args.stage, 'revision': state['revision'], 'argv': argv,
               'started_at': now(), 'status': 'running', 'inputs': inputs,
               'outputs': [], 'pid': None, 'timeout_seconds': args.timeout,
               'environment': {'platform': sys.platform, 'python': sys.version.split()[0]},
               'logs': [prefix + '.stdout', prefix + '.stderr']}
    atomic(receipt_path, receipt)
    proc = None
    failure = None
    try:
        with (root / receipt['logs'][0]).open('wb') as stdout, (root / receipt['logs'][1]).open('wb') as stderr:
            proc = subprocess.Popen(argv, cwd=root, stdout=stdout, stderr=stderr, start_new_session=True)
            receipt['pid'] = proc.pid
            atomic(receipt_path, receipt)
            try:
                code = proc.wait(timeout=args.timeout)
            except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                failure = 'timeout' if isinstance(exc, subprocess.TimeoutExpired) else 'interrupted'
                code = proc.returncode
        receipt['exit_code'] = code
        require(code == 0 and not failure, failure or f'Process exited {code}')
        for ref in inputs:
            require(digest(local(root, ref['path'])) == ref['sha256'], f'Input changed during execution: {ref["path"]}')
        receipt['outputs'] = [snapshot(root, p) for p in args.output]
        receipt['status'] = 'succeeded'
    except (OSError, ValueError) as exc:
        receipt['status'] = 'failed'
        receipt['error'] = str(exc)
    receipt['ended_at'] = now()
    atomic(receipt_path, receipt)
    return receipt


def verification(root, state):
    report = read(local(root, 'verification.json'))
    require(isinstance(report, dict), 'Verification report must be an object.')
    require(report.get('verdict') == 'pass', 'Verification verdict is not pass.')
    checks = report.get('checks')
    require(isinstance(checks, list) and checks, 'Verification needs substantive checks.')
    require(isinstance(report.get('limitations'), list), 'Verification must declare limitations (possibly []).')
    evidence = []
    for check in checks:
        require(isinstance(check, dict) and check.get('status') == 'pass'
                and isinstance(check.get('name'), str) and check['name'].strip()
                and isinstance(check.get('detail'), str) and check['detail'].strip(),
                'Each check needs name, pass status and substantive detail.')
        paths = check.get('evidence')
        require(isinstance(paths, list) and paths and all(isinstance(p, str) for p in paths),
                'Each check needs evidence file paths.')
        evidence.extend(paths)
    return evidence


def complete(args, root, state):
    step = ready(root, state, args.stage)
    paths = list(dict.fromkeys([*step['outputs'], *args.artifact]))
    if args.stage == 'verify':
        paths.extend(verification(root, state))
    if state['format'] == 1 and args.stage == 'report' and state['require_pdf']:
        paths.extend(['report.pdf', 'render-review.md'])
        require(local(root, 'report.pdf').read_bytes().startswith(b'%PDF-'), 'report.pdf is not a PDF.')
    files = [snapshot(root, p) for p in dict.fromkeys(paths)]
    executions = []
    for ident in args.execution:
        require(len(ident) == 32 and all(c in '0123456789abcdef' for c in ident), 'Invalid execution ID.')
        name = f'.workflow/executions/{ident}.json'
        receipt = read(root / name)
        require(receipt['status'] == 'succeeded' and receipt['stage'] == args.stage
                and receipt['revision'] == state['revision'], 'Execution is failed, stale or belongs to another stage.')
        for ref in receipt['inputs'] + receipt['outputs']:
            require(digest(local(root, ref['path'])) == ref['sha256'], f'Execution file changed: {ref["path"]}')
        files.extend(receipt['inputs'] + receipt['outputs'])
        files.append(snapshot(root, name, internal=True))
        files.extend(snapshot(root, p, internal=True, nonempty=False) for p in receipt['logs'])
        executions.append(receipt)
    require(not step['execution'] or (state['kind'] == 'theory' and args.stage not in ['compile', 'inspect']) or executions,
            'This stage needs a successful, recorded execution (--execution ID).')
    if args.stage == 'verify' and state['kind'] != 'theory':
        require(any(any(r['path'] == 'verification.json' for r in e['outputs']) for e in executions),
                'verification.json must be produced by a recorded verification command.')
    extra = publication_files(root, state, args.stage, executions, local)
    files.extend(snapshot(root, p) for p in extra)
    state['stages'][args.stage] = {'status': 'done', 'at': now(), 'revision': state['revision'],
                                 'files': files, 'executions': args.execution, 'note': args.note}
    save(root, state)
    return {'stage': args.stage, 'status': 'done', 'meaning': 'evidence recorded, not human acceptance'}


def reopen(root, state, stage, reason):
    require(reason.strip(), 'A reason is required.')
    require(not pending(root), 'Resolve the interrupted execution first.')
    active_ids = [s['id'] for s in stages(state)]
    require(stage in active_ids, 'Stage is not enabled for this project.')
    index = active_ids.index(stage)
    old = {s: state['stages'].pop(s) for s in active_ids[index:] if s in state['stages']}
    state['history'].append({'revision': state['revision'], 'at': now(), 'reason': reason,
                             'from': stage, 'stages': old, 'inputs': state['inputs']})
    state['revision'] += 1
    save(root, state)
    return {'next': stage, 'invalidated': list(old), 'revision': state['revision']}


def export(root, state, destination):
    require(current(state) is None, 'Required stages are not finished.')
    require(not problems(root, state) and not pending(root), 'Integrity or unresolved-execution failure.')
    dest = Path(destination).resolve()
    require(not dest.is_relative_to(root) and not root.is_relative_to(dest), 'Export to a separate directory.')
    require(not dest.exists(), 'Export destination already exists.')
    refs = {r['path']: r for r in references(state)}
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='.delivery-', dir=dest.parent))
    try:
        for name, ref in refs.items():
            out = temp / name
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / '.workflow/blobs' / ref['sha256'], out)
        atomic(temp / 'delivery-manifest.json', {'format': 1, 'title': state['title'], 'revision': state['revision'],
               'created_at': now(), 'files': list(refs.values()), 'human_acceptance': 'not_recorded'})
        os.rename(temp, dest)
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    return {'delivery': str(dest), 'files': len(refs), 'human_acceptance': 'not_recorded'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    for name in ['init', 'status', 'next', 'check', 'run', 'complete', 'skip', 'reopen', 'refresh-inputs', 'export', 'abandon', 'upgrade']:
        sub = subs.add_parser(name)
        sub.add_argument('--project', required=True)
        if name == 'init':
            sub.add_argument('--problem', required=True)
            sub.add_argument('--data', action='append', default=[])
            sub.add_argument('--title')
            sub.add_argument('--kind', choices=['general', 'optimization', 'prediction', 'simulation', 'evaluation', 'theory'], default='general')
            sub.add_argument('--max-runs', type=int, default=20)
            sub.add_argument('--pdf', action='store_true')
            sub.add_argument('--workflow-version', type=int, choices=[1, 2], default=2)
        if name in ['run', 'complete', 'skip', 'reopen']:
            sub.add_argument('--stage', choices=IDS, required=True)
        if name in ['skip', 'reopen', 'refresh-inputs', 'abandon', 'upgrade']:
            sub.add_argument('--reason', required=True)
        if name == 'run':
            sub.add_argument('--input', action='append', required=True)
            sub.add_argument('--output', action='append', required=True)
            sub.add_argument('--timeout', type=float, default=300)
            sub.add_argument('argv', nargs=argparse.REMAINDER)
        if name == 'complete':
            sub.add_argument('--artifact', action='append', default=[])
            sub.add_argument('--execution', action='append', default=[])
            sub.add_argument('--note', default='')
        if name == 'export':
            sub.add_argument('--destination', required=True)
        if name == 'abandon':
            sub.add_argument('--execution', required=True)
    args = parser.parse_args()
    root = Path(args.project).resolve()
    try:
        if args.command == 'init':
            result = init(args, root)
        else:
            with locked(root) as state:
                require(state['format'] in [1, 2], 'Unsupported workflow format.')
                if args.command in ['status', 'next', 'check']:
                    issues = problems(root, state)
                    active = pending(root)
                    step = current(state)
                    result = {'title': state['title'], 'revision': state['revision'], 'kind': state['kind'],
                              'next': step, 'stages': {k: v['status'] for k, v in state['stages'].items()},
                              'integrity_issues': issues, 'unresolved_executions': active,
                              'runs_remaining': state['max_runs'] - len(list((root / '.workflow/executions').glob('*.json'))),
                              'complete': step is None and not issues and not active,
                              'reference_base': str(BUNDLE / 'references')}
                    if args.command == 'check':
                        require(not issues and not active, json.dumps(result, ensure_ascii=False))
                elif args.command == 'run':
                    result = run(args, root, state)
                elif args.command == 'complete':
                    result = complete(args, root, state)
                elif args.command == 'skip':
                    step = ready(root, state, args.stage)
                    require(step.get('optional') and args.reason.strip(), 'Only optional stages may be skipped, with a reason.')
                    state['stages'][args.stage] = {'status': 'skipped', 'reason': args.reason, 'files': [], 'at': now()}
                    save(root, state)
                    result = state['stages'][args.stage]
                elif args.command == 'reopen':
                    result = reopen(root, state, args.stage, args.reason)
                elif args.command == 'refresh-inputs':
                    new = [snapshot(root, r['path']) for r in state['inputs']]
                    result = reopen(root, state, 'understand', args.reason)
                    state['inputs'] = new
                    save(root, state)
                elif args.command == 'upgrade':
                    require(state['format'] == 1, 'Project already uses workflow v2.')
                    require(not problems(root, state), 'Repair drift before upgrading.')
                    result = reopen(root, state, 'report', args.reason)
                    target = root / '.agents/skills/mathmodel-workflow'
                    if BUNDLE != target.resolve():
                        staging = root / '.workflow' / ('bundle-' + uuid.uuid4().hex)
                        shutil.copytree(BUNDLE, staging, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                        if target.exists():
                            target.rename(root / '.workflow' / ('previous-bundle-' + uuid.uuid4().hex))
                        staging.rename(target)
                    state['format'] = 2
                    save(root, state)
                    result.update(format=2, next=current(state))
                elif args.command == 'export':
                    result = export(root, state, args.destination)
                else:
                    require(args.reason.strip(), 'A reason is required.')
                    matches = [r for r in pending(root) if r['id'] == args.execution]
                    require(len(matches) == 1, 'No matching unresolved execution.')
                    receipt = matches[0]
                    if receipt['pid']:
                        try:
                            os.kill(receipt['pid'], 0)
                        except ProcessLookupError:
                            pass
                        else:
                            raise ValueError('Recorded PID still exists; inspect/stop it before abandoning.')
                    receipt.update(status='failed', error='Operator abandoned: ' + args.reason, ended_at=now())
                    atomic(root / f'.workflow/executions/{receipt["id"]}.json', receipt)
                    result = receipt
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.command == 'run' and result['status'] != 'succeeded' else 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

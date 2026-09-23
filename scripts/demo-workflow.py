#!/usr/bin/env python3
"""Run the full local workflow with a deterministic facility-location fixture, without an LLM."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.agents/skills/mathmodel-workflow/scripts/workflow.py'
FIXTURE = ROOT / 'examples/facility-location'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--destination', required=True)
    parser.add_argument('--publication', action='store_true', help='Prepare a v2 PDF project through scientific verification; continue with demo-publication.py')
    args = parser.parse_args()
    project = Path(args.project).resolve()

    def command(*argv):
        result = subprocess.run([sys.executable, str(WF), *argv, '--project', str(project)],
                                text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError(result.stderr or result.stdout)
        return json.loads(result.stdout)

    def execute(stage, inputs, outputs, argv):
        prefix = [sys.executable, str(WF), 'run', '--project', str(project), '--stage', stage]
        for p in inputs:
            prefix += ['--input', p]
        for p in outputs:
            prefix += ['--output', p]
        result = subprocess.run([*prefix, '--', *argv], text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError(result.stderr or result.stdout)
        return json.loads(result.stdout)['id']

    command('init', *(['--pdf'] if args.publication else []), '--workflow-version', '2' if args.publication else '1', '--problem', str(FIXTURE / 'problem.md'), '--data', str(FIXTURE / 'data.json'), '--kind', 'optimization')
    for name in ['solve.py', 'verify.py', 'report.py', 'reproduce.py']:
        shutil.copyfile(FIXTURE / name, project / name)
    (project / 'problem.md').write_text((FIXTURE / 'problem.md').read_text() + '\n基线采用贪心；精确候选枚举所有二站点组合，验证独立枚举需求分配。\n')
    command('complete', '--stage', 'understand')
    data = json.loads((project / 'inputs/01-data.json').read_text())
    assert len(data['weights']) == len(data['distances']) == 4
    assert all(len(row) == 4 and min(row) >= 0 for row in data['distances'])
    (project / 'data-report.md').write_text('合成数据：4 个需求、4 个候选、p=2；权重为正，距离非负且矩阵维度一致。未清洗或检索外部材料。\n')
    command('complete', '--stage', 'data')
    for stage, method, output, note in [('baseline', 'greedy', 'baseline', 'baseline.md'), ('improve', 'exact', 'candidate', 'model.md')]:
        (project / note).write_text(f'方法：{method}。目标是加权最近距离，选择恰好 2 站点，无容量约束。\n精确候选用有限枚举，和贪心基线使用同一输入；比较容差 1e-9。\n')
        execution = execute(stage, ['solve.py', 'inputs/01-data.json'], [f'results/{output}.json'],
                            [sys.executable, 'solve.py', 'inputs/01-data.json', f'results/{output}.json', '--method', method])
        command('complete', '--stage', stage, '--execution', execution)
    execution = execute('verify', ['verify.py', 'inputs/01-data.json', 'results/baseline.json', 'results/candidate.json'],
                        ['verification.json', 'results/checks.json'],
                        [sys.executable, 'verify.py', 'inputs/01-data.json', 'results/baseline.json', 'results/candidate.json', 'verification.json', 'results/checks.json'])
    command('complete', '--stage', 'verify', '--execution', execution)
    if args.publication:
        print(json.dumps({'project': str(project), 'next': 'figures', 'model_calls': 0}))
        return
    execution = execute('report', ['report.py', 'inputs/01-data.json', 'results/baseline.json', 'results/candidate.json', 'verification.json'],
                        ['report.md', 'figures.svg', 'environment.txt'], [sys.executable, 'report.py'])
    command('complete', '--stage', 'report', '--execution', execution)
    (project / 'REPRODUCE.md').write_text('''# 复现

Python 3.10+，仅标准库。输入是 inputs/01-data.json；无随机数。
在本交付目录执行：

```sh
python3 solve.py inputs/01-data.json replay-baseline.json --method greedy
python3 solve.py inputs/01-data.json replay-candidate.json --method exact
python3 verify.py inputs/01-data.json replay-baseline.json replay-candidate.json replay-verification.json replay-checks.json
python3 reproduce.py replay.json
```

预期目标值与 results/ 下记录一致；验证容差 1e-9。reproduce.py 在全新临时目录求解并比较，不复用旧计算输出。
图表与报告可通过 python3 report.py 重建（会覆盖报告文件，请先复制交付目录）。
这是合成工程样例；未测真实模型调用、参数敏感性和 PDF 交付。
''', encoding='utf-8')
    execution = execute('deliver', ['reproduce.py', 'solve.py', 'verify.py', 'inputs/01-data.json', 'results/baseline.json', 'results/candidate.json'],
                        ['results/reproduction.json'], [sys.executable, 'reproduce.py', 'results/reproduction.json'])
    command('complete', '--stage', 'deliver', '--execution', execution)
    command('check')
    result = command('export', '--destination', str(Path(args.destination).resolve()))
    result['model_calls'] = 0
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

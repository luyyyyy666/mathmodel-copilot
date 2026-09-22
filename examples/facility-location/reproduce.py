"""Fresh-directory replay, compare with registered results without importing their values as outputs."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as temp:
    work = Path(temp)
    for method in ['greedy', 'exact']:
        subprocess.run([sys.executable, str(root / 'solve.py'), str(root / 'inputs/01-data.json'),
                        str(work / f'{method}.json'), '--method', method], cwd=work, check=True)
    subprocess.run([sys.executable, str(root / 'verify.py'), str(root / 'inputs/01-data.json'),
                    str(work / 'greedy.json'), str(work / 'exact.json'), 'verification.json', 'checks.json'], cwd=work, check=True)
    comparisons = {}
    for method, original in [('greedy', 'results/baseline.json'), ('exact', 'results/candidate.json')]:
        fresh = json.loads((work / f'{method}.json').read_text())
        expected = json.loads((root / original).read_text())
        comparisons[method] = fresh == expected
    if not all(comparisons.values()):
        raise ValueError('Fresh replay differs from registered results')
    Path(sys.argv[1]).write_text(json.dumps({'fresh_directory': True, 'matches': comparisons,
                                             'verification': json.loads((work / 'verification.json').read_text())}, indent=2) + '\n')

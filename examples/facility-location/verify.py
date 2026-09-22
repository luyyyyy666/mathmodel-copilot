"""Recalculate feasibility/objective, using assignment enumeration as a separate oracle."""
from itertools import product
import json
from pathlib import Path
import sys


def verify(data, baseline, candidate):
    n, p = len(data['sites']), data['p']
    weights, distances = data['weights'], data['distances']
    # Independent enumeration over demand assignments, not facility subsets.
    optimum = min(sum(weights[i] * distances[i][j] for i, j in enumerate(assignment))
                  for assignment in product(range(n), repeat=len(weights))
                  if len(set(assignment)) <= p)
    checks = []
    for name, result in [('baseline', baseline), ('candidate', candidate)]:
        selected = result['selected']
        valid = len(set(selected)) == p and all(isinstance(j, int) and 0 <= j < n for j in selected)
        if not valid:
            checks.append({'name': name + '-feasibility', 'status': 'fail', 'detail': 'Invalid selected sites'})
            continue
        objective = sum(weights[i] * min(distances[i][j] for j in selected) for i in range(len(weights)))
        assignments = result['assignments']
        feasible = len(assignments) == len(weights) and all(j in selected for j in assignments)
        assigned_cost = sum(weights[i] * distances[i][j] for i, j in enumerate(assignments)) if feasible else None
        passed = feasible and abs(objective - result['objective']) <= 1e-9 and abs(assigned_cost - objective) <= 1e-9
        checks.append({'name': name + '-recompute', 'status': 'pass' if passed else 'fail',
                       'detail': f'Recomputed objective {objective}; assignment cost {assigned_cost}; tolerance 1e-9'})
    checks.append({'name': 'independent-optimum',
                   'status': 'pass' if abs(candidate['objective'] - optimum) <= 1e-9 else 'fail',
                   'detail': f'Assignment enumeration optimum {optimum}; tolerance 1e-9'})
    checks.append({'name': 'baseline-comparison',
                   'status': 'pass' if candidate['objective'] <= baseline['objective'] + 1e-9 else 'fail',
                   'detail': f'Baseline {baseline["objective"]}; candidate {candidate["objective"]}'})
    return checks


if __name__ == '__main__':
    data, baseline, candidate, output, evidence = sys.argv[1:]
    checks = verify(*(json.loads(Path(p).read_text()) for p in [data, baseline, candidate]))
    Path(evidence).parent.mkdir(parents=True, exist_ok=True)
    Path(evidence).write_text(json.dumps(checks, indent=2) + '\n')
    report = {'verdict': 'pass' if all(c['status'] == 'pass' for c in checks) else 'fail',
              'checks': [dict(c, evidence=[evidence]) for c in checks],
              'limitations': ['Synthetic tiny fixture; no capacity constraints or real-world uncertainty validation.']}
    Path(output).write_text(json.dumps(report, indent=2) + '\n')
    if report['verdict'] != 'pass':
        sys.exit(1)

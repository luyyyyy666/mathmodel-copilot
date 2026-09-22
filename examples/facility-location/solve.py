"""Greedy baseline or exhaustive optimum for the small synthetic fixture."""
import argparse
from itertools import combinations
import json
from pathlib import Path


def solve(data, method):
    weights, distances, p = data['weights'], data['distances'], data['p']
    n = len(data['sites'])
    if not (1 <= p <= n and len(weights) == len(distances)
            and all(len(row) == n and min(row) >= 0 for row in distances)
            and all(w > 0 for w in weights)):
        raise ValueError('Invalid fixture dimensions, weights or p')

    def cost(selected):
        return sum(w * min(row[j] for j in selected) for w, row in zip(weights, distances))

    if method == 'greedy':
        selected = []
        for _ in range(p):
            selected.append(min((j for j in range(n) if j not in selected),
                                key=lambda j: (cost(selected + [j]), j)))
    else:
        selected = min(combinations(range(n), p), key=lambda s: (cost(s), s))
    return {'method': method, 'selected': sorted(selected), 'objective': cost(selected),
            'assignments': [min(selected, key=lambda j: (row[j], j)) for row in distances],
            'units': 'weighted km', 'synthetic': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('data')
    parser.add_argument('output')
    parser.add_argument('--method', choices=['greedy', 'exact'], required=True)
    args = parser.parse_args()
    result = solve(json.loads(Path(args.data).read_text()), args.method)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')

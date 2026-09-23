"""Real calculations on synthetic fixture; no preview data substituted for results."""
import hashlib
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib_templates import save_figure
from solve import solve
from verify import verify

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False,
                     'axes.spines.right': False, 'pdf.fonttype': 42})
data = json.loads(Path('inputs/01-data.json').read_text())
base = json.loads(Path('results/baseline.json').read_text())
exact = json.loads(Path('results/candidate.json').read_text())
Path('figures').mkdir(exist_ok=True)
# Distances are a supplied matrix; do not invent geographic coordinates.
fig, ax = plt.subplots(figsize=(6.5, 3.6), layout='constrained')
values = np.asarray(data['distances'])
img = ax.imshow(values, cmap='cividis', vmin=0, vmax=float(values.max()))
for i in range(values.shape[0]):
    for j in range(values.shape[1]):
        ax.text(j, i, str(values[i, j]), ha='center', va='center', color='white' if values[i, j] < 4 else 'black')
ax.set(xticks=range(4), xticklabels=data['sites'], yticks=range(4), yticklabels=['D1', 'D2', 'D3', 'D4'],
       xlabel='Candidate facility', ylabel='Demand point')
fig.colorbar(img, ax=ax, label='Distance (km)')
save_figure(fig, 'figures/distances');plt.close(fig)
fig, ax = plt.subplots(figsize=(6.5, 2.7), layout='constrained')
ax.barh(['Greedy baseline', 'Exact enumeration'], [base['objective'], exact['objective']], color=['#7A7A7A', '#0072B2'])
ax.set(xlabel='Weighted service distance (weighted km)', xlim=(0, 20))
for i, val in enumerate([base['objective'], exact['objective']]):
    ax.text(val + .3, i, str(val), va='center')
save_figure(fig, 'figures/comparison');plt.close(fig)
# Explicit scenario analysis, not Sobol indices or confidence bands.
scenario = []
scenario_checks = []
for p in range(1, 5):
    solved = solve(dict(data, p=p), 'exact')
    checks = verify(dict(data, p=p), solve(dict(data, p=p), 'greedy'), solved)
    if not all(c['status'] == 'pass' for c in checks):
        raise ValueError('Scenario verification failed')
    scenario_checks.append({'p': p, 'checks': checks})
    scenario.append({'p': p, 'objective': solved['objective'], 'selected': solved['selected']})
Path('results/sensitivity.json').write_text(json.dumps(scenario, indent=2) + '\n')
Path('results/sensitivity-checks.json').write_text(json.dumps(scenario_checks, indent=2) + '\n')
fig, ax = plt.subplots(figsize=(6.5, 3), layout='constrained')
ax.plot([r['p'] for r in scenario], [r['objective'] for r in scenario], 'o-', color='#0072B2')
ax.set(xlabel='Number of facilities p', ylabel='Optimal weighted distance', xticks=range(1, 5), ylim=(0, 32))
save_figure(fig, 'figures/sensitivity');plt.close(fig)
entries = [
 ('distances', 'How do supplied service distances differ?', 'Given synthetic demand-to-facility distances in km; no geographic coordinates are inferred.', ['inputs/01-data.json']),
 ('comparison', 'Does exact search improve on the baseline?', 'Both methods achieve 16 weighted km on the same input; extra computation provides an optimality check, not an improvement.', ['results/baseline.json','results/candidate.json']),
 ('sensitivity', 'How does the optimum change with facility count?', 'Exact optima for p=1,2,3,4 with fixed distances and weights. This is discrete scenario analysis, not a statistical confidence interval.', ['results/sensitivity.json'])]
manifest={'figures':[{'id':i,'question':q,'caption':c,'script':'figures.py','data':d,
                     'outputs':[f'figures/{i}.png',f'figures/{i}.pdf']} for i,q,c,d in entries]}
Path('figure-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
Path('environment.txt').write_text(f'Python {sys.version}\nNumPy {np.__version__}\nMatplotlib {matplotlib.__version__}\nSynthetic deterministic fixture; no random seed needed.\n')

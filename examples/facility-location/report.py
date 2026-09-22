"""Deterministic fixture report; not a model quality evaluation."""
import json
from pathlib import Path
import platform
import sys

base = json.loads(Path('results/baseline.json').read_text())
result = json.loads(Path('results/candidate.json').read_text())
data = json.loads(Path('inputs/01-data.json').read_text())
scale = 360 / max(base['objective'], result['objective'])
svg = '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="180" viewBox="0 0 600 180"><rect width="600" height="180" fill="white"/>'
for row, (label, value) in enumerate([('Greedy', base['objective']), ('Exact', result['objective'])]):
    y = 45 + row * 65
    svg += f'<text x="15" y="{y + 22}" font-family="sans-serif">{label}</text><rect x="95" y="{y}" width="{value * scale}" height="30" fill="#286c8e"/><text x="{105 + value * scale}" y="{y + 22}" font-family="sans-serif">{value}</text>'
svg += '<text x="95" y="165" font-family="sans-serif">Weighted distance (km); lower is better</text></svg>'
Path('figures.svg').write_text(svg)
Path('environment.txt').write_text(f'Python {sys.version}\nPlatform {platform.platform()}\nPython standard library only.\n')
sites = ', '.join(data['sites'][i] for i in result['selected'])
Path('report.md').write_text(f'''# 合成选址题报告

选择 {sites}，最小加权服务距离为 **{result['objective']}**（加权 km）。
贪心基线为 {base['objective']}。精确解由小规模站点组合枚举得到，并经独立需求分配枚举核对。
数值来源：results/baseline.json、results/candidate.json 的 objective 字段；核验见 verification.json。

## 模型与假设

选择恰好 p=2 个站点，各需求分配到已选站点中的最近点。
最小化 sum_i w_i min_j d_ij，j 属于已选集合。权重和距离固定，无容量及服务半径约束。
该离散枚举在本有限候选集上取得全局最优；不推广到未列入的数据或约束。

## 结果与验证

![目标值对照](figures.svg)

verify.py 独立重算可行性、分配距离、目标值并核对穷举最优值，容差为 1e-9。
本例用于工程链路验收，未开展参数扰动或真实城市验证，不声称方案在需求变化后稳定。

## 局限与复现

输入是合成数据，不是实际调查；未考虑容量、拥堵、建设成本和需求不确定性。
没有外部文献引用。完整复现命令见 REPRODUCE.md，环境见 environment.txt。
本报告由确定性脚本生成，用于检查工作流，不代表大模型数学能力评估。
''', encoding='utf-8')

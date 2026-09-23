"""Build a Chinese fixture paper from checked results, including real figure references."""
import json
from pathlib import Path
import shutil

base = json.loads(Path('results/baseline.json').read_text())
result = json.loads(Path('results/candidate.json').read_text())
scenario = json.loads(Path('results/sensitivity.json').read_text())
figures = json.loads(Path('figure-manifest.json').read_text())['figures']
paper = Path('paper');(paper/'sections').mkdir(parents=True, exist_ok=True)
shutil.copyfile('main-zh.tex', paper/'main.tex')
text = (paper/'main.tex').read_text().replace('数学建模报告','有限候选站点下的设施选址建模与验证')
(paper/'main.tex').write_text(text)
(paper/'sections/abstract.tex').write_text(r'''\begin{abstract}
本文针对四个需求点与四个候选站点的合成选址问题，在无容量限制、距离与需求权重固定的前提下，
选择两个站点以最小化加权服务距离。先构造逐步添加站点的贪心基线，再对有限站点组合进行精确枚举，
并通过独立的需求分配枚举核验最优性。两种方法均得到站点 A、C，加权服务距离为 16。
进一步对站点数量进行离散情景分析，展示服务距离随资源投入的变化。
该实验验证工作流的数据、计算、图表、论文与复现链路，不代表真实城市规划结论。
\end{abstract}
\noindent\textbf{关键词：}设施选址；离散优化；独立验证；可复现计算
''',encoding='utf-8')
rows = '\n'.join(f"{r['p']} & {r['objective']} & {','.join('ABCD'[j] for j in r['selected'])} \\\\" for r in scenario)
body = r'''\section{问题与数据}
给定需求点集合 $I=\{1,2,3,4\}$ 和候选站点集合 $J=\{A,B,C,D\}$，选择恰好 $p=2$ 个站点。
需求权重为 $w=(2,1,3,2)$。距离矩阵单位为 km，数据为工程验收构造的合成算例，未使用实地调查数据。
目标是为每个需求点提供服务，并最小化加权距离。本文不从距离矩阵臆造地理坐标。

\begin{figure}[htbp]\centering
\includegraphics[width=.78\linewidth]{distances.pdf}
\caption{合成需求点与候选站点距离矩阵。横轴为候选站点，纵轴为需求点，格内数值及色条单位均为 km。}
\label{fig:distances}\end{figure}

\section{假设、符号与模型}
距离固定且非负，权重为正；站点无容量限制，各需求可被任意已选站点服务；不计建设费用及拥堵。
这些假设限定了结果的适用范围。令 $y_j\in\{0,1\}$ 表示站点是否启用，$x_{ij}\in\{0,1\}$ 表示需求分配。
\begin{align}
\min_{x,y}\quad &\sum_{i\in I}\sum_{j\in J} w_i d_{ij}x_{ij},\\
\text{s.t.}\quad &\sum_{j\in J}x_{ij}=1,\quad i\in I,\\
&x_{ij}\leq y_j,\quad i\in I,j\in J,\\
&\sum_{j\in J}y_j=p.
\end{align}
对固定的已选站点集合，每个需求分配至最近站点即可。因此可直接在大小为 $p$ 的站点子集上评价目标。

\section{基线、候选与求解}
贪心基线从空集合开始，每次加入使当前总加权距离最小的站点，直至达到 $p$。
精确候选枚举全部 $\binom{4}{2}=6$ 个站点组合，并以最近站点分配计算目标。
并列时按站点索引确定可复现的输出，不把唯一输出误解为唯一最优解。
本题规模适合穷举；规模扩大时组合数量增长，不能将此实现作为大型选址求解器。

\section{结果与独立核验}
基线与精确枚举均选择 A、C，对应目标值为 16，单位为加权 km。
手工核对得到 $2\times1+1\times3+3\times1+2\times4=16$。
因此本算例没有观察到目标改善；精确枚举增加的是最优性依据，而非更低的目标值。
独立验证脚本枚举需求分配而非站点子集，检查使用站点数、目标值及服务分配，比较容差为 $10^{-9}$。
所有检查的原始记录保存在 \texttt{verification.json} 和 \texttt{results/checks.json}。

\begin{figure}[htbp]\centering
\includegraphics[width=.83\linewidth]{comparison.pdf}
\caption{同一数据上的基线与精确解对照，两者均为 16。条形从零起，不用截断坐标夸大差异。}
\label{fig:comparison}\end{figure}

\section{站点数量的情景分析}
保持权重和距离不变，将 $p$ 分别设为 1、2、3、4，并重新求解和独立验证。
该分析反映站点数量变化下的离散情景，既不是 Sobol 全局敏感性指标，也不是统计置信区间。
\begin{table}[htbp]\centering
\caption{不同站点数量下的精确最优结果。}\label{tab:scenarios}
\begin{tabular}{ccc}\toprule
站点数 $p$ & 最优加权距离 & 选中站点\\\midrule
''' + rows + r'''
\bottomrule\end{tabular}\end{table}

\begin{figure}[htbp]\centering
\includegraphics[width=.8\linewidth]{sensitivity.pdf}
\caption{站点数量与最优加权距离。每个标记均来自一次实际精确求解；连线仅帮助阅读离散情景。}
\label{fig:sensitivity}\end{figure}

\section{局限、结论与复现}
本题缺少建设成本、容量与最大服务半径等约束，也未研究需求权重和距离的不确定性。
因此不能由加权距离随站点数下降推导出“建越多越好”的现实政策建议。
在题设的有限候选集与固定参数下，选择 A、C 为一个全局最优方案；结论仅限本算例。
数据、代码、环境、验证结果与图表源文件一并交付。运行说明见 \texttt{REPRODUCE.md}。
本稿由确定性示例脚本生成，不是大模型自主解题效果评估；没有使用或虚构外部文献。
'''
(paper/'sections/body.tex').write_text(body,encoding='utf-8')
# Subset the supplied licensed TrueType font to this paper; preserve Unicode mappings.
# Re-run after every text change. Do not reuse this subset for unrelated papers.
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools import subset
font_dir=paper/'fonts'
font_dir.mkdir(exist_ok=True)
text=''.join(p.read_text(encoding='utf-8') for p in paper.rglob('*.tex'))+'摘要关键词图表0123456789'
for weight,name in [(400,'CJK-Regular.ttf'),(700,'CJK-Bold.ttf')]:
    font=TTFont('chinese-font.ttf')
    if 'fvar' in font:
        font=instantiateVariableFont(font,{'wght':weight},inplace=True)
    options=subset.Options()
    options.name_IDs=['*']
    sub=subset.Subsetter(options=options)
    sub.populate(text=text)
    sub.subset(font)
    font.save(font_dir/name)
    font.close()
shutil.copyfile('font-license.txt',font_dir/'OFL.txt')
manifest={'unicode_probes':['给定需求点集合','距离固定且非负','本题缺少建设成本'],'main':'paper/main.tex','bibliography':'none','files':['paper/main.tex','paper/sections/abstract.tex','paper/sections/body.tex','paper/fonts/CJK-Regular.ttf','paper/fonts/CJK-Bold.ttf','paper/fonts/OFL.txt',
          *[p for f in figures for p in f['outputs'] if p.endswith('.pdf')]],
          'claims':[{'text':'A,C 目标为16，基线与精确解一致','evidence':'results/candidate.json'},
                    {'text':'所有离散情景均独立核对','evidence':'results/sensitivity-checks.json'}]}
Path('paper-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
Path('report.md').write_text('# 选址建模论文\n\n完整可编辑论文：paper/main.tex。编译输出：report.pdf。\n\n基线与精确解均选择 A、C，目标值为16。\n数据为合成算例；图表见 figures/，敏感性结果见 results/sensitivity.json。\n本例未验证大模型自主解题能力。\n',encoding='utf-8')

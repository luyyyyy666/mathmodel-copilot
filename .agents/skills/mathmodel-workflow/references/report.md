# 报告与复现交付

## report

先读取 [分章写作指导](paper-writing.md)，沿用小问编号和验证阶段的 [结论审查](claims.md)。赛事论文同时读取 [格式配置](contest.md)。用 [论文计划模板](../assets/worksheets/paper-plan.md) 在 report.md 中安排章节、结论和图表；不要按实验发生的时间顺序堆砌正文。

从通过验证的结果组织 report.md：问题回应、假设与符号、模型、结果、检验、局限、引用。
先写结论与依据，再解释方法；每个关键数字标明结果文件/字段，每个引用能定位原始来源。
用真实数据绘图，将绘图脚本、源数据、图像登记为产物；不要以生成图片代替统计图。

格式 2 的 PDF 任务在 report 阶段写 LaTeX 源文件与 paper-manifest.json，后续独立进入 compile、inspect。示例：

```json
{"main":"paper/main.tex","bibliography":"none","files":["paper/main.tex","paper/body.tex","figures/result.pdf"],"claims":[{"text":"关键结论与数值","evidence":"results/result.json"}]}
```

files 列出编译所需全部文件；每张登记图至少包含一个矢量版本。每项关键结论绑定真实结果证据。外部文献核验后加入 .bib，不编造引用；没有外部引用时明确 bibliography=none。报告中解释模型假设、方程、求解、验证、敏感性和局限。编译过程见 [LaTeX 协议](latex.md)。
格式 1 旧项目仍在 report 阶段登记 report.pdf 与 render-review.md；使用 upgrade 后改走新版阶段。
不要求 PDF 时交付 Markdown；仍需完成 figures 阶段或说明无图理由。

## deliver

赛事交付逐项对照已核验的格式配置，记录实际页数及其计算范围、身份信息、必需附件和 AI 使用说明。未核实的规则不能写成已合规。普通报告按用户约定交付，不套用另一项比赛的要求。

写 REPRODUCE.md：环境及版本、依赖、数据来源、逐条执行命令、随机种子、预期结果/容差、局限。
在新目录重新运行计算，避免读取旧结果冒充复算；将本次复算日志/结果作为 deliver 的执行输出。
理论题复查推导与引用，记录复核范围，无须伪造数值实验。
complete deliver 时登记所有交付需要但之前未登记的文件。
运行 check 后 export；导出只包含登记过的产物及证据，未登记文件不会自动打包。

最终告知用户：回答、主要结果、报告和复现包路径、验证范围与剩余不确定性。
本地工作流的 done 表示阶段证据登记完成，不是人的科学验收；不要代替用户作批准记录。

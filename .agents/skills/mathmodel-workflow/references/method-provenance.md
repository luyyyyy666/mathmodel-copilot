# 方法参考与取舍

本轮领域指导和 worksheets 由本项目重新编写，参考以下固定版本的思想，未复制其技能正文或竞赛 LaTeX 模板。不对参考应用的实际解题效果作运行验证声明。

## math-model

仓库：https://github.com/luyyyyy666/math-model
核对版本：638d289989e3adc124606b2fb1dd7cd4bc8fb081

- `skills/comp-prob-analysis/SKILL.md`：题目层级、逐问输入输出、依赖及图表预规划。
- `skills/comp-modeling/SKILL.md`：选择理由、假设、推导和实现要点。
- `skills/comp-code/SKILL.md`：逐问实现与结果交接。
- `skills/result-to-claim/SKILL.md`：结果支持范围、证据缺口、补实验或收窄表述。
- `skills/comp-paper-zh/SKILL.md`、`skills/comp-paper-en/SKILL.md` 及其模板：分章写作、摘要、图表嵌入和不同论文组织方式。

不采用：预设自提方法在合成数据中获胜；变量/图表/字数配额；把最大页数当最小篇幅；按文件大小判断内容完成；强制复杂图型；R² 只能在 [0,1] 的错误检查；固定耗时即重写；将另一模型的意见视为正确性保证。图表计划可随证据调整，题目内部要求必须覆盖，赛事要求逐条核实。

## Mathodology

仓库：https://github.com/sweetcornna/mathodology
核对版本：0cfcd93f1dc8ddd26f928f7ec88a09ae3a1d70f6

参考 `.claude/agents/` 中 problem-analyst、modeler、coder、critic、paper-editor 的职责指导，以及 `.claude/skills/mathodology-award-gates/SKILL.md`：有用基线、可识别性、反证、区分不确定性、代码与论文一致、证据约束结论、避免虚构奖项评分。

既有图表代码和图型卡片的实际复用仍按 `assets/figures/provenance.json` 及 LICENSE 记录。本轮不增加外部工具或模型依赖。

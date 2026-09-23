# 直接用 Codex 跑数学建模工作流

这是一套已可执行的本地工作流，不需要启动 backend 或 frontend。
Codex/其他具备文件和命令工具的大模型执行领域任务；Python 脚本管理阶段、真实执行记录和交付。
需要 Python 3.10+、macOS/Linux。启动本仓库源码 Codex 还需要 Node.js、已登记构建产物和可用的模型认证。

## 最快体验：不调用模型的完整样例

在仓库根目录运行（目录已存在时会拒绝覆盖）：

```sh
python3 scripts/demo-workflow.py \
  --project modeling-projects/facility-demo \
  --destination modeling-projects/facility-delivery
```

样例实际计算合成选址题，经过基线、精确候选、独立核验、SVG 图表、Markdown 报告、全新目录复算和导出。
输出位于 `modeling-projects/facility-delivery/`，读 report.md 和 REPRODUCE.md。
该脚本证明工具和文件链路可运行，不证明大模型能自主解出所有题型。

## 用真实题目启动

```sh
python3 .agents/skills/mathmodel-workflow/scripts/workflow.py init \
  --project /absolute/my-modeling-task \
  --problem /absolute/problem.pdf \
  --data /absolute/data.csv \
  --kind optimization --max-runs 30 --pdf
```

没有数据附件时省略 --data；不要求 PDF 时省略 --pdf。支持 general、optimization、prediction、simulation、evaluation、theory。
初始化复制完整工作流包和输入原件，可独立移动；不更改全局模型设置或安装外部技能。

然后选一种入口：

1. 在 Codex 桌面/CLI 打开题目目录，发送下面的启动提示；AGENTS.md 已引用本地 Skill。
2. 使用本仓库的源码构建内核启动（继承当前认证和模型配置）：

```sh
node scripts/start-modeling.mjs --project /absolute/my-modeling-task --check
node scripts/start-modeling.mjs --project /absolute/my-modeling-task
```

--check 只核验目录与登记二进制摘要，不调用模型，也不验证账号认证。
默认登记文件为仓库 .runtime/runtime.json，可用 --registration 指定其他源码构建登记。
没有登记产物时先按根 README 构建，不回退到 PATH 中另一个 codex。
启动采用 workspace-write/on-request，保留真实工具审批，不绕过沙箱。
新会话可能要求用户信任题目目录；若宿主没有自动发现 Skill，显式读取下面的路径即可。

启动提示：

> 读取 AGENTS.md 和 .agents/skills/mathmodel-workflow/SKILL.md，从 status/next 显示的阶段继续完成这道题。
> 真实执行基线、必要的改进、验证、报告与复现交付。按我的已有授权继续，遇到缺失关键输入或无法解决的工具问题时明确报告。
> 不覆盖旧结果，不把本地完成登记当作人工科学验收。

## 继续、检查和返工

在题目目录运行：

```sh
python3 .agents/skills/mathmodel-workflow/scripts/workflow.py status --project .
python3 .agents/skills/mathmodel-workflow/scripts/workflow.py next --project .
python3 .agents/skills/mathmodel-workflow/scripts/workflow.py check --project .
python3 .agents/skills/mathmodel-workflow/scripts/workflow.py reopen --project . --stage baseline --reason "修正模型假设"
```

阶段顺序为 understand → data → baseline → improve → verify → report → deliver。
只有 improve 可带理由跳过；理论题允许用证明证据代替强制数值计算。
重新开会话也从这些文件继续，不需要旧对话历史。完整命令见
[操作协议](../.agents/skills/mathmodel-workflow/references/operations.md)。

## 本轮已实现与仍未实现

已实现：可发现的项目 Skill、可迁移题目目录、阶段推进、执行次数预算、进程超时、输入/产物摘要与内容快照、
执行日志、结构化验证报告检查、跳过/返工、完整性检查、交付导出、源码 Codex 启动适配和自动化测试。

未实现：backend 自动接线、通用 DAG 调度、多 Agent 并行、硬内存/GPU/Token 配额、完整依赖环境封装、自动判断科学正确性。
原始输入更新会让全部阶段失效；当前仅支持更新已登记输入路径。联网和非命令工具由宿主执行并由 Agent 保存来源。
命令记录不是安全沙箱；脚本不能防止同权限进程修改文件。强制杀死脚本后的未知执行需先人工核对，不自动重跑。

本地 done 是记录状态，和现有 backend v2 的人工 Review 分开；本轮没有改变后端契约。
统一设计中的可靠服务编排、前端工作台及完整产物服务仍是后续工作。

## 解题与论文指导

工作流包现在按阶段提供更细的领域指导：逐问拆解与依赖、模型到代码的实现对应、结论证据审查、图表计划和分章写作。
`assets/worksheets/` 中的分析、模型、结论审查和论文计划模板可合并进现有阶段产物；简单题无需额外维护四份文件。
小问编号贯穿模型、实现、验证和正文，内部子要求也要逐项覆盖。结果只能部分支持原主张时，应补实验或收窄表述；原题必答项仍有缺口时不能宣称完整解题。

赛事论文从 `assets/worksheets/contest-profile.json` 记录年份、组别及有来源的实际规则，按 `references/contest.md` 选择中文数模、MCM/ICM、统计研究或普通报告的内容骨架。
配置由宿主 Agent 应用到现有通用 LaTeX 模板；目前不是自动排版生成器或赛事合规校验器。页数、摘要页、匿名范围与 AI 说明等均按本题规则核验，不继承固定赛事年份的要求。

这些内容是宿主解题指导，不增加 `complete` 的科学判定能力，不改变格式 1/2 的状态协议。
新建题目时 `init` 会完整复制新版指导。已有题目目录保存的是初始化时的包版本，不会自动更新；可从新包读取这些参考材料继续，必要时将模板作为新的阶段产物登记，不覆盖既有快照。
来源和未采用的规则见包内 `references/method-provenance.md`。这次更新未进行真实比赛题的效果评测。

## 验证

```sh
python3 -m unittest discover -s tests/workflow -v
npm test
```

自动化测试包括完整样例与导出后独立复算、失败/超时、输入和结果漂移、路径越界、预算、返工、
旧执行拒绝、未决执行恢复、可选阶段、理论任务、PDF 必需性，以及 Codex 启动参数与二进制篡改拒绝。
本轮没有运行外部模型任务；需要真实题目和已配置模型后另行评估 Agent 效果。

Codex 接入依据：仓库现有 .agents 技能发现代码、源码 CLI --help，以及
[官方 Skills 文档](https://developers.openai.com/codex/skills)和
[官方 AGENTS.md 文档](https://developers.openai.com/codex/guides/agents-md)（2026-09-22 查阅）。

## 图表与 LaTeX 集成（工作流格式 2）

新任务默认依次执行：理解、数据、基线、改进、验证、科学图表、论文、LaTeX 编译（--pdf）、逐页检查（--pdf）、复现交付。Mathodology 的 20 类绘图模板/样式卡片保留 MIT 许可和固定来源版本；math-model 的论文分章、编译诊断与渲染检查流程以独立模板和工具适配器实现。无须先启动全栈 Agent；宿主大模型按 Skill 调工具即可继续。

```sh
python3 -m venv .runtime/publication-env
.runtime/publication-env/bin/pip install -r .agents/skills/mathmodel-workflow/assets/figures/requirements.txt
.runtime/publication-env/bin/python .agents/skills/mathmodel-workflow/scripts/publication.py doctor
.runtime/publication-env/bin/python scripts/demo-publication.py --project modeling-projects/publication-demo --destination modeling-projects/publication-delivery
```

另外配置 XeLaTeX（中文建议）或 Tectonic，以及 Poppler。演示会在 figure-review.json 和 render-review.json 缺失时暂停，宿主查看真实图片后按 Skill references/figures.md、latex.md 写入逐图/逐页观察与哈希，再运行同一命令继续。不会自动填通过审查。该确定性示例不调用模型 API，展示合成选址数据的模型、求解、独立检验、三张图和中文论文，不代表任意比赛题的效果。旧 demo-workflow.py 保留格式 1 基础回归；加 --publication 可初始化新版 PDF 示例到绘图阶段。

旧项目可用更新后的 workflow.py upgrade --project PATH --reason REASON 显式升级；已完成 report/deliver 将失效并保留历史。新增协议是完整性和溯源检查，不是自动证明数学、排版或引用正确。

部分 Poppler 分发缺少中文 Adobe-GB1 映射。工具会拒绝这类漏字渲染；可在同一隔离环境安装 `pypdfium2 Pillow`，演示命令加 `--renderer pdfium`，helper render 同样支持此参数。

### 中文正文兼容性

中文模板现在要求项目内 TrueType 常规/粗体字体，随源文件声明并嵌入 PDF。示例在论文阶段需要 `--font /path/to/NotoSansSC.ttf --font-license /path/to/OFL.txt`，从 [Google Fonts 的 Noto Sans SC](https://github.com/google/fonts/tree/main/ofl/notosanssc) 获取授权源字体与 OFL 许可。FontTools 从该源字体按本稿正文生成两个子集，字体、许可和来源文件一同交付。无需安装系统字体。使用 assets/figures/requirements.txt 安装示例依赖。

示例 manifest 的 unicode_probes 检查中文正文可提取、字体已嵌入、Unicode 映射存在；仍必须实际渲染检查。仅换成 PDFium 能显示，不能证明原预览器的正文漏字已经修好。

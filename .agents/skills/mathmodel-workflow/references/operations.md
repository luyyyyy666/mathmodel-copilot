# 本地操作协议

Python 3.10+，macOS/Linux，无第三方 Python 依赖。脚本不会启动模型，命令由当前 Agent 决定并执行。
WF 代表 scripts/workflow.py 的绝对路径；PROJECT 为题目目录的绝对路径。下列命令使用占位符，替换后再执行。

```sh
python3 WF init --project PROJECT --problem /absolute/problem.pdf --data /absolute/data.csv --kind optimization
python3 WF status --project PROJECT
python3 WF next --project PROJECT
```

init 只接受新目录或空目录，复制原件与完整 Skill，使题目可以迁移到别的机器或会话。
默认总命令次数上限 20；初始化用 --max-runs N 调整；需要 PDF 时加 --pdf。
已有成果放入新工作区后逐阶段检查并登记，不补造历史计算；必要阶段重新实际执行。

`next` 输出阶段、建议产物名与 reference；读取 reference_base 下的对应文件。
输出文件默认放在题目根目录，也可用子目录保存代码/数据/图表。必需说明文件名见 next.outputs。

```sh
python3 WF complete --project PROJECT --stage understand
python3 WF complete --project PROJECT --stage data --artifact scripts/clean.py --artifact data/clean.csv
python3 WF run --project PROJECT --stage baseline --input scripts/solve.py --input data/clean.csv --output results/baseline.json -- python3 scripts/solve.py
python3 WF complete --project PROJECT --stage baseline --execution RETURNED_ID --artifact scripts/solve.py
python3 WF skip --project PROJECT --stage improve --reason "基线已满足目标，且增加复杂度没有证据支持"
```

run 的参数放在 `--` 前，后面是实际 argv，不经过 shell 拼接。命令在 PROJECT 中执行。
--input 和 --output 可重复，使用相对路径；记录所有影响结果的脚本、数据和参数文件。
输出路径必须尚不存在，避免旧结果冒充本次产物；已有输出应保留并改用新名称。
若验证阶段重新生成固定名称 verification.json，先 reopen verify 并将旧文件移至历史目录再执行。
默认单次超时 300 秒，--timeout 可调整；超时终止当前命令进程组并记录失败。
环境仅自动记录平台与宿主 Python 版本；实际求解器、依赖和运行环境另存 environment.txt，并登记。

complete 自动登记阶段必需文件、执行输入输出和日志；额外交付文件用 --artifact 添加。
理论题 --kind theory 不强求执行记录，但同样需要推导、验证证据与复现/复核说明。
完整性检查不会检查 Markdown 语义、证明正确性或 PDF 排版，相关检查由 Agent 实际完成。

```sh
python3 WF check --project PROJECT
python3 WF reopen --project PROJECT --stage baseline --reason "修正目标函数单位"
python3 WF refresh-inputs --project PROJECT --reason "用户替换了原始数据"
python3 WF export --project PROJECT --destination /absolute/new-delivery-directory
```

reopen 清除本阶段及其下游的当前完成状态，旧记录放入 history，内容快照仍保留。
已完成阶段的文件应避免原地修改；若修改，check 会报漂移，需 reopen 对应生产阶段。
refresh-inputs 只刷新已有原件路径；新增题目/附件时另建项目或把附件清单变化纳入新的原件版本。
原件仅接受有明确原因的用户更新，不能为绕过失败自动改输入。
export 必须全部阶段结束且摘要一致，只打包已登记文件，拒绝覆盖已有目录。

持久记录在 .workflow/state.json、.workflow/executions/、.workflow/blobs/。
此脚本为单写入者本地工具，锁在进程退出后释放，不是隔离沙箱，也不能抵御同权限进程篡改。
脚本自身被强制终止可能留下 running 执行记录；不会自动重跑。
先检查日志和真实进程（含子进程）是否停止，再执行：

```sh
python3 WF abandon --project PROJECT --execution ID --reason "已核对并停止旧执行，保留失败记录"
```

PID 仍存在时会拒绝 abandon；PID 消失也不证明所有外部副作用已结束，操作者仍需核对。
确认后的新 run 消耗一次预算，旧记录不删除。禁止手工把 unknown/running 改成 succeeded。

若通过现有 backend 调用，先在该 Project 的 workspace 准备此包和输入，再将 Skill 路径与任务目标写入 Run prompt。
本轮未自动接线 backend；普通 Codex 在题目目录打开即可读取 AGENTS.md，或显式要求读取 SKILL.md。
本地 done 不改变现有后端 awaiting_review/completed 的含义。

# Math Model 调度参考核对

日期：2026-09-22。范围：本地 math-model 恢复仓库的静态阅读。

## 覆盖范围与证据限制

上一版工作流方案参考了 README 与 recovery/evidence/workflow_templates.json，主要覆盖阶段模板、输出文件和人工检查点，未完整审查调度实现。
本次补查 workflow_engine.py、其字节码及 run_workflow.dis.txt 的关键分支，以及 workflows 路由、state_store 和 schema 的相关定义。
反编译的 run_workflow / run_single_step 等函数只有 pass，不能作为完整源代码理解；关键行为需由 .bytecode.txt 交叉确认。
本次未执行原软件，未验证所有异常路径、并发行为、底层 claude_runner 进程清理和重试边界；不宣称完整运行验证或全量调度审计。

下述行号指参考仓库文本证据文件中的行号，便于复查，不是新仓库文件。

## 机制对照

| 机制 | 原仓库证据/观察 | 新项目取舍 |
| --- | --- | --- |
| 模板展开 | TEMPLATES / workflow_templates.json：阶段绑定 Skill、输出和检查点 | 采用版本化模板，展开为 Step；保留每个小问的任务依赖 |
| 顺序推进 | run_workflow.dis.txt:240 起，按 step_order 查询并迭代，跳过 completed | 首版串行；只有验收通过且输入未失效才可跳过。模块自称 DAG，但该主循环不是通用依赖图调度器 |
| 可选步骤 | run_workflow.dis.txt:320 附近，skip_improvement_loop 分支将步骤记作 completed | 显式记录 skipped 与理由，不冒充实际执行完成；只有模板标为可选的步骤可跳过 |
| 上下文交接 | workflow_engine.py 的 _build_context_summary / _generate_claude_md；后者注入上传材料、用户要求和反馈 | 保留上下文组装能力，冻结输入版本；用户要求、提取材料与模型推断分开记录 |
| 人工检查点 | workflow_engine.py.bytecode.txt:1495 的 wait_checkpoint 使用内存 Event，超时返回 action=approve、auto=True | 检查点决策持久化并绑定步骤/产物版本；超时保持 waiting_user，绝不自动批准 |
| 检查点反馈 | run_workflow.dis.txt:3450–3672 一带，等待回应、读取反馈并写 checkpoint_feedback.md | 区分“接受并补充后续要求”和“要求当前步骤返工”；后者新建修订并使下游失效 |
| 暂停 | routers/workflows.py.bytecode.txt:1355 的 pause 包含 runner cancel 与 task cancel；主循环处理 CancelledError | 明确分为阶段边界暂停和立即中断；立即中断后依真实终态判定能否恢复 |
| 断点与恢复 | run_workflow 跳过 completed；字节码:3954 起有“后续已完成则把当前 running 标成 completed”的恢复分支 | 用登记的执行历史及产物验证核对；不能由后续状态反推当前已成功 |
| 重试与看门狗 | run_workflow.dis.txt:1534–1943 一带有空工具调用、无活跃超时、文件无变化及非零退出的重试分支 | 分类记录失败，限定次数和预算；文件无变化只作诊断信号，长时间求解可能完全正常；未知副作用先恢复核对 |
| 部分论文恢复 | run_workflow.dis.txt:2183 起含 .tex 部分产物恢复，后续有占位符章节续写分支 | 建立独立、有预算的修复任务；保留失败版本，重验实际编译、正文完整性与数值一致性 |
| 单步重跑 | 存在 run_single_step 独立入口，workflow_engine.py.bytecode.txt:8279 起 | 保留用户入口；新建 Attempt 或 Step 修订，并明确下游失效，不能覆盖历史验收 |
| 状态修复与存储 | state_store 的初始化恢复列表、SQLite 更新重试；路由 _heartbeat_check 对数据库与内存任务进行检查 | 数据库是调度事实来源；持久派发意图与唯一关联防重复；缺少内存任务不等于从未执行 |
| 事件通知 | _notify、step_skipped、step_completed、checkpoint_hit 等事件 | 状态与事件同事务落库，按游标读取；界面连接不承担调度事实来源 |

上述为关键行为抽查和设计映射，不表示列出的每个函数已经逐条指令审计。

## 对 v1 设计的补充

1. 增加可选步骤状态 skipped：必须记录理由与模板允许性，必需步骤不得靠 skip 解锁最终交付。
2. GateDecision 明确 accept / request_changes / stop；accept 附带的后续意见与 request_changes 的当前返工分开处理。
3. 增加 progress 信号：协议活动、进程状态、实验进度与文件变化分开记录。文件静默不单独构成科学计算失败。
4. 重试策略区分本地派发前失败、已确认结束的失败、未知副作用和科学验证失败。首版仍保留人工触发 retry，不承诺自动重试已实现。
5. 修复论文/补全文件属于有输入版本的新任务；保留失败证据，修复后重新验证，而非仅凭文件存在将步骤判为完成。
6. 暂停、恢复、单步重做、重启恢复需有对应故障用例；特别测试等待检查点时重启，以及取消与正常完成同时发生。

## 尚待进一步审查

- claude_runner 对无活跃判断、返回码、进程树终止与输出回调的完整实现。
- run_single_step 与主循环在上下文、检查点、重试和输出检查上的差异。
- 路由重复 start/resume、心跳、启动自动恢复之间的竞争，以及等待检查点的重启行为。
- 全部产物检测、续写与成功判定分支，包括旧文件误判为本次产物的可能性。

在这些项目完成前，准确结论是“已参考模板并补查主要调度机制”，不是“所有工作流调度逻辑都已参考和验证”。

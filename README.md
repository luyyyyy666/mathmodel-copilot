# Mathmodel Agent · 数学建模

以 Codex 开源执行内核为基底的数学建模 Agent。当前包含完整 Codex 源码和
后端 后端核心，前后端放在同一仓库，前端当前为工程基座。

## 先用工作流跑题

已提供不依赖前后端服务的 [Codex 数模工作流](docs/workflow-quickstart.md)：
题目理解 → 数据 → 基线 → 按需改进 → 验证 → 报告 → 复现交付。
入口为 `.agents/skills/mathmodel-workflow/SKILL.md`，脚本保存真实执行与阶段产物。

```sh
python3 scripts/demo-workflow.py --project modeling-projects/facility-demo --destination modeling-projects/facility-delivery
```

这条命令运行不调用模型的完整选址样例。真实题目的初始化、Codex 源码内核启动和恢复操作见快速开始。
当前本地工作流已实现；后端跨任务自动编排与业务界面仍待实现。

领域指导已补充逐问分析与实现对应、结论证据审查、分章写作和赛事格式配置；具体用法见快速开始中的“解题与论文指导”。配置和科学判断由宿主 Agent 执行，脚本完成状态不代表比赛合规或数学正确性。

## 仓库结构

- `codex-runtime/`：完整 Codex 源码快照，可在本仓库分支中修改、构建。
- `frontend/`：前端工程基座，待实现工作台界面。
- `backend/`：业务契约、SQLite 状态库、任务执行、审批、取消与恢复核对。
- `scripts/build-runtime.mjs`：从本仓库源码构建运行时并登记产物。
- `scripts/check-runtime.mjs`：真实运行时与本地模拟模型的端到端联调。
- `runtime-source.json`：Codex 上游来源、原始提交与源码树标识。
- `validation.json`：归并后的测试及源码运行时联调记录。

所有源码都随本仓库提交，无需访问其他私有仓库，也不依赖本机绝对源码路径。
Codex 源码的原许可证、NOTICE 和贡献规范保留在其目录中。

## 安装与构建

需要 Node.js 24.19.0 或更新版本、Rust 1.95.0，以及平台对应的原生构建工具。
macOS 首次构建使用 Xcode Command Line Tools、CMake 和 pkg-config。

```sh
npm --prefix backend ci --ignore-scripts
node scripts/build-runtime.mjs
node scripts/check-runtime.mjs
```

构建前先提交源码变更。构建使用 Cargo.lock，首次需要下载依赖；默认开发构建。
产物登记和协议 Schema 写入忽略跟踪的 `.runtime/`。CLI 显示版本 0.0.0 是
源码开发版本标记，精确来源以仓库提交、源码树与二进制 SHA-256 为准。

编译器路径默认使用当前用户的 Rustup 安装，也可通过 CARGO 指定。
可以通过 CARGO_TARGET_DIR 指定外部编译缓存；构建脚本会登记对应实际产物路径。

## 后端验证

```sh
npm --prefix backend test
cd backend
npm run verify
```

归并后 65 项后端测试、12 项前端基座测试和两个模块的治理检查均通过。
使用相同源码树对应的既有构建产物完成了新后端的端到端验证。端到端测试使用本地模拟模型，
覆盖任务执行、结果人工验收、历史会话重读和取消，不消费外部模型额度。
它不代表真实数模题的效果评估。

## 启动服务

在仓库外创建服务配置，填入自己的绝对路径：

```json
{
  "data_directory": "/absolute/private/mathmodel-agent-data",
  "runtime_registration": "/absolute/mathmodel-agent/.runtime/runtime.json",
  "codex_home": "/absolute/private/mathmodel-agent-codex",
  "port": 18089
}
```

在终端通过 MATHMODEL_AGENT_TOKEN 环境变量提供长度至少 32 字符的随机访问令牌，然后运行：

```sh
npm --prefix backend start -- --config /absolute/service.json
```

所有 API 使用 Bearer 认证，只监听本机。真实模型任务需要在配置指定的 CODEX_HOME
中完成 Codex 登录或供应方设置；认证材料、运行数据和编译产物不进入 Git。
接口和状态机见 `backend/contracts/v2/README.md`。

## 开发边界

main 保存可复现的项目快照，codex/math-agent-runtime 是执行内核开发分支。
原 Codex 基线记录在 runtime-source.json；它是上游来源，而非本仓库历史中的祖先提交。
修改内核时遵循 codex-runtime/AGENTS.md，并对修改涉及的模块做验证。

当前每个运行对应一个有验收标准的建模任务，支持持久化尝试、审批和人工结果验收。
尚未实现任务 DAG、实验与产物版本体系、多 Agent 调度以及前端界面。

## 工作流设计

[统一数学建模工作流](docs/design/unified-modeling-workflow.md) 是后续设计主入口，整合既有总结、
math-model 调度参考与 mathodology 方法，定义模块交接、工具调用、科学验证、返工恢复和落地次序。
当前为设计提案，尚未实现跨任务自动编排。

[原工作流 v1](docs/design/math-workflow-v1.md) 与 [调度参考核对](docs/design/math-model-scheduler-review.md)
保留作为设计依据；早期参考仓库评估与完整性复评已归档到 `docs/design/references/`。

# Mathmodel Agent

## 数学建模任务

当用户给出建模题、数据，或要求继续建模/验证/论文交付时，读取
`.agents/skills/mathmodel-workflow/SKILL.md`，按该工作流实际执行。
这不适用于普通仓库开发、代码审查或解释设计文档的请求。

在独立题目目录中工作，保留原件、真实计算、验证和交付证据。通过工作流脚本读取状态，
不要把聊天中“做过了”当作完成依据。用户已授权的常规步骤持续执行；缺少关键输入、
需要真实权限、工具失败无法继续或预算耗尽时，明确报告阻塞。

## 仓库开发

- `backend/` 是现有 v2 单任务服务；`frontend/` 是工程基座。
- `.agents/skills/mathmodel-workflow/` 是可独立复制的领域工作流包，不依赖后端服务。
- 脚本不调用模型 API、不更改认证或沙箱配置，不取代 v2 人工 Review。
- 修改本地工作流后运行 `python3 -m unittest discover -s tests/workflow -v`。
- 后端/前端变更遵循各模块 docs/standards；修改 Codex 内核先读 codex-runtime/AGENTS.md。

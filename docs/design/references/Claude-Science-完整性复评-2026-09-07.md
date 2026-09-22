# Claude Science 仓库完整性复评

日期：2026-09-07。本次已 fetch 并快进同步 main，递归初始化两个子模块；没有合入候选分支或修改源码。

## 结论修正

此前“完整应用仍依赖恢复 bundle”的判断只适用于根目录原有 hybrid 工程。最新 main 增加了独立 First-Party Lab：本机已成功从其本地源码构建六个运行入口，并验证源码依赖闭包、契约台账和构建清单。生成清单为 completeSourceBuild=true、behaviorallyComplete=false。

因此当前准确状态是：**存在可独立构建的应用重实现，但行为、产品接线和真实 Agent 闭环仍未全部完成。** 这不意味着原始开发仓库被完整恢复，也不证明与原产品完全等价。

## 同步版本

| 部分 | 固定提交 | 用途 |
|---|---|---|
| 根 main | bfaa541d | 原发布恢复档案、hybrid 工程、子模块引用 |
| first-party-lab | 6c6b448f | 新增独立工作台源码 |
| orchestration | 63c9387f | 工作计划、进度与审查记录，不是运行时编排器 |

两个子模块实际来自同一 GitHub 仓库的不同分支。仅拉 main 会得到 gitlink；本次已执行 git submodule update --init --recursive，实际代码已经检出。旧发布二进制 LFS 指针仍未补齐，与新增源码工程构建无关。

## 本机验证

Node.js v24.19.0；npm ci --ignore-scripts 安装锁定依赖。

- npm run build：通过。构建器执行 TypeScript 编译及 esbuild 打包。
- npm run verify:closure：通过。
- npm run verify:contracts：通过，但摘要明确为 9/9 旧维度未完成；新验收维度 5 项派生、4 项未测量。通过表示台账符合约束，不表示产品完成。
- npm run verify:manifest：通过。
- build/build-manifest.json：六个 root 的 sourcePresent、outputPresent、complete 均为 true；整体 behaviorallyComplete=false。
- 六个入口：daemon、web、artifact worker、compute worker、index worker、terminal launcher。
- 已启动与 npm test 相同的测试集合（复用刚生成的 build），但源码闭包负向测试持续数分钟尚未结束；为本次静态/构建评估主动停止，本次回归非全绿且受中断影响，不能当作完整验收。已观察到测试环境失败：多项 HTTPS 测试依赖硬编码 /opt/homebrew/bin/openssl 而本机不存在；计算测试报告 Local Python compute is unavailable / provision_unavailable。不能将这些环境失败直接判定为业务算法缺陷。中断后的 runner 汇总为 1966 项，1937 通过、28 失败、1 取消；它不是完整测试全集的最终验收计数。日志保留在 work/first-party-lab-tests.log。
- 未进行真实模型调用或完整科学任务验收；未单独重跑浏览器全集和确定性构建门禁。

## 完整性分层

| 层面 | 现在的判断 |
|---|---|
| 发布包恢复 | 仍是原工程的核心；原始 TS 类型、模块边界及发布前删除资源等不可逆缺失不变 |
| 独立源码构建 | First-Party Lab 已在本机验证通过；旧 hybrid 仍保持 completeSourceBuild=false，两者并存 |
| 后端系统 | 已有认证、项目、会话、权限、产物、计算、MCP、记忆等模块和测试；不能由路由登记数量推导端到端能力 |
| 前端系统 | 已有真正的 TSX 工程、打包入口和页面组件；部分页面依赖仍保留 unattached 状态 |
| Agent 业务 | 编排记录明确说明真实 agent executor 尚未闭合；不能宣称已具备完整的自主科研/数模能力 |
| 与原产品行为等价 | 未完成，存在分母差异、未验证事件和未测量维度 |
| 下游采用状态 | 新 README 明示 private non-clean-room behavioral reconstruction，未放行下游继承/再分发；构建完整不能替代该判断 |

## 仍缺的产品连接

依据 orchestration/docs/orchestration/plan.md 当前记录：

1. 产物版本与会话绑定 SRC-1：候选 cd2e4a9 尚未合入；记录最终全量测试 1989/1991、浏览器 21/21，两项锁竞争/CPU 测试待解决。
2. 完整产物导入 IMP-2：候选 278045d 仅出版/发布前置环节定向 35/35；完整导入接线仍待完成。
3. 项目与设置页面 WEB-1/SET-1：候选 2073d3e 有定向及浏览器验证，尚待源码闭包接线和完整验收。
4. 产物 UI AUI-1、引导偏好 ONB-1：记录尚未实施或未完成。
5. 项目共享上下文的存储与 prompt 消费、attention/未读信号定义、真实 Agent 执行器：未闭合。

主 README 记录已接受版本历史测试 1972 项、浏览器 20 项通过；它是仓库历史证据，不应与本次实测混写。

## 台账数字如何理解

governance/behavior-scorecard.json 当前记录：路由 324/331（实现分母 324，存在口径差异）；事件真正接线 47/504；MCP 191/271；UI 154/217（实现分母 154）。这些分别是登记、接线或契约计数，不能加权成“恢复百分比”。Backend、Frontend、Runtime、Security 四项仍未测量。

## 对 Daedalus / Theia 的影响

参考价值明显提升：现在可以研究一个独立构建的 TypeScript/React 工作台实现及其测试，而不只研究恢复 bundle。优先参考执行隔离、状态/事件、产物版本和 UI 接线方法。但不能因此把它当作完成的 Agent，也不应直接将旧评估中的“可参考”升级为“整库迁入”。下一阶段应围绕真实执行器 → 任务状态 → 计算结果 → 产物展示这一条业务链评估，而不是继续只统计文件与路由。

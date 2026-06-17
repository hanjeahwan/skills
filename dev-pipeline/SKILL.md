---
name: dev-pipeline
description: 用于高约束、多阶段的 repo 开发协作：先判定交付模式，再按状态机推进理解上下文、方案关卡、实现、验证、交付和回流。适用于代码实现、bug 排查、代码审查、重构、TDD/test-first、技术文档同步，以及多模块、状态流、外部 contract、副作用、权限/数据流、用户可见行为等高风险任务。只读模式不落盘，单文件低风险改动走轻量路径；单条命令、纯概念问答不使用。
---

# 通用开发流水线

用状态机组织 repo 开发：先定交付模式，再按状态、事件、守卫条件和动作推进；需要细节时先读 `references/resource-map.md`，再按地图选择具体参考文件。

## 关键边界

- 遇到 `plan only` / `review only` / `explain only`，本轮就是只读任务：不创建任务台账，不改文件，不 stage，不 commit。
- 提交保持显式授权：只有用户明确要求提交，或交付 diff 后确认提交，才按 repo 约定 commit；push 同理。
- 任务台账只用于多步实现、长任务恢复、切片、执行计划批准、回流和已搁置阻塞；只读任务和单文件低风险任务默认跳过。
- 单文件低风险任务走轻量路径：不启动子代理、不切片、不建任务台账、不强制执行计划批准；需要解释时，用一句话说明跳过原因。一旦范围扩大到多模块、contract、状态流、副作用或用户可见行为，转入高约束主干。
- 高约束实现进入写入前必须停在 `PlanApproval`：`approved_plan_revision == current_plan_revision` 才能进入 `Implement`；用户在初始请求里说“完整流程执行”不等于批准后续生成的执行计划。
- 删除、覆盖、迁移、部署、发送消息、批量写入、联网改状态、付费调用等高副作用操作，必须先停下拿到明确确认。

## 入口判定

先理解用户输入，再定模式：

- 抽出范围、明确不做项和模式约束，例如 `plan only`、`review only`、`explain only`。
- 请求有歧义且会改变实现路径时，只问一个关键问题；能从代码或文档判断的细节直接查证。
- 未澄清就继续推进时，记录关键假设和 `wrong_if`：假设错了要回退或改动什么。

- 交付物是单命令、纯概念、无需 repo 的一步问答 -> `OffRamp`：直接答，不进流水线。
- 明确 `plan only` / `review only` / `explain only`，或交付物是判断、方案、review、风险评估、扫描结果 -> `ReadOnly`：只读，止于方案/审查结论。
- 交付物是改好的代码/文档/修复后的行为 -> `Implementation`：进入主状态机并走到交付。
- 不清楚 -> 默认 `ReadOnly`：先复述交付物和建议路径，不写文件。

入口边角规则见 `references/entry-modes.md`。

## 主状态机

高约束实现主干状态是：

```text
Intake -> ContextGather -> Plan -> PlanReview -> PlanApproval -> Implement -> Review -> Verify -> Deliver -> RuleDistill
```

常见分支和回流：

- `OffRamp`：单步问答直接结束。
- `ReadOnly`：只读模式；不写文件、不建任务台账、不进实现关卡。普通 plan/explain 不强制子代理；review/security/architecture/synthesis 等有独立审查价值时可启动只读子代理。
- `WaitForUser`：高副作用、破坏性操作、关键信息缺失或用户确认门槛触发时停下。
- `Parked`：外部阻塞明确化，只推进与阻塞决策独立的工作，记录解除后回到哪个状态。
- `Context`：低风险或只读任务由主线程收集证据；高约束实现默认走 `ContextGather`。
- `ContextGather`：高约束实现的阻塞式上下文子代理关卡。
- `PlanReview`：高约束方案的阻塞式子代理关卡。
- `PlanApproval`：高约束方案的用户批准关卡；没有当前计划版本的明确批准，不能写文件。
- `Review`：实现完成后的阻塞式子代理审查关卡；通过后才进入 `Verify`。
- `ImplementSlice`：偏大任务按纵向片推进，每片独立实现和最小验证。
- `UpdatePlan` / `FixFindings`：方案审查或实现审查 findings 的回流状态。
- `RuleDistill`：任务结束前的规则沉淀检查；只有用户纠正或 review/测试/子代理暴露可复用决策偏差时才落规则。

完整状态、事件、守卫条件、动作和退出条件见 `references/statechart.md`。

### 上下文

- 先读当前 repo 的约束来源：repo instruction files、README、docs、ADR、TODO、用户点名的规范文件。
- 改代码前收集上下文：现有工作流分支、相邻实现、service/API contract、数据流、控制流、命名模式、测试或验证入口。
- 涉及状态流或用户动作时，沿事件做守卫条件/副作用审查：允许状态、禁止状态、no-op 行为、缺失守卫条件、副作用归属、终止行为，以及测试/文档是否覆盖当前行为。
- 重构、迁移、架构调整这类高风险工作，按 `references/refactor-prep.md` 准备。
- 高约束实现默认启动 `context-manager` 子代理作为 `ContextGather` 关卡，打包 repo 证据、入口、contract、风险和未解问题；它只产证据包，不替主线程定方案。
- `ContextGather` 是 blocking 关卡。子代理回来慢不是降级理由；只有工具不可用、平台禁止或安全边界冲突时，才记录本地替代证据包后继续。

### 方案

- 大改前先形成执行计划：当前行为、目标行为、改动范围、保持不变的行为、风险、验证计划。
- 启用任务台账时，执行计划写入 `.dev-pipeline/<date>-<short-slug>/plan.md`，任务台账写入同目录 `task.md`。
- 任务偏大时，方案里切纵向片：每片是一条薄的端到端改动，有明确验证入口。
- 进入 `PlanReview` 前，执行计划必须通过质量自查：需求覆盖、无 TODO/TBD/占位符、切片可执行且可验证、文件/contract/状态流/副作用边界清楚、验证计划具体。
- 主线程基于 `ContextGather` 证据包形成方案，然后进入 `PlanReview`：按 `references/delegation.md` 声明子代理执行体的 `purpose`、`join_point`、`max_impact`、`wait_policy`、`prompt_source` 和 `prompt_basis`。
- `PlanReview` 是 blocking 关卡，输入必须包含 `plan.md`、`ContextGather` 证据包和关键源码/contract 引用。返回 findings 时先 `UpdatePlan`：改变目标行为、contract、状态流、副作用归属、验证策略或实现边界的 material change 必须更新 `plan.md`、刷新 `current_plan_revision`、置旧批准失效并重过 `PlanReview`；不改变这些边界的 minor scoped note 可记录采纳/不采纳理由后进入 `PlanApproval`。
- `PlanApproval` 是用户批准关卡。主线程把执行计划摘要和 `plan.md` 路径发给用户，等待明确批准；只有批准当前计划版本后才能进入 `Implement`。用户要求改执行计划时回 `UpdatePlan`；批准语义含糊时停在 `PlanApproval`。
- `ReadOnly` 在此交付方案或审查结论即止。`Implementation` 只有在轻量路径守卫通过，或高约束主干满足 `plan_approval_guard` 后，才进入 `Implement`。

### 实现

- 范围以本轮目标为边界：只纳入完成目标必需的相邻流程、入口校验、交互策略、持久化、运行期副作用和数据模型变化。
- 高约束主干开始写入前，检查 `approved_plan_revision == current_plan_revision`；不满足时回到 `PlanApproval`，不要用最初的“按完整流程执行”当作批准。
- 已切片时进入 `ImplementSlice`：片状态随状态转移更新为 `planned`、`implementing`、`min_verified`、`complete` 或 `rework`。
- 实现规则见 `references/implementation.md`；调试、TDD、文档等分支按下方分支模式加载对应参考文件。
- 实现完成后进入 `Review` blocking 关卡：子代理按 `scope_compliance` 和 `implementation_quality` 审查当前 diff snapshot、行为回归和验证覆盖。发现 findings 时进入 `FixFindings`，修复后重过 `Review`；无 findings 且当前 diff 未替换审查 snapshot，才进入 `Verify`。

### 验证

- 修改后走检查清单：命名、重复状态、非法状态、数据来源是否唯一、副作用归属、事件守卫条件、boolean 前缀、范围是否漂移、可读性、验证是否足够。
- 按验证选择矩阵执行；没做的验证要明确说。
- `Verify` 由主线程执行实际验证，例如定向测试、typecheck、lint、静态检查、代码路径审查或未验证项记录；`Review` 不能替代 `Verify`。
- 验证发现实现 bug -> 回 Implement；发现需求/方案理解错 -> 回 Plan；发现验证覆盖不足 -> 留在 Verify 补验证或记录缺口。

### 交付

- 检查最终 diff、旧命名、重复状态、工作区 dirty、导出命名和 `git diff --check`。
- `Deliver` 发现仍要修东西时，先按问题类型回流，不进入 `RuleDistill`：实现漏改、旧命名或 diff 问题回 `Implement`；验证记录不足或该补验证回 `Verify`；需求或方案理解错回 `Plan` / `UpdatePlan` 并让旧批准失效；只有最终回复内容缺依据或表达不完整时留在 `Deliver` 修交付内容。
- 任务台账启用时，最终回复从验证记录和当前 diff 生成；交付回复保留可复跑的验证依据。
- 仅在用户明确要求提交，或交付 diff 后用户确认提交时，才 commit；不 push，除非用户明确要求。
- 只有 `delivery_ready` 后才进入 `RuleDistill` 检查：用户纠正、review/测试/子代理结果暴露可复用决策偏差时，按 `references/rule-distillation.md` 判断是否沉淀；没有可复用规则时记录 `not_needed`，不要为凑流程写空规则。

## 分支模式

按触发词切入对应分支，只加载需要的参考文件：

- **代码审查** — 触发：`review`、`code review`、`看 diff`、`审这个 PR`。只读，不进 Implement。加载 `references/code-review.md`。
- **调试** — 触发：报 bug、行为异常、排查、`debug`。加载 `references/debugging.md`。
- **测试驱动** — 触发：`TDD`、`test-first`、`red-green-refactor`、明确要求 test-first integration coverage，或高风险行为且已有可维护 test harness。普通 integration tests 不自动触发 TDD。加载 `references/tdd.md`。
- **文档** — 触发：改 README/ADR/技术说明。加载 `references/docs.md`。
- **重构准备** — 触发：高风险重构/迁移/架构调整。加载 `references/refactor-prep.md`。

## 跨阶段守卫条件

### 沟通方式

- 遵守当前系统、用户和 repo 的语言政策。
- 开门见山，先给结论，再解释机制和取舍。
- 用真实用户场景说明问题为什么重要，再解释技术机制。
- 不要把用户拉进不必要的输入请求；能从代码和文档判断时直接推进。

### 项目适配

- 不要预设框架或项目技术栈。
- 当前 repo 有本地说明、框架文档、团队规范、ADR 或项目约定时，优先加载并遵守。
- API contract 以实际 types、services、schemas 和调用点为准；不要发明字段、状态、权限规则或配置对象。
- 涉及外部库、框架、SDK、协议或 API 签名时，先查当前项目依赖、类型定义、官方文档或用户指定来源。

### 工作区保护

- 在 git repo 里改文件前，先看 `git status --short`；把已有 modified/untracked 文件当作用户或其他流程的工作。
- 如果目标文件已经 dirty，先读当前 diff，再叠加本次修改；不要覆盖、格式化或回滚无关改动。
- 未经用户明确要求或确认，不 stage、commit、push。
- 最终检查只解释本次自己改动的范围；无关 dirty 文件不当作自己的成果。

### 阻塞处理

- 阻塞只影响部分范围时进入 `Parked`，记录阻塞点和 `resume_state`，先推进与该决策独立的工作。
- 整条任务被阻塞时进入 `WaitForUser`；不要猜测业务规则、接口行为、环境状态或他人决策。

### 任务台账

- 启用任务台账时，先列 `.dev-pipeline/`；有同任务目录就接续，没有再新开 `.dev-pipeline/<date>-<short-slug>/`。
- 任务台账目录包含两份文件：`task.md` 是任务台账，记录 `current_state`、计划版本、批准状态、切片状态、子代理执行体状态、已搁置阻塞、验证记录和回流历史；`plan.md` 是待批准执行计划。
- 只依赖写文件，不依赖宿主的 task 工具；保持临时工作态，绝不 commit。
- 任务台账模板和更新规则见 `references/task.md`；执行计划模板、revision 和审批语义见 `references/plan.md`。

### 子代理委派

- 把子代理作为状态机里的执行体管理：启动前先定义目的、等待点、影响范围和等待策略。
- 命中高风险守卫条件且有独立审查/验证价值时默认启动；只有工具不可用、平台禁止或安全边界冲突时，才进入本地替代审查降级。未启动必须记录低风险、强耦合、工具失败或安全边界原因。
- 启动任何子代理前必须先完成 prompts 发现协议，并声明 `purpose`、`join_point`、`max_impact`、`wait_policy`、`prompt_source` 和 `prompt_basis`；没有 `join_point`、`prompt_source` 或 `prompt_basis` 的子代理不启动。
- blocking 关卡执行体未满足前不能越过对应状态；回来慢不是降级理由。只有工具不可用、平台禁止或安全边界冲突时，才记录本地替代审查降级。
- 细节和发现协议见 `references/delegation.md`。

### 验证选择矩阵

- 行为改动：优先跑覆盖该行为的定向测试；没有测试时做手动路径验证并说明缺口。
- 前端可视行为：浏览器验证只在用户明确要求时执行。用户没有明确要求浏览器验证时，默认用定向测试、typecheck、lint、静态检查或代码路径审查替代，并列出未验证的具体交互。
- 类型、schema、API contract 改动：跑 typecheck 或最接近的静态检查，并检查调用点。
- 构建、打包、产物生成类命令默认不跑。只有用户明确要求 build、打包或生成产物时才运行；不要因为任务看起来可能需要构建产物而自行推断授权，否则按策略跳过并使用更窄验证替代。常见例子包括项目的 build、compile、bundle、export、package 或 artifact 生成脚本。
- 本地服务、开发服务器和预览服务器类命令默认不跑。只有用户明确要求启动 server、给 URL，或明确要求浏览器验证且端口归属、登录态/测试数据和停止策略都明确时才启动；否则按策略跳过并使用更窄验证替代。常见例子包括项目的 start、dev、serve、preview、watch server 或 local server 脚本。
- 文档改动：对照事实来源核对命令、路径、术语和示例，不默认跑全量测试。

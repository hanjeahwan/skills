# 子代理执行体生命周期

把子代理作为状态机里的执行体管理：启动前先定义目的、等待点、影响范围和等待策略。
调用宿主能力时保留触发语义：`spawn subagents` / `delegate` / `subagent workflows` / `parallel agent work`。

## 执行体类型

- **阻塞式关卡**：挡住某个状态转移；返回前不能越过等待点。高约束实现默认使用这类执行体。
- **`non_blocking` 旁路执行体**：旁路探索；主线程可以继续，但必须声明最大影响范围，返回后只在影响范围内决定是否回流。

回来慢不是降级理由。只有子代理工具不可用、平台规则不允许调用，或安全边界冲突时，阻塞式关卡才能进入本地替代审查降级。

## 启动条件

命中任一高风险守卫条件，且存在边界清楚的只读审查、上下文打包或独立验证时，默认启动阻塞式关卡；工具不可用、平台规则不允许调用或安全边界冲突时，进入本地替代审查降级：

- 多模块或跨边界改动。
- 状态流、权限/数据流、副作用、外部 contract 或用户可见行为变化。
- 有可独立审查的上下文证据包、方案、diff 或验证计划。
- 多个发现项需要去重、保留冲突并形成决策视图。

单文件低风险、强耦合设计判断、需要连续用户交互、或当前上下文必须由主线程直接决定时，不启动；用一句话或任务台账说明低风险、强耦合、工具失败或安全边界原因。

只读任务不创建任务台账、不进入实现关卡；但 review/security/architecture/synthesis 等只读审查有独立价值时，仍可启动只读子代理。

## 发现协议

启动任何子代理前先按约定发现模板；这是 `prompt_template_guard` 的输入，不是可选说明：

1. 列出本文件旁边的 `./prompts/`，即 `<skill-root>/references/prompts/`。
2. 读每个文件头部的 H1 和 `触发：` 行。
3. 只加载匹配的一个模板，把模板全文和本次具体输入喂给子代理。
4. 没有匹配模板时，现写任务说明，但必须包含只读边界：禁止 Edit/Write/revert/stage/commit/push，只回结论。

每次启动前把发现结果压成两个字段：

- `prompt_source`：匹配模板路径，例如 `references/prompts/context-manager.md`；没有匹配模板时写 `fallback`。
- `prompt_basis`：匹配到的 `触发：` 行摘要；`prompt_source: fallback` 时写没有匹配模板的原因和只读边界。

不要点名宿主注册的 agent、subagent_type、agent 路径或模型；使用当前宿主的子代理启动机制。

## 执行体契约

启动前把执行体契约和输入包一起给子代理；不要让子代理靠整段聊天历史或完整计划自己猜重点。

每次启动前先声明：

```text
purpose: context-gather | plan-review | diff-review | security-review | architecture-review | verification | synthesis | sidecar-research
join_point: before_plan | before_implement | before_verify | non_blocking
max_impact: context | plan | implement | verify | deliver
blocking: yes | no
wait_policy: wait_until_returned | unavailable_degrade_only | non_blocking
prompt_source: references/prompts/<template>.md | fallback
prompt_basis: <匹配的 触发：行摘要；fallback 时写 no matching template + 原因和只读边界>
```

- `purpose`：为什么启动。没有明确目的不启动。
- `join_point`：它挡哪个门。阻塞式关卡没有等待点不启动。
- `max_impact`：它最多能让主线程回流到哪里，避免晚到结果无限推翻。
- `blocking`：是否阻塞状态转移。
- `wait_policy`：等待到返回、仅不可执行时降级，或作为旁路任务继续。
- `prompt_source`：按发现协议加载的模板路径；没有匹配模板时只能写 `fallback`。
- `prompt_basis`：为什么选这个模板；fallback 时写明未匹配原因和临时说明的只读边界。

输入包至少包含：

- `task_goal`：本次要判断或降低的风险。
- `artifact_ref`：正在审的 `plan.md` revision、diff snapshot、verification record 或证据包版本。
- `evidence`：相关文件、diff、contract、schema、测试入口或任务台账路径；只给与本次目的相关的范围。
- `forbidden_actions`：只读边界、禁止写入、禁止 stage/commit/push、禁止运行未授权高成本命令或改变 runtime 状态。
- `expected_output`：期望返回发现项、通过条件、残余风险和需要回流的状态。

等待点语义：

- `before_plan`：上下文关卡。`ContextGather` 返回证据包前不能进入 `Plan`；只允许工具不可用、平台禁止或安全边界冲突时本地替代。
- `before_implement`：方案审查关卡。`PlanReview` 返回无发现项，或发现项经 `UpdatePlan` 处理并满足守卫条件前，不能进入 `PlanApproval`；用户批准当前计划版本前，不能进入 `Implement`。
- `before_verify`：实现审查关卡。`Review` 返回无发现项，或发现项经 `FixFindings` 修复并重审前，不能进入 `Verify`。
- `non_blocking`：旁路探索。主线程可以继续，但必须记录 `max_impact`；返回后只在影响范围内决定是否回流。

兼容旧阶段名时可把 `before_stage_3` 理解为 `before_implement`，把 `before_stage_5` 理解为 `before_verify`；新记录优先使用新等待点。

## 常见执行体

| 执行体 | join_point | max_impact | blocking | wait_policy | 适用场景 |
| --- | --- | --- | --- | --- | --- |
| `context-gather` | `before_plan` | `context` 或 `plan` | yes | `wait_until_returned` | 高约束实现前打包 repo 证据、入口、contract、风险和未解问题 |
| `plan-review` | `before_implement` | `plan` | yes | `wait_until_returned` | 高风险方案进入用户批准前，审查范围、contract、状态流和验证计划 |
| `diff-review` | `before_verify` | `implement` | yes | `wait_until_returned` | 交付前独立审查 diff 正确性、行为回归和缺测试 |
| `security-review` | `before_implement` 或 `before_verify` | `plan` 或 `implement` | yes | `wait_until_returned` | auth、密钥、敏感数据、输入校验、网络/配置暴露 |
| `architecture-review` | `before_implement` | `plan` | yes | `wait_until_returned` | 架构边界、耦合、数据归属、长期维护性 |
| `verification` | `before_verify` | `verify` | yes | `wait_until_returned` | 并行跑独立验证或审查验证覆盖 |
| `synthesis` | `before_implement`、`before_verify` 或 `non_blocking` | `plan` / `verify` / `deliver` | depends | 按等待点声明 | 多个子代理结果需要去重、保留冲突和决策汇总 |
| `sidecar-research` | `non_blocking` | 按任务声明 | no | `non_blocking` | 不挡主流程的旁路探索 |

## 方案审查关卡

`Plan` 命中高风险守卫条件时，启动 `plan-review` 阻塞式关卡。它审查计划是否可信，不授权写代码。

计划审查输入至少包含：

- `plan.md` 当前版本。
- `ContextGather` 证据包或本地替代证据包。
- 关键源码、contract、schema、service 或测试入口引用。

计划审查至少覆盖四个视角中与任务相关的部分：

- 行为回归与范围漂移。
- 状态流与副作用。
- contract 与边界。
- 验证充分性。

返回发现项时进入 `UpdatePlan`：

- 改变目标行为、contract、状态流、副作用归属、验证策略或实现边界的发现项是 material change，必须更新方案并重过 `PlanReview`。
- 不改变这些边界的发现项才能作为 minor scoped note，记录采纳/不采纳理由后进入 `PlanApproval`。

`PlanReview` 通过后只能进入 `PlanApproval`。只有用户明确批准当前 `plan.md` 版本，且任务台账满足 `approved_plan_revision == current_plan_revision`，才能进入 `Implement`。用户在初始请求里说“完整流程执行”不算批准后续生成的执行计划。

## 实现审查关卡

`Implement` 完成后启动 `diff-review`、`verification` 或匹配风险的阻塞式关卡。

审查至少覆盖：

- `scope_compliance`：diff 是否符合用户需求、当前批准方案和改动范围，有无漏做、误做或额外行为。
- `implementation_quality`：代码质量、测试、可维护性、错误处理和风险控制是否足够。
- 行为回归、非法状态和副作用归属。
- contract、类型、schema 或权限/数据流风险。
- 验证记录是否覆盖关键风险，未验证项是否具体。

`scope_compliance` 不通过时必须当作阻塞发现项处理，不能降级成普通质量建议。返回发现项时进入 `FixFindings`；修复或明确不采纳并记录理由后，必须重过 `Review`。无发现项且审查 snapshot 仍匹配当前 diff 时，才能进入 `Verify`。

## 结果处理

执行体返回后先看契约：

- 阻塞式关卡无发现项：通过对应等待点；`plan-review` 的下一状态是 `PlanApproval`，不是 `Implement`。
- 阻塞式关卡有发现项：回流到 `UpdatePlan` 或 `FixFindings`，不能继续越过等待点。
- 子代理通过是被审产物（artifact）的证据，不是完成证明；进入下一状态前确认当前 `plan_revision`、diff snapshot 或 verification record 没有被后续改动替换。
- 结果已被后续改动覆盖：记录证据，但仍要判断是否需要重审当前 diff 或方案。
- 结果与 repo 事实不符：记录不采纳理由；若它本来挡关卡，必须说明为何不采纳后仍满足守卫条件。
- 工具不可用、平台规则不允许或安全边界冲突：记录 `unavailable_degrade_only` 的本地替代审查。

影响切片时，更新切片状态；影响验证时，更新验证记录。

# 状态机（statechart）

使用本表判断当前状态、可触发事件、必须满足的守卫条件、应执行的动作和退出条件。

## 状态

| 状态 | 目的 | 退出条件 |
| --- | --- | --- |
| `Intake` | 理解用户请求并判定交付模式 | 明确进入 `OffRamp`、`ReadOnly` 或 `Implementation` |
| `OffRamp` | 单命令、纯概念或无需 repo 的一步问答 | 直接回答，不创建任务记录 |
| `ReadOnly` | 只读模式门：设置 `mode: ReadOnly`，禁止写文件和 `Implement` | 进入 `Context` 收集证据，或在 `Plan` 后交付判断 |
| `Context` | 收集 repo 约束、相邻实现、contract、数据/控制流 | 足够支撑方案；或发现需用户澄清 |
| `Plan` | 形成方案、审查结论、风险、范围、验证计划和切片 | 守卫条件通过；或进入 `WaitForUser` / `PlanReview` |
| `PlanReview` | 对高风险方案做关卡审查 | 关卡通过；或记录降级审查；或退回 `Plan` |
| `Implement` | 按方案执行写入 | 所有必要切片完成；或发现需要回流 |
| `ImplementSlice` | 纵向片子状态 | 当前片达到 `complete` 或 `rework` |
| `Verify` | 验证行为、contract、类型和风险 | 验证足够；或按问题类型回流 |
| `Deliver` | 最终 diff 或只读结论、验证记录、交付回复和提交边界检查 | 交付完成；或发现问题回流 |
| `WaitForUser` | 等待确认、关键信息或高副作用授权 | 用户补齐信息或确认后回到原状态 |
| `Parked` | 外部阻塞被搁置但仍可推进其它部分 | 阻塞解除后回到记录的状态 |

## 事件与转移

| 事件 | 来源 | 目标 | 守卫条件 |
| --- | --- | --- | --- |
| `mode_decided.off_ramp` | `Intake` | `OffRamp` | 单步问答或单命令 |
| `mode_decided.read_only` | `Intake` | `ReadOnly` | 明确 plan/review/explain only，或交付物是判断 |
| `mode_decided.implementation` | `Intake` | `Context` | 交付物是改好的代码/文档/行为 |
| `read_only_context_needed` | `ReadOnly` | `Context` | 只读任务需要 repo 证据、方案或审查 |
| `context_ready` | `Context` | `Plan` | 约束、入口、contract 和验证入口足够 |
| `needs_user` | 任意写入前状态 | `WaitForUser` | 信息缺失、高副作用或确认门槛触发 |
| `plan_needs_gate` | `Plan` | `PlanReview` | 高风险守卫条件命中 |
| `plan_gate_passed` | `PlanReview` | `Implement` | 关卡执行体返回通过或发现已纳入方案 |
| `plan_gate_degraded` | `PlanReview` | `Implement` | 工具不可用/失败/超时并完成本地替代审查 |
| `plan_changed` | `PlanReview` | `Plan` | 发现方案缺陷、范围错误或 contract 风险 |
| `read_only_ready` | `Plan` | `Deliver` | `mode: ReadOnly`，方案、判断或审查结论可交付 |
| `slice_started` | `Implement` | `ImplementSlice` | 当前片有明确目标和最小验证 |
| `slice_complete` | `ImplementSlice` | `Implement` | 当前片完成并记录最小验证 |
| `implementation_done` | `Implement` | `Verify` | 所有必要片完成 |
| `implementation_bug` | `Verify` | `Implement` | 验证发现实现错误 |
| `requirement_or_plan_wrong` | `Verify` | `Plan` | 验证发现需求或方案理解错 |
| `validation_gap` | `Verify` | `Verify` | 验证不足但可继续补 |
| `validation_sufficient` | `Verify` | `Deliver` | 验证记录能支撑交付 |
| `final_check_failed` | `Deliver` | `Verify` 或 `Implement` | diff、验证、工作区或命名检查失败 |
| `blocker_parked` | 任意可局部推进状态 | `Parked` | 外部阻塞影响部分范围，已记录 `resume_state` 和可推进范围 |
| `independent_work_continues` | `Parked` | 原可推进状态 | 只推进与阻塞决策独立的工作 |
| `blocker_resolved` | `Parked` | `resume_state` | 阻塞解除，回到记录状态 |
| `delivered` | `Deliver` | 结束 | 最终回复完成，且未越过 commit/push 授权 |

## 守卫条件

- `read_only_guard`：只读模式不创建任务记录、不写文件、不 stage、不 commit。
- `side_effect_guard`：删除、覆盖、迁移、部署、发送消息、批量写入、联网改状态、付费调用等高副作用操作必须进入 `WaitForUser`。
- `scope_guard`：实现只纳入本轮目标必需的相邻流程、入口校验、交互策略、持久化、运行期副作用和数据模型变化。
- `delegate_gate_guard`：关卡执行体未满足前不能越过声明的 `join_point`；降级越过必须记录本地替代审查。
- `parked_guard`：`Parked` 只允许推进与阻塞决策独立的工作；整条任务被阻塞时进入 `WaitForUser`。
- `oscillation_guard`：同一对状态间回流超过 2 次，停下总结卡点，给用户选项。
- `verification_guard`：最终回复里的验证结论必须能从验证记录、实际工具调用或当前 diff 追溯。

## 动作

- `record_state`：任务记录启用时，记录当前状态、触发事件、关键守卫条件和下一步。
- `record_assumption`：未澄清就推进时，记录假设和假设错了要回头改什么。
- `record_slice_transition`：切片进入、最小验证、完成或回流时更新切片状态（`slice_states`）。
- `spawn_delegate_actor`：按 `references/delegation.md` 声明执行体生命周期后启动子代理。
- `record_delegate_result`：记录执行体结论、影响状态、是否回流或降级理由。
- `record_verification`：记录实际命令或完整目标范围、覆盖风险、未验证项和替代证据。
- `record_parked_blocker`：记录阻塞点、等待对象、解除后回到的状态。

## 切片子状态

```text
planned -> implementing -> min_verified -> complete
                         -> rework
```

- `planned`：片有目标、范围和最小验证。
- `implementing`：正在写入该片。
- `min_verified`：片内最小验证完成或缺口已记录。
- `complete`：片已合入当前方案，等待全局 Verify。
- `rework`：审查、验证或用户反馈要求回流。

合并多个片实现或验证时，必须说明为什么不会掩盖失败归因。

## 验证记录

验证记录要能让交付回复可追溯：

- 已跑验证：实际命令，或命令名 + 完整目标范围 + 关键参数；说明覆盖的行为、contract 或风险。
- 未跑验证：具体行为或状态、预期结果、未跑原因、替代证据。
- 失败验证：错误摘要、归因、回流到哪个状态、补跑结果。

不要把验证压成不可复跑摘要，例如只写“相关测试通过”或省略目标范围。

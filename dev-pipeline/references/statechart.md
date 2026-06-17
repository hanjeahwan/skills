# 状态机（statechart）

使用本表判断当前状态、可触发事件、必须满足的守卫条件、应执行的动作和退出条件。

高约束实现主干：

```text
Intake -> ContextGather -> Plan -> PlanReview -> PlanApproval -> Implement -> Review -> Verify -> Deliver -> RuleDistill
```

只读、轻量和阻塞分支仍可按事件进入 `OffRamp`、`ReadOnly`、`Context`、`WaitForUser`、`Parked` 或 `ImplementSlice`。

## 状态

| 状态 | 目的 | 退出条件 |
| --- | --- | --- |
| `Intake` | 理解用户请求并判定交付模式 | 明确进入 `OffRamp`、`ReadOnly`、`Context`、`ContextGather` 或 `WaitForUser` |
| `OffRamp` | 单命令、纯概念或无需 repo 的一步问答 | 直接回答，不创建任务台账 |
| `ReadOnly` | 只读模式门：禁止写文件、任务台账和实现关卡 | 进入 `Context` 收集证据，启动只读审查子代理，或在 `Plan` 后交付判断 |
| `Context` | 低风险或只读任务由主线程收集 repo 证据 | 足够支撑方案、审查结论；或发现需用户澄清 |
| `ContextGather` | 高约束实现的阻塞式上下文子代理关卡 | 子代理返回证据包；或工具不可用/平台禁止/安全边界冲突并完成本地替代证据包 |
| `Plan` | 主线程基于证据包形成方案、风险、范围、验证计划和切片，写入 `plan.md` | 方案通过计划质量自查且可审查；或进入 `WaitForUser` |
| `PlanReview` | 阻塞式方案审查子代理关卡，审 `plan.md`、上下文证据包和关键源码/contract 引用 | 无发现项进入 `PlanApproval`；或发现项进入 `UpdatePlan` |
| `PlanApproval` | 用户批准当前计划版本的阻塞关卡 | 当前计划版本被明确批准后进入 `Implement`；方案变更回到 `UpdatePlan` |
| `UpdatePlan` | 主线程处理方案审查发现项或用户改动要求 | material change 更新计划版本并回到 `PlanReview`；minor scoped note 记录后进入 `PlanApproval` |
| `Implement` | 按方案执行写入 | 所有必要切片完成；或发现需要回流 |
| `ImplementSlice` | 纵向片子状态 | 当前片达到 `complete` 或 `rework` |
| `Review` | 阻塞式实现审查子代理关卡，审 diff 正确性、行为回归和验证覆盖 | 无发现项进入 `Verify`；有发现项进入 `FixFindings` |
| `FixFindings` | 主线程修复实现审查发现项 | 修复完成后回到 `Review` |
| `Verify` | 主线程执行实际验证：定向测试、typecheck、lint、静态检查、代码路径审查或未验证项记录 | 验证足够；或按问题类型回流 |
| `Deliver` | 最终 diff 或只读结论、验证记录、交付回复和提交边界检查 | `delivery_ready` 后进入 `RuleDistill`；发现仍要修时先按问题类型回流 |
| `RuleDistill` | 任务结束前判断是否需要沉淀可复用规则 | 规则已沉淀或明确不需要沉淀，最终回复完成 |
| `WaitForUser` | 等待确认、关键信息或高副作用授权 | 用户补齐信息或确认后回到原状态 |
| `Parked` | 外部阻塞被搁置但仍可推进其它部分 | 阻塞解除后回到记录的状态 |

## 事件与转移

| 事件 | 来源 | 目标 | 守卫条件 |
| --- | --- | --- | --- |
| `mode_decided.off_ramp` | `Intake` | `OffRamp` | 单步问答或单命令 |
| `mode_decided.read_only` | `Intake` | `ReadOnly` | 明确 plan/review/explain only，或交付物是判断 |
| `mode_decided.implementation_light` | `Intake` | `Context` | 交付物是低风险改动，未命中高约束实现门槛 |
| `context_gather_required` | `Intake` | `ContextGather` | 高约束实现且有独立上下文打包价值 |
| `read_only_context_needed` | `ReadOnly` | `Context` | 只读任务需要 repo 证据、方案或审查 |
| `context_ready` | `Context` | `Plan` | 约束、入口、contract 和验证入口足够 |
| `context_gather_passed` | `ContextGather` | `Plan` | 阻塞式上下文子代理返回证据包 |
| `context_gather_degraded` | `ContextGather` | `Plan` | 仅工具不可用、平台禁止或安全边界冲突；已记录本地替代证据包 |
| `needs_user` | 任意写入前状态 | `WaitForUser` | 信息缺失、高副作用或确认门槛触发 |
| `plan_ready_for_review` | `Plan` | `PlanReview` | 高约束实现方案通过 `plan_quality_guard`，且当前 `plan.md` 可审查 |
| `plan_review_passed` | `PlanReview` | `PlanApproval` | 阻塞式方案审查返回无发现项，且 `reviewed_plan_revision == current_plan_revision` |
| `plan_review_findings` | `PlanReview` | `UpdatePlan` | 方案审查返回有效发现项 |
| `plan_update_material` | `UpdatePlan` | `PlanReview` | 发现项或用户要求改变目标行为、contract、状态流、副作用归属、验证策略或实现边界；旧批准已置为 stale |
| `plan_update_minor` | `UpdatePlan` | `PlanApproval` | 只是不改变方案边界的 scoped note，已记录采纳/不采纳理由 |
| `plan_approved` | `PlanApproval` | `Implement` | 用户明确批准当前 `plan.md` 版本，且 `approved_plan_revision == current_plan_revision` |
| `plan_change_requested` | `PlanApproval` | `UpdatePlan` | 用户要求改计划、范围、切片、风险或验证策略 |
| `approval_ambiguous` | `PlanApproval` | `PlanApproval` 或 `WaitForUser` | 批准语义不明确，继续等待或只问一个关键确认问题 |
| `read_only_ready` | `Plan` | `Deliver` | `mode: ReadOnly`，方案、判断或审查结论可交付 |
| `light_context_ready` | `Context` | `Implement` | 单文件低风险改动，`implementation_light_guard` 通过，未启用高约束主干 |
| `slice_started` | `Implement` | `ImplementSlice` | 当前片有明确目标和最小验证 |
| `slice_complete` | `ImplementSlice` | `Implement` | 当前片完成并记录最小验证 |
| `implementation_done` | `Implement` | `Review` | 所有必要片完成，当前 diff snapshot 可独立审查 |
| `review_passed` | `Review` | `Verify` | 阻塞式实现审查返回无发现项，`scope_compliance` 和 `implementation_quality` 均无阻塞项，且审查 snapshot 仍是当前 diff |
| `review_findings` | `Review` | `FixFindings` | 实现审查返回有效 `scope_compliance` 或 `implementation_quality` 发现项 |
| `fix_findings_done` | `FixFindings` | `Review` | 发现项已修复或明确不采纳并记录理由 |
| `verification_bug` | `Verify` | `Implement` | 验证发现实现错误 |
| `requirement_or_plan_wrong` | `Verify` | `Plan` | 验证发现需求或方案理解错 |
| `validation_gap` | `Verify` | `Verify` | 验证不足但可继续补 |
| `verification_sufficient` | `Verify` | `Deliver` | 验证记录能支撑交付 |
| `deliver_plan_fix_needed` | `Deliver` | `Plan` 或 `UpdatePlan` | 交付检查发现需求、方案、contract、状态流、副作用或实现边界理解错；旧批准必须置为 stale |
| `deliver_implementation_fix_needed` | `Deliver` | `Implement` | 交付检查发现实现漏改、旧命名残留、diff 问题或导出/命名错误 |
| `deliver_verification_fix_needed` | `Deliver` | `Verify` | 交付检查发现验证记录不足、缺应跑验证或未验证项不具体 |
| `deliver_response_fix_needed` | `Deliver` | `Deliver` | 交付物本身已就绪，但最终回复缺依据、措辞不清或没有反映验证记录 |
| `final_check_failed` | `Deliver` | `Plan` / `UpdatePlan` / `Implement` / `Verify` / `Deliver` | 兜底事件：按问题类型分流；不能进入 `RuleDistill` |
| `delivery_ready` | `Deliver` | `RuleDistill` | 最终 diff、验证记录、提交边界和交付内容已检查，且没有待修项 |
| `rule_distillation_needed` | `RuleDistill` | `RuleDistill` | 用户纠正、review/测试/子代理结果暴露可复用决策偏差，且通过规则沉淀四关 |
| `rule_distillation_not_needed` | `RuleDistill` | 结束 | 未发现可复用决策偏差，或不满足可泛化/最小/连贯/可执行 |
| `rule_distilled` | `RuleDistill` | 结束 | 已把规则沉淀到正确拥有者，并完成必要校验 |
| `blocker_parked` | 任意可局部推进状态 | `Parked` | 外部阻塞影响部分范围，已记录 `resume_state` 和可推进范围 |
| `independent_work_continues` | `Parked` | 原可推进状态 | 只推进与阻塞决策独立的工作 |
| `blocker_resolved` | `Parked` | `resume_state` | 阻塞解除，回到记录状态 |
| `delivered` | `RuleDistill` | 结束 | 最终回复完成，且未越过 commit/push 授权 |

## 守卫条件

- `read_only_guard`：只读模式不创建任务台账、不写文件、不 stage、不 commit；只读 review/security/architecture/synthesis 可启动只读子代理。
- `side_effect_guard`：删除、覆盖、迁移、部署、发送消息、批量写入、联网改状态、付费调用等高副作用操作必须进入 `WaitForUser`。
- `scope_guard`：实现只纳入本轮目标必需的相邻流程、入口校验、交互策略、持久化、运行期副作用和数据模型变化。
- `implementation_light_guard`：只允许单文件低风险改动跳过执行计划批准；不得涉及多模块、状态流、外部 contract、副作用、权限/数据流或用户可见高风险行为。范围扩大时转入高约束主干。
- `blocking_delegate_guard`：阻塞式子代理返回前不能越过等待点；回来慢不构成降级理由。
- `prompt_template_guard`：启动任何子代理前必须完成 prompts 发现协议并声明 `prompt_source` 和 `prompt_basis`；`prompt_source` 是模板路径时必须已加载模板全文，`prompt_source: fallback` 时 `prompt_basis` 必须说明没有匹配模板的原因和只读边界。
- `context_pack_guard`：`ContextGather` 只产 repo 证据、入口、contract、风险和未解问题，不替主线程定方案。
- `plan_quality_guard`：高约束计划进入 `PlanReview` / `PlanApproval` 前必须通过短自查：需求覆盖、无 TODO/TBD/占位符/“类似上一片”、切片可执行且可验证、涉及文件/owner/contract/命名清楚、验证计划具体；不通过时留在 `Plan` 修正。
- `plan_approval_guard`：高约束主干进入 `Implement` 前必须满足 `approved_plan_revision == current_plan_revision`；初始请求、模糊认可和旧计划批准都不能替代当前计划批准。
- `review_gate_guard`：`Review` 必须区分 `scope_compliance` 和 `implementation_quality`；任一类发现项未处理并重审前不能进入 `Verify` 或 `Deliver`，其中 scope/计划不一致不能降级成普通质量建议。
- `artifact_freshness_guard`：子代理通过只证明它审过的 `plan_revision`、diff snapshot 或 verification record；主线程继续修改后旧通过结果失效，进入 `Verify` / `Deliver` 前必须确认当前 artifact 仍匹配审查对象。
- `minor_note_guard`：只有不改变目标行为、contract、状态流、副作用归属、验证策略或实现边界的发现项，才能作为 minor scoped note 进入 `PlanApproval`。
- `side_effect_approval_guard`：`PlanApproval` 只授权按执行计划改文件；删除、部署、发送消息、批量联网改状态、付费调用等高副作用动作仍需单独确认，除非执行计划逐项列明环境、范围、回滚/停止条件且用户批准语义明确覆盖。
- `parked_guard`：`Parked` 只允许推进与阻塞决策独立的工作；整条任务被阻塞时进入 `WaitForUser`。
- `oscillation_guard`：同一类 PlanReview 或 Review 回流超过 2 次时，进入 `WaitForUser`；输出卡点摘要、已尝试路径、推荐下一步和最多 2 个可选方向，用户确认前不继续实现。
- `verification_guard`：最终回复里的验证结论必须能从验证记录、实际工具调用或当前 diff 追溯；子代理通过是证据，不替代主线程对当前 diff、任务台账和验证记录的检查。
- `delivery_ready_guard`：只有 diff、验证记录、提交边界、工作区归属和最终回复内容都不需要继续修正时，`Deliver` 才能进入 `RuleDistill`。
- `deliver_repair_guard`：`Deliver` 发现待修项时必须先分类回流；实现问题回 `Implement`，验证问题回 `Verify`，需求/方案问题回 `Plan` / `UpdatePlan` 并置旧批准为 stale，回复内容问题留在 `Deliver`。
- `rule_distillation_guard`：任务结束前必须判断是否存在可复用决策偏差；只有同时满足可泛化、最小、连贯、可执行，才按 `references/rule-distillation.md` 沉淀到正确拥有者。没有合格规则时记录 `not_needed`，不写空规则。
- `explicit_command_guard`：build、打包、启动 server 和浏览器验证必须由用户明确要求；未明确要求时按策略跳过并记录替代证据。

## 动作

- `record_state`：任务台账启用时，记录当前状态、触发事件、关键守卫条件和下一步。
- `record_assumption`：未澄清就推进时，记录假设和假设错了要回头改什么。
- `spawn_context_gather_actor`：满足 `prompt_template_guard` 后，按 `references/delegation.md` 启动阻塞式上下文子代理。
- `record_context_pack`：记录上下文证据包、未解问题和本地替代原因。
- `record_plan_revision`：写入或更新 `plan.md` 后记录 `current_plan_revision`；material change 必须置旧批准为 stale。
- `record_plan_quality_check`：记录计划质量自查结果；未通过时留在 `Plan` 修正，不进入 `PlanReview`。
- `record_plan_update`：记录 PlanReview 发现项、采纳/不采纳理由、是否 material change。
- `record_plan_approval`：记录批准状态、批准消息、`approved_plan_revision`、无效化原因和下一状态。
- `record_slice_transition`：切片进入、最小验证、完成或回流时更新切片状态（`slice_states`）。
- `spawn_plan_review_actor`：满足 `prompt_template_guard` 后，按 `references/delegation.md` 启动阻塞式方案审查子代理。
- `spawn_review_actor`：满足 `prompt_template_guard` 后，按 `references/delegation.md` 启动阻塞式实现审查子代理。
- `spawn_read_only_or_sidecar_actor`：满足 `prompt_template_guard` 后，按 `references/delegation.md` 启动只读审查或旁路子代理。
- `record_review_result`：按 `scope_compliance` 和 `implementation_quality` 记录 Review 发现项、审查 snapshot、影响状态和是否回流。
- `record_fix_findings`：记录修复或不采纳的发现项以及重审结果。
- `record_verification`：记录实际命令或完整目标范围、覆盖风险、未验证项和替代证据。
- `record_skipped_by_policy`：记录按策略跳过的 build、server 或浏览器验证命令、跳过原因和替代证据。
- `record_deliver_repair`：记录 `Deliver` 检查发现的待修项、分类、回流目标和旧批准是否失效。
- `record_rule_distillation`：记录规则沉淀检查结果：`not_needed`、`distilled` 或 `skipped`，以及依据和落点。
- `record_parked_blocker`：记录阻塞点、等待对象、解除后回到的状态。

## 切片子状态

```text
planned -> implementing -> min_verified -> complete
                         -> rework
```

- `planned`：片有目标、范围和最小验证。
- `implementing`：正在写入该片。
- `min_verified`：片内最小验证完成或缺口已记录。
- `complete`：片已合入当前方案，等待实现审查和全局验证。
- `rework`：审查、验证或用户反馈要求回流。

合并多个片实现或验证时，必须说明为什么不会掩盖失败归因。

## 验证记录

验证记录要能让交付回复可追溯：

- 已跑验证：实际命令，或命令名 + 完整目标范围 + 关键参数；说明覆盖的行为、contract 或风险。
- 未跑验证：具体行为或状态、预期结果、未跑原因、替代证据。
- 按策略跳过：具体命令或验证类型、跳过原因、替代证据；适用于用户未明确要求的 build、server 或浏览器验证。
- 失败验证：错误摘要、归因、回流到哪个状态、补跑结果。

不要把验证压成不可复跑摘要，例如只写“相关测试通过”或省略目标范围。

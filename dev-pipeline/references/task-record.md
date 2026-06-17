# 任务记录台账

任务记录用于保留实现模式的工作态。只在多步实现、长任务恢复、切片、方案批准、阻塞式子代理关卡、回流、搁置阻塞，或用户允许记录时，在 `.dev-pipeline/<date>-<short-slug>/` 记录状态机状态。

- **启用前先判定**：只读、`OffRamp`、单步低风险任务默认不创建任务记录。
- **重入先读回**：启用任务记录时先列 `.dev-pipeline/`，优先接续同目标目录。
- **一任务一目录**：`<date>` 用今天日期，`<short-slug>` 是任务的 kebab 短描述；目录内 `task.md` 是过程台账，`plan.md` 是用户批准物。
- **同名冲突**：同日同 slug 且目标一致时接续；目标不一致时追加 `-2`、`-3` 等后缀，不覆盖旧目录。
- **只依赖写文件**：不依赖宿主的 task/todo 工具；宿主恰好有 task 机制时可同步，但不作为依赖。
- **保持临时工作态**：绝不 commit；它是工作态，不是交付物。
- **按状态转移更新**：进入新状态、计划版本变化、批准状态变化、切片状态变化、`ContextGather` 证据包、`PlanReview` findings、`UpdatePlan`、`Review` findings、`FixFindings`、验证失败、阻塞搁置或回流时更新，不等最后补总结。

## `task.md` 模板

```markdown
# <任务一句话>

mode: OffRamp / ReadOnly / Implementation
current_state: Intake / Context / ContextGather / Plan / PlanReview / PlanApproval / UpdatePlan / Implement / ImplementSlice / Review / FixFindings / Verify / Deliver / WaitForUser / Parked
last_event: <触发当前状态的事件>
task_dir: .dev-pipeline/<date>-<short-slug>/
plan_file: .dev-pipeline/<date>-<short-slug>/plan.md
current_plan_revision: <hash / timestamp / monotonic id>
reviewed_plan_revision: <已通过 PlanReview 的 revision；无则 None>
approved_plan_revision: <用户已批准的 revision；无则 None>
approval_state: not_required / pending / approved / changes_requested / stale
approval_invalidated_reason: <material plan change / user requested change / none>

## 假设
- <未澄清就推进时做的假设> -> wrong_if: <错了要回头改什么>

## 守卫条件
- <守卫条件名称>：pass / fail / degraded；evidence <依据>
- 建议至少记录：`blocking_delegate_guard`、`context_pack_guard`、`plan_approval_guard`、`minor_note_guard`、`review_gate_guard`、`verification_guard`、`explicit_command_guard`。

## 上下文证据包
- source: context-gather / local-substitute / main-thread
- entry_points: <入口和文件/模块>
- contracts: <service/API/schema/type 边界>
- risks: <状态流、副作用、权限/数据流、用户可见风险>
- open_questions: <未解问题；无则写 None>

## 切片状态
- <片名>：planned / implementing / min_verified / complete / rework
  - goal: <端到端目标>
  - min_verification: <命令/路径/缺口>
  - notes: <回流、合并验证原因或风险>

## 子代理执行体
- <执行体 id 或 purpose>
  - purpose: <context-gather / plan-review / diff-review / verification / ...>
  - gate: <context / plan / review / none>
  - join_point: <before_plan / before_implement / before_verify / non_blocking>
  - max_impact: <context / plan / implement / verify / deliver>
  - blocking: yes/no
  - wait_policy: <wait_until_returned / unavailable_degrade_only / non_blocking>
  - status: pending / passed / findings / degraded / ignored
  - result: <结论、采纳情况、回流状态>

## 方案审查处理
- finding: <PlanReview finding>
  - disposition: adopted / rejected / already_covered
  - impact: material / minor
  - reason: <采纳/不采纳原因>
  - plan_revision_after: <更新后的 revision；未变则同 current_plan_revision>
  - next_state: PlanReview / PlanApproval / WaitForUser

## 方案批准
- state: not_required / pending / approved / changes_requested / stale
- current_plan_revision: <当前 plan.md revision>
- reviewed_plan_revision: <已审查通过 revision>
- approved_plan_revision: <已批准 revision；无则 None>
- approved_at: <用户批准的消息时间或 None>
- approved_message: <用户批准原话摘要；不要伪造>
- allowed_implementation_scope: <批准后允许写入的范围>
- side_effects_covered: yes/no；evidence <计划书是否逐项列明高副作用动作及用户批准是否覆盖>
- invalidated_by: <material plan change / user requested change / none>
- next_state: Implement / UpdatePlan / PlanApproval / WaitForUser

## 实现审查处理
- finding: <Review finding>
  - disposition: fixed / rejected / already_covered
  - affected_slice: <片名或 none>
  - evidence: <修复证据或不采纳理由>
  - next_state: Review / Verify / WaitForUser

## 已搁置阻塞
- <卡住什么（等谁/缺什么）> -> resume_state: <State>

## 验证记录
- verified:
  - command_or_scope: <实际命令，或命令名 + 完整目标范围 + 关键参数>
    covers: <覆盖的行为、contract 或风险>
- skipped_by_policy:
  - command_or_scope: <按策略跳过的 build/server/browser 验证命令或类型>
    reason: <用户未明确要求 build/server/browser；缺少端口/登录态/测试数据/停止策略等>
    substitute_evidence: <更窄验证、代码路径审查或未验证项>
- unverified:
  - behavior: <具体行为或状态>
    expected: <预期结果>
    reason: <未跑原因>
    substitute_evidence: <替代证据>
- failed:
  - command_or_check: <失败验证>
    cause: <实现 bug / 方案错 / 环境缺口 / 验证入口错>
    transition: <回流到哪个状态>
    rerun: <补跑结果>

## 状态转移
- <来源> --<事件>--> <目标>：<原因和依据>

## 交付检查
- final_diff_checked: yes/no
- verification_record_reflected: yes/no
- no_unowned_changes_claimed: yes/no
- commit_requested: yes/no
```

小任务可以省略空章节，但不能省略当前状态、关键守卫条件和实际验证结果。

## `plan.md` 模板

```markdown
# Plan: <任务一句话>

status: draft / reviewed / pending_approval / approved / superseded
revision: <hash / timestamp / monotonic id>
task_record: .dev-pipeline/<date>-<short-slug>/task.md

## 证据来源
- context_pack: <ContextGather / local substitute / main-thread>
- key_files: <关键文件、模块或 contract 引用>
- constraints: <repo instruction、README、ADR、用户点名规范>

## 当前行为
- <基于证据的当前行为>

## 目标行为
- <要交付的行为或文档结果>

## 改动范围
- <会改哪些模块、入口、contract 或文档>

## 不改动项
- <明确不做，防止范围漂移>

## Contract / 状态流 / 副作用
- contracts: <API/type/schema/service 边界>
- states: <允许状态、禁止状态、no-op、terminal behavior>
- side_effects: <谁拥有副作用、什么时候触发、是否需要额外确认>

## 纵向切片
- <slice name>
  - goal: <端到端目标>
  - files_or_modules: <预计触达范围>
  - min_verification: <最小验证入口>

## 风险
- <风险> -> mitigation: <控制方式>

## 验证计划
- <验证命令、范围或代码路径审查>

## 按策略跳过的验证
- <build/server/browser 等未被用户明确要求时写具体替代证据>

## 待批准事项
- <用户批准后允许执行的范围>
- <如包含高副作用动作，逐项列环境、范围、回滚/停止条件>
```

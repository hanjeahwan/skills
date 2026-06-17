# 任务记录台账

任务记录用于保留实现模式的工作态。只在多步实现、长任务恢复、切片、阻塞式子代理关卡、回流、搁置阻塞，或用户允许记录时，在 `.dev-pipeline/<date>-<short-slug>.md` 记录状态机状态。

- **启用前先判定**：只读、`OffRamp`、单步低风险任务默认不创建任务记录。
- **重入先读回**：启用任务记录时先列 `.dev-pipeline/`，优先接续已有记录。
- **一任务一文件**：`<date>` 用今天日期，`<short-slug>` 是任务的 kebab 短描述。
- **只依赖写文件**：不依赖宿主的 task/todo 工具；宿主恰好有 task 机制时可同步，但不作为依赖。
- **保持临时工作态**：绝不 commit；它是工作态，不是交付物。
- **按状态转移更新**：进入新状态、切片状态变化、`ContextGather` 证据包、`PlanReview` findings、`UpdatePlan`、`Review` findings、`FixFindings`、验证失败、阻塞搁置或回流时更新，不等最后补总结。

## 模板

```markdown
# <任务一句话>

mode: OffRamp / ReadOnly / Implementation
current_state: Intake / Context / ContextGather / Plan / PlanReview / UpdatePlan / Implement / ImplementSlice / Review / FixFindings / Verify / Deliver / WaitForUser / Parked
last_event: <触发当前状态的事件>

## 假设
- <未澄清就推进时做的假设> -> wrong_if: <错了要回头改什么>

## 守卫条件
- <守卫条件名称>：pass / fail / degraded；evidence <依据>
- 建议至少记录：`blocking_delegate_guard`、`context_pack_guard`、`minor_note_guard`、`review_gate_guard`、`verification_guard`。

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
  - next_state: PlanReview / Implement / WaitForUser

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

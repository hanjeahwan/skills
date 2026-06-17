# 执行计划（plan.md）

`plan.md` 是待批准执行计划。进入 `Plan` 时生成或更新，进入 `PlanReview` 时作为审查输入，进入 `PlanApproval` 时交给用户批准。

- **版本绑定**：每次 material plan change 后更新 `revision`，并同步 `task.md` 的 `current_plan_revision`。
- **审查绑定**：`PlanReview` 通过后，把 `reviewed_plan_revision` 记录到 `task.md`。
- **批准绑定**：只有用户明确批准当前 `revision`，才能把 `approved_plan_revision` 记录到 `task.md` 并进入 `Implement`。
- **批准失效**：目标行为、contract、状态流、副作用归属、验证策略或实现边界变化时，旧批准变为 stale，必须重新 `PlanReview` 和 `PlanApproval`。
- **高副作用动作**：`PlanApproval` 只授权按执行计划改文件；删除、部署、发送消息、批量联网改状态、付费调用等动作，必须在本执行计划逐项列明环境、范围、回滚/停止条件，且用户批准语明确覆盖。
- **质量自查**：高约束计划进入 `PlanReview` 前，必须确认需求已覆盖、无占位符、切片可执行且可验证、文件/边界/命名/验证计划具体；不满足时留在 `Plan` 修正。

## 模板

```markdown
# Plan: <任务一句话>

status: draft / reviewed / pending_approval / approved / superseded
revision: <hash / timestamp / monotonic id>
task_file: .dev-pipeline/<date>-<short-slug>/task.md

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

## 计划质量自查
- requirements_covered: yes/no；evidence <需求与目标行为是否逐项对应>
- no_placeholders: yes/no；evidence <无 TODO/TBD/待定/类似上一片/后续补充>
- slices_executable: yes/no；evidence <每片有目标、触达范围和最小验证入口>
- boundaries_named: yes/no；evidence <文件、contract、状态流、副作用归属清楚>
- verification_specific: yes/no；evidence <验证命令、范围或未验证项具体>

## 待批准事项
- <用户批准后允许执行的范围>
- <如包含高副作用动作，逐项列环境、范围、回滚/停止条件>
```

---
name: dev-pipeline
description: 用于高约束、多阶段的 repo 开发协作：先判定交付模式，再按状态机推进理解上下文、方案关卡、实现、验证、交付和回流。适用于代码实现、bug 排查、代码审查、重构、TDD/test-first、技术文档同步，以及多模块、状态流、外部 contract、副作用、权限/数据流、用户可见行为等高风险任务。只读模式不落盘，单文件低风险改动走轻量路径；单条命令、纯概念问答不使用。
---

# 通用开发流水线

用状态机组织 repo 开发：先定交付模式，再按状态、事件、守卫条件和动作推进；需要细节时先读 `references/resource-map.md`，再按地图选择具体参考文件。

## 关键边界

- 遇到 `plan only` / `review only` / `explain only`，本轮就是只读任务：不创建任务记录，不改文件，不 stage，不 commit。
- 提交保持显式授权：只有用户明确要求提交，或交付 diff 后确认提交，才按 repo 约定 commit；push 同理。
- 任务记录只用于多步实现、长任务恢复、切片、回流和已搁置阻塞；只读任务和单文件低风险任务默认跳过。
- 单文件低风险任务走轻量路径：不启动子代理、不切片、不建任务记录；需要解释时，用一句话说明跳过原因。
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

主干状态是：

```text
Intake -> Context -> Plan -> Implement -> Verify -> Deliver
```

常见分支和回流：

- `OffRamp`：单步问答直接结束。
- `ReadOnly`：只读模式；仍可走 Context/Plan 形成判断，不进 Implement。
- `WaitForUser`：高副作用、破坏性操作、关键信息缺失或用户确认门槛触发时停下。
- `Parked`：外部阻塞明确化，只推进与阻塞决策独立的工作，记录解除后回到哪个状态。
- `PlanReview`：高风险方案进入关卡；子代理不可用时在关卡内降级成本地替代审查。
- `ImplementSlice`：偏大任务按纵向片推进，每片独立实现和最小验证。
- `Rework`：验证或 reviewer 发现问题后按原因退回 Plan / Implement / Verify。

完整状态、事件、守卫条件、动作和退出条件见 `references/statechart.md`。

### 上下文

- 先读当前 repo 的约束来源：repo instruction files、README、docs、ADR、TODO、用户点名的规范文件。
- 改代码前收集上下文：现有工作流分支、相邻实现、service/API contract、数据流、控制流、命名模式、测试或验证入口。
- 涉及状态流或用户动作时，沿事件做守卫条件/副作用审查：允许状态、禁止状态、no-op 行为、缺失守卫条件、副作用归属、终止行为，以及测试/文档是否覆盖当前行为。
- 重构、迁移、架构调整这类高风险工作，按 `references/refactor-prep.md` 准备。

### 方案

- 大改前先分享方案：当前行为、目标行为、改动范围、保持不变的行为、风险、验证计划。
- 任务偏大时，方案里切纵向片：每片是一条薄的端到端改动，有明确验证入口。
- 命中高风险守卫条件时进入 `PlanReview`：按 `references/delegation.md` 声明子代理执行体的 `purpose`、`join_point`、`max_impact` 和 `timeout_behavior`；子代理不可用或超时时，在关卡内完成本地替代审查降级。
- `ReadOnly` 在此交付方案或审查结论即止。`Implementation` 只有在守卫条件都满足时进入 Implement。

### 实现

- 范围以本轮目标为边界：只纳入完成目标必需的相邻流程、入口校验、交互策略、持久化、运行期副作用和数据模型变化。
- 已切片时进入 `ImplementSlice`：片状态随状态转移更新为 `planned`、`implementing`、`min_verified`、`complete` 或 `rework`。
- 实现规则见 `references/implementation.md`；调试、TDD、文档等分支按下方分支模式加载对应参考文件。

### 验证

- 修改后走检查清单：命名、重复状态、非法状态、数据来源是否唯一、副作用归属、事件守卫条件、boolean 前缀、范围是否漂移、可读性、验证是否足够。
- 按验证选择矩阵执行；没做的验证要明确说。
- 验证发现实现 bug -> 回 Implement；发现需求/方案理解错 -> 回 Plan；发现验证覆盖不足 -> 留在 Verify 补验证或记录缺口。

### 交付

- 检查最终 diff、旧命名、重复状态、工作区 dirty、导出命名和 `git diff --check`。
- 任务记录启用时，最终回复从验证记录和当前 diff 生成；交付回复保留可复跑的验证依据。
- 仅在用户明确要求提交，或交付 diff 后用户确认提交时，才 commit；不 push，除非用户明确要求。
- 交付后若被用户纠正，按 `references/rule-distillation.md` 沉淀可复用规则。

## 分支模式

按触发词切入对应分支，只加载需要的参考文件：

- **代码审查** — 触发：`review`、`code review`、`看 diff`、`审这个 PR`。只读，不进 Implement。加载 `references/code-review.md`。
- **调试** — 触发：报 bug、行为异常、排查、`debug`。加载 `references/debugging.md`。
- **测试驱动** — 触发：`TDD`、`test-first`、`red-green-refactor`。加载 `references/tdd.md`。
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

### 任务记录

- 启用任务记录时，先列 `.dev-pipeline/`；有本任务记录就接续，没有再新开。
- 任务记录是记录台账：记录 `current_state`、切片状态、`delegate_states`、已搁置阻塞、验证记录和回流历史。
- 只依赖写文件，不依赖宿主的 task 工具；保持临时工作态，绝不 commit。
- 模板和更新规则见 `references/task-record.md`。

### 子代理委派

- 把子代理作为状态机里的执行体管理：启动前先定义目的、等待点、影响范围和超时策略。
- 命中高风险守卫条件且有独立审查/验证价值时默认启动，或进入本地替代审查降级；未启动必须记录低风险、强耦合、工具失败或安全边界原因。
- 启动前必须声明 `purpose`、`join_point`、`max_impact`、`timeout_behavior`；没有 `join_point` 的子代理不启动。
- 关卡执行体未满足前不能越过对应状态；降级越过时必须记录本地替代审查。
- 细节和发现协议见 `references/delegation.md`。

### 验证选择矩阵

- 行为改动：优先跑覆盖该行为的定向测试；没有测试时做手动路径验证并说明缺口。
- 前端可视行为：浏览器冒烟不是默认硬要求。只有本地路由、登录态、测试数据和浏览器工具都可用且成本合理时才执行；否则用更窄验证替代，并列出未验证的具体交互。
- 类型、schema、API contract 改动：跑 typecheck 或最接近的静态检查，并检查调用点。
- `build` 和全量检查属于高成本验证；只有构建 artifact / 打包产物是交付物、用户明确要求，或没有更窄验证能覆盖关键编译风险时才跑。
- 文档改动：对照事实来源核对命令、路径、术语和示例，不默认跑全量测试。

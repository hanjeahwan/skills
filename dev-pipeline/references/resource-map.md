# dev-pipeline 资源地图

按需读取，不要为了完整性一次性加载所有文件。

## 入口与模式

- `entry-modes.md`：用户请求有边界问题时读取，例如 `plan only`、`review only`、重构默认先出方案、上一轮建议被接受、是否等待确认。
- `task.md`：只有需要启用 `.dev-pipeline/<date>-<short-slug>/task.md` 任务台账时读取；记录 current_state、子代理执行体状态、计划版本、用户批准、切片、发现项、回流和验证。只读模式、`OffRamp`、单文件低风险任务默认不需要。
- `plan.md`：进入 `Plan` / `PlanReview` / `PlanApproval`，需要生成或更新 `.dev-pipeline/<date>-<short-slug>/plan.md` 时读取；记录执行计划模板、revision、审批语义和高副作用批准边界。

## 主干阶段细节

- `statechart.md`：阻塞式状态机来源。需要理解 `ContextGather -> Plan -> PlanReview -> PlanApproval -> Implement -> Review -> Verify -> Deliver -> RuleDistill`、状态转移、守卫条件、动作、退出条件，或处理回流、子代理 `join_point`、计划批准、验证记录、规则沉淀时读取。
- `implementation.md`：进入 `Implement` 写代码时读取，覆盖单一事实来源、状态机建模、阶段边界和命名规则。
- `refactor-prep.md`：重构、迁移、架构调整，或涉及多模块/状态流/外部 contract、副作用、权限/数据流/用户可见行为时读取。
- `rule-distillation.md`：进入 `RuleDistill`，或交付前发现用户纠正、审查/测试/子代理结果暴露可复用决策偏差，需要判断是否沉淀成持久规则时读取。

## 分支流程

- `code-review.md`：用户要求 review、code review、看 diff、审 PR 时读取，只读不进 `Implement`。
- `debugging.md`：用户报告 bug、行为异常、排查或 debug 时读取。
- `tdd.md`：用户明确要求 TDD、test-first、red-green-refactor、test-first integration coverage，或业务状态流、API mapper/schema、权限/计费/保存/发布/删除、可复现 bug、多 boolean/enum 状态等高风险行为且项目已有可维护 test harness 时读取。普通 integration tests 不自动触发 TDD。
- `docs.md`：改 README、ADR、技术说明或同步技术文档时读取。

## 子代理委派

- `delegation.md`：任务命中子代理委派触发条件，或需要判断阻塞式关卡 / `non_blocking` 旁路执行体、是否应跳过启动子代理时读取。
- `prompts/*.md`：启动任何子代理前的必经步骤。这里的 `prompts/` 是本文件旁边的 `./prompts/`，即 `<skill-root>/references/prompts/`；每个模板文件的 H1 和 `触发：` 行是唯一注册信息。先列文件，读每个文件头部的 H1 和 `触发：` 行，只加载匹配模板，并把结果记录为 `prompt_source` 和 `prompt_basis`。

## 评估与宿主信息

- `../evals/evals.json`：修改触发、状态机守卫条件、子代理委派、任务台账、commit 或交付规则后读取并补少量回归用例。
- `../agents/openai.yaml`：只在调整宿主界面展示文案时读取；它不是执行规则来源。

# dev-pipeline 资源地图

按需读取，不要为了完整性一次性加载所有文件。

## 入口与模式

- `entry-modes.md`：用户请求有边界问题时读取，例如 `plan only`、`review only`、重构默认先出方案、上一轮建议被接受、是否等待确认。
- `scratch-pad.md`：只有需要启用 `.dev-pipeline/` 工作态记录时读取；只读模式、off-ramp、单文件低风险任务默认不需要。

## 主干阶段细节

- `implementation.md`：进入 Stage 3 写代码时读取，覆盖单一事实来源、状态机建模、phase boundaries 和命名规则。
- `refactor-prep.md`：重构、迁移、架构调整，或涉及多模块/状态流/外部 contract/side effects/权限数据流/用户可见行为时读取。
- `feedback-capture.md`：交付后被用户纠正，或 review/test/subagent 结果暴露可复用决策偏差时读取。

## 分支流程

- `code-review.md`：用户要求 review、code review、看 diff、审 PR 时读取，只读不进 Stage 3。
- `debugging.md`：用户报告 bug、行为异常、排查或 debug 时读取。
- `tdd.md`：用户明确要求 TDD、test-first、red-green-refactor，或行为风险高且项目已有可维护 test harness 时读取。
- `docs.md`：改 README、ADR、技术说明或同步技术文档时读取。

## 委派

- `delegation.md`：任务命中委派触发条件，或需要判断是否应跳过委派时读取。
- `prompts/*.md`：只在真正启动子代理/委派时按发现协议读取。先列文件，读每个文件头部的 H1 和 `触发：` 行，再只加载匹配的一个模板。

## 评估与宿主信息

- `../evals/evals.json`：修改触发、写入门槛、委派、任务记录、commit 或交付规则后读取并补回归用例。
- `../agents/openai.yaml`：只在调整宿主界面展示文案时读取；它不是执行规则来源。

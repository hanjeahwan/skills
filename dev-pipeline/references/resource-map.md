# dev-pipeline 资源地图

按需读取，不要为了完整性一次性加载所有文件。

## 入口与模式

- `entry-modes.md`：用户请求有边界问题时读取，例如 `plan only`、`review only`、重构默认先出方案、上一轮建议被接受、是否等待确认。
- `scratch-pad.md`：只有需要启用 `.dev-pipeline/` 工作态记录时读取；只读模式、off-ramp、单文件低风险任务默认不需要。

## 主干阶段细节

- `implementation.md`：进入 Stage 3 写代码时读取，覆盖单一事实来源、状态机建模、phase boundaries 和命名规则。
- `refactor-prep.md`：重构、迁移、架构调整，或涉及多模块/状态流/外部 contract/side effects/权限数据流/用户可见行为时读取。
- `rule-distillation.md`：交付后被用户纠正，或 review/test/子代理结果暴露可复用决策偏差，需要沉淀成持久规则时读取。

## 分支流程

- `code-review.md`：用户要求 review、code review、看 diff、审 PR 时读取，只读不进 Stage 3。
- `debugging.md`：用户报告 bug、行为异常、排查或 debug 时读取。
- `tdd.md`：用户明确要求 TDD、test-first、red-green-refactor，或行为风险高且项目已有可维护 test harness 时读取。
- `docs.md`：改 README、ADR、技术说明或同步技术文档时读取。

## 子代理委派

- `delegation.md`：任务命中子代理委派触发条件，或需要判断是否应跳过启动子代理时读取。
- `prompts/*.md`：只在真正启动子代理时按发现协议读取。先列文件，读每个文件头部的 H1 和 `触发：` 行，再按下面地图只加载匹配模板：
  - `prompts/context-manager.md`：上下文分散，需要先把 repo 证据、入口、约束、风险和未解问题打包给后续工作时选。
  - `prompts/codebase-orchestrator.md`：repo 级重构、迁移或架构治理，需要风险排序、影响面和提案关卡时选。
  - `prompts/architect-reviewer.md`：需要审查耦合、系统边界、数据归属、长期可维护性或设计连贯性时选。
  - `prompts/reviewer.md`：需要独立审查代码/diff 的正确性、安全、行为回归或缺测试时选。
  - `prompts/security-auditor.md`：改动涉及 auth、密钥/敏感数据、输入校验、加密、网络/配置暴露或供应链依赖时选。
  - `prompts/error-coordinator.md`：多个错误/症状需要分组、定位主故障、排出排查顺序时选。
  - `prompts/knowledge-synthesizer.md`：多个子代理返回发现项，需要去重、保留冲突并形成决策视图时选。

## 评估与宿主信息

- `../evals/evals.json`：修改触发、写入门槛、子代理委派、任务记录、commit 或交付规则后读取并补回归用例。
- `../agents/openai.yaml`：只在调整宿主界面展示文案时读取；它不是执行规则来源。

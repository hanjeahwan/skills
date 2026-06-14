# 重构准备清单（Stage 1 前置）

涉及多个模块、状态流、外部 contract、side effects、权限/数据流或用户可见行为的重构前，在主干 Stage 1 之前准备这些内容：

- 当前工作流：入口、分支、terminal states、side effects。
- 问题：具体 bug、维护性问题或行为风险。
- 状态质量：非法状态、重复状态、派生状态、单一事实来源，以及 boolean 组合是否会漂移。
- 事件审查：逐个 event/action 列出允许状态、禁止状态、no-op 行为、missing guard、terminal behavior，以及 guard 与 tests/docs 是否一致。
- 副作用归属：每个 side effect 由谁触发、何时触发、成功/失败事件如何回到状态流；异步结果是否可能覆盖较新的状态。
- 方案边界：状态模型、service 边界、public API 保持/拆分边界或 ownership。
- 范围：会改哪些文件，哪些文件明确不改。
- 行为保持：哪些现有行为必须不变。
- 文档影响：README、ADR、技术说明是否需要同步；只记录真实已实现行为，不把计划写成事实。
- 验证计划：按主干验证选择矩阵选择入口。
- 灰色地带：需要业务或后端确认的点。

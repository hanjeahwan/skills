# 子代理执行体生命周期

把子代理作为状态机里的执行体管理：启动前先定义目的、等待点、影响范围和超时策略。
调用宿主能力时保留触发语义：`spawn subagents` / `delegate` / `subagent workflows` / `parallel agent work`。

## 启动条件

命中任一高风险守卫条件，且存在边界清楚的只读审查或独立验证时，默认启动子代理；工具失败、平台规则不允许调用或安全边界冲突时，进入本地替代审查降级：

- 多模块或跨边界改动。
- 状态流、权限/数据流、副作用、外部 contract 或用户可见行为变化。
- 有可独立审查的 diff、方案或验证计划。
- 多个发现项需要去重、保留冲突并形成决策视图。

单文件低风险、强耦合设计判断、需要连续用户交互、或当前上下文必须由主线程直接决定时，不启动；用一句话或任务记录说明低风险、强耦合、工具失败或安全边界原因。

## 执行体契约

每次启动前先声明：

```text
purpose: plan-review | diff-review | security-review | architecture-review | verification | synthesis | sidecar-research
join_point: before_stage_3 | before_stage_5 | non_blocking
max_impact: stage_2 | stage_3 | stage_4 | deliver
timeout_behavior: wait | degrade_with_local_review | continue_as_sidecar
```

- `purpose`：为什么启动。没有明确目的不启动。
- `join_point`：它挡哪个门。没有等待点不启动。
- `max_impact`：它最多能让主线程回流到哪里，避免晚到结果无限推翻。
- `timeout_behavior`：超时后等待、降级本地审查，或转为非阻塞旁路任务。

按等待点区分关卡执行体和旁路任务：

- `before_stage_3`：计划关卡。未返回或未降级前不能进入实现。
- `before_stage_5`：交付关卡。未返回或未降级前不能最终交付。
- `non_blocking`：旁路探索。主线程可以继续，但必须记录 `max_impact`；返回后只在影响范围内决定是否回流。

## 发现协议

启动子代理时不查中心表，按约定发现模板：

1. 列出本文件旁边的 `./prompts/`，即 `<skill-root>/references/prompts/`。
2. 读每个文件头部的 H1 和 `触发：` 行。
3. 只加载匹配的一个模板，把模板全文和本次具体输入喂给子代理。
4. 没有匹配模板时，现写任务说明，但必须包含只读边界：禁止 Edit/Write/revert/stage/commit/push，只回结论。

不要点名宿主注册的 agent、subagent_type、agent 路径或模型；使用当前宿主的子代理启动机制。

## 常见执行体

| 执行体 | join_point | max_impact | 适用场景 |
| --- | --- | --- | --- |
| `plan-review` | `before_stage_3` | `stage_2` | 高风险方案进入实现前审查范围、contract、状态流和验证计划 |
| `diff-review` | `before_stage_5` | `stage_3` | 交付前独立审查 diff 正确性、行为回归和缺测试 |
| `security-review` | `before_stage_5` | `stage_2` 或 `stage_3` | auth、密钥、敏感数据、输入校验、网络/配置暴露 |
| `architecture-review` | `before_stage_3` | `stage_2` | 架构边界、耦合、数据归属、长期维护性 |
| `verification` | `before_stage_5` | `stage_4` | 并行跑独立验证或审查验证覆盖 |
| `synthesis` | `non_blocking` 或 `before_stage_5` | `stage_4` | 多个子代理结果需要去重、保留冲突和决策汇总 |

## 计划审查关卡

Stage 2 方案命中高风险守卫条件时，启动 `plan-review` 关卡或记录降级原因。

计划审查至少覆盖四个视角中与任务相关的部分：

- 行为回归与范围漂移。
- 状态流与副作用。
- contract 与边界。
- 验证充分性。

如果子代理工具失败、平台规则不允许调用、或安全边界冲突，主线程做本地替代审查，并在任务记录或回复中写明降级原因。

## 结果处理

执行体返回后先看契约：

- 结果在 `max_impact` 内且有效：回流到对应状态，或补验证/修实现。
- 结果已被后续改动覆盖：记录证据，不回流。
- 结果与 repo 事实不符：记录不采纳理由，不回流。
- 执行体超时：按 `timeout_behavior` 处理；关卡降级必须有本地替代审查。

影响切片时，更新切片状态；影响验证时，更新验证记录。

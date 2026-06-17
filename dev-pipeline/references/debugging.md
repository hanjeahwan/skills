# 调试分支

报 bug、行为异常、排查、`debug` 时切入。低风险诊断可走轻量 `Context`；需要写入且命中高约束门槛时，沿主干 `ContextGather -> Plan -> PlanReview -> PlanApproval -> Implement` 推进。本分支额外遵循：

- 先用复现、数据流、日志或调用链把根因收敛到有证据支撑的假设。
- 用户指出 demo、相邻实现或历史行为时，先比较差异，再下结论。
- 只加窄诊断；确认原因后，决定移除还是保留。
- 用户观测和假设冲突时，丢掉假设，重新检查工作流。
- 对异步流程要追真实顺序：event emission、side effect、state transition、finalize、retry path。
- 修 bug 前先判断它属于哪个 phase 或边界，避免在错误层修症状。

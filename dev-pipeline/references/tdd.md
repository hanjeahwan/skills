# Test-Driven Development 分支

用户明确要求 TDD、test-first、red-green-refactor、integration tests，或任务行为风险高且当前项目已有可维护 test harness 时切入。该分支改写主干 Stage 3 的节奏。

- 默认不进入 TDD 模式。
- 如果当前项目已有明确的 TDD 流程、测试命令或测试工具链，优先按项目方式执行 red-green-refactor。
- 如果没有明确的项目 TDD 流程，按轻量 TDD 协议执行：一次只写一个测试，只测 public interface 的可观察行为，先 RED，再写最小实现到 GREEN，全部通过后才 refactor。
- 不要 horizontal slicing：不要一次写完所有测试再实现。
- 如果行为 contract 已清楚，直接列出第一个要验证的行为并实现一个最小可验证路径；如果不清楚，只问一个关键问题。
- 如果项目没有可维护 test harness，不要硬造测试体系；说明测试缺口，改用 targeted static check、现有验证命令或手动路径验证。

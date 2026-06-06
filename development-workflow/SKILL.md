---
name: development-workflow
description: 用于开发任务中的上下文收集、方案确认、实现、验证和交付；适用于代码修改、调试、重构、代码审查和技术文档更新。
---

# 通用开发协作流程

使用这个 skill 时，把自己当作与用户结对的资深工程师：先理解现有系统，再提出可执行方案，最后完成实现和验证。这个 skill 是通用协作流程，不包含任何特定框架、公司或项目规则。

## 沟通方式

- 遵守当前系统、用户和 repo 的语言政策；没有明确约定时，保持简洁清晰。
- 开门见山，先给结论，再解释机制和取舍。
- 用真实用户场景说明问题为什么重要，再解释技术机制。
- 不要把用户拉进不必要的输入请求；能从代码和文档判断时直接推进。
- 如果方案有风险，说明具体故障模式：什么会坏、谁承担代价、什么时候爆发。
- 用户说 `review` 时，进入代码审查模式：先列发现的问题，文件/行引用清楚，避免低信号猜测。

## 通用工作流

1. 先读当前 repo 的约束来源，例如 repo instruction files、README、docs、ADR、TODO、用户点名的规范文件。
2. 改代码前先收集上下文：现有工作流分支、相邻实现、service/API contract、数据流、控制流、命名模式、测试或验证入口。
3. 大改前先分享方案：当前行为、目标行为、改动范围、保持不变的行为、风险、验证计划。
4. 用户要求或工作流敏感的重构时，如果当前环境提供 subagent 或 multi-agent 工具，用它们独立审查方案或 diff；如果没有可用工具，自己做第二轮审查，并在最终回复说明没有使用 subagent。
5. 实现时保持范围窄。不要把相邻流程、入口校验、交互策略、持久化、运行期副作用、数据模型扩展一起带进来，除非任务明确包含。
6. 修改后走一遍检查清单：命名、重复状态、source of truth、boolean 前缀、范围是否漂移、可读性、验证是否足够。
7. 交付前按风险跑验证：优先 targeted lint、typecheck、tests、diff check 或手动路径验证。`build` 主要验证编译/打包边界，不是默认行为验证；只有改到依赖/配置、编译边界、模板类型、打包产物或用户明确要求时才跑。没做的验证要明确说。

## 项目适配规则

- 不要在这个 skill 里假设框架或项目技术栈。
- 如果当前 repo 有本地说明、framework skill、company skill、pattern docs 或 ADR，优先加载并遵守它们。
- 涉及外部库、框架、SDK、协议或 API 签名时，先查当前项目依赖、类型定义、官方文档或用户指定来源。
- API contract 以实际 types、services、schemas 和调用点为准。不要发明字段、状态或 policy object。
- 跨模块边界先按当前项目既有实践判断，例如路由、状态管理、UI、HTTP、数据库、CLI、队列或其它适用边界；不要套用别的 repo 的习惯。

## 调试规则

- 不要脑补根因。先复现、追踪数据流，或对照日志/调用链验证。
- 用户指出 demo、相邻实现或历史行为时，先比较差异，再下结论。
- 只加窄诊断；确认原因后，决定移除还是保留。
- 用户观测和假设冲突时，丢掉假设，重新检查工作流。
- 对异步流程要追真实顺序：event emission、side effect、state transition、finalize、retry path。
- 修 bug 前先判断它属于哪个 phase 或边界，避免在错误层修症状。

## Test-Driven Development 模式启用与执行

- 默认不进入 TDD 模式。
- 当用户明确要求 TDD、test-first、red-green-refactor、integration tests，或任务行为风险高且当前项目已有可维护 test harness 时，进入 TDD 模式。
- 如果当前环境有可用的 TDD helper skill/tool，优先使用它执行完整 red-green-refactor。
- 如果没有可用的 TDD helper skill/tool，按轻量 TDD 协议执行：一次只写一个测试，只测 public interface 的可观察行为，先 RED，再写最小实现到 GREEN，全部通过后才 refactor。
- 不要 horizontal slicing：不要一次写完所有测试再实现。
- 如果行为 contract 已清楚，直接列出第一个要验证的行为并开始 tracer bullet；如果不清楚，只问一个关键问题。
- 如果项目没有可维护 test harness，不要硬造测试体系；说明测试缺口，改用 targeted static check、现有验证命令或手动路径验证。

## 实现规则

- canonical domain object 是 source of truth。不要为了方便镜像成多个平行属性，除非它们有独立 lifecycle 或缓存价值。
- 不要加 getter/setter 做简单派生。
- 避免冗余 props、冗余 methods、冗余 snapshots；已有 helper 能表达同一数据时直接复用。
- 不要为了防御理论上不存在的状态到处 throw error；先确认现有工作流是否保证数据存在。
- 类型和接口默认靠近使用点；只有跨边界共享时才 export。
- 命名要表达 domain，不要用泛化或测试语义污染业务概念。
- boolean flags 用 domain predicate 前缀：`is...`、`has...`、`can...`、`should...`。
- 符号命名要有明确作用域但不冗余；目录或 feature 已表达的上下文，不要在文件名和类型名里重复堆叠。
- 复杂流程优先抽出明确 phase/state model，不要散落多个 boolean 互相推断。
- 当代码和工作流变复杂、同时存在多阶段 state、event、side effects、retry 或 terminal states 时，优先使用 state controller / state machine 思路处理，例如 statechart 风格：显式定义 states、events、transitions、guards 和 effects。先遵守当前 repo 既有状态管理工具；不要为了简单流程强行引入新依赖。
- 保持 phase boundaries。不要把用户动作、入口校验、刷新/重载、运行期副作用、persistence、交互策略混在一起，除非任务明确包含。

## 重构独立审查模式

非平凡重构前，准备这些内容：

- 当前工作流：入口、分支、terminal states、side effects。
- 问题：具体 bug、维护性问题或行为风险。
- 方案边界：状态模型、service 边界或 ownership。
- 范围：会改哪些文件，哪些文件明确不改。
- 行为保持：哪些现有行为必须不变。
- 验证计划：静态验证、自动测试、手动路径或浏览器验证。
- 灰色地带：需要业务或后端确认的点。

如果当前环境提供 subagent 或 multi-agent 工具，给它原始方案或 diff，不要泄露预期答案。外部审查提出的 required changes 必须跟进。

如果当前环境没有 subagent 工具，不要假装已经做过外部审查。改为自己做第二轮审查：重新检查工作流分支、状态边界、命名、重复状态、验证计划，并在最终回复说明未使用 subagent 的原因。

## 交付前检查

- 检查最终 diff。
- 搜索旧命名、旧 boolean flags 和重复状态。
- 确认没有 revert 用户改动。
- 确认新文件名和 exported symbols 有明确作用域但不冗余。
- 跑 `git diff --check`。
- 根据风险跑 targeted lint、typecheck、tests、diff check 或手动路径验证；不要默认 build，除非这次改动真的需要验证编译/打包边界。
- 最终回复说明改了什么、验证了什么、还有什么没验证。

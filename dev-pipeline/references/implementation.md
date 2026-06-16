# 实现规则（Stage 3 深度）

进入实现模式、在主干 Stage 3 写代码时遵循这些规则。

- 以当前项目认可的核心领域对象作为唯一事实来源；只有存在独立 lifecycle 或明确缓存价值时，才拆出平行状态。
- 不要加 getter/setter 做简单派生。
- 避免冗余 props、冗余 methods、冗余 snapshots；已有函数或组件能表达同一数据时直接复用。
- 不要为了防御理论上不存在的状态到处 throw error；先确认现有工作流是否保证数据存在。
- 类型和接口默认靠近使用点；只有跨边界共享时才 export。
- 命名要表达 domain，不要用泛化或测试语义污染业务概念。
- boolean flags 用 domain predicate 前缀：`is...`、`has...`、`can...`、`should...`。
- 符号命名要有明确作用域但不冗余；目录或 feature 已表达的上下文，不要在文件名和类型名里重复堆叠。

## 状态机建模

- 当流程出现多个阶段、用户事件、异步 side effects、retry、terminal states，或多个 boolean 互相推断时，先用 statechart 思路建模：列出 states、events、transitions、guards、effects 和不可达状态。默认先作为分析和重构方案，不要直接引入状态机库。
- 如果现有实现已经因为 boolean 组合、分支散落或副作用顺序导致维护风险，建议用户把实现重构成 statechart-like 结构，例如 reducer、transition table 或 state controller；优先沿用当前 repo 的状态管理工具，只有 repo 已有状态机实践或复杂度明确需要时，才考虑引入状态机库。

## Phase boundaries

- 保持 phase boundaries。不要把用户动作、入口校验、刷新/重载、运行期副作用、persistence、交互策略混在一起，除非任务明确包含。

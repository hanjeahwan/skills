# dev-pipeline

`dev-pipeline` 是高约束工程流水线 skill，用于需要读取 repo 上下文、跨阶段推进并交付验证结果的开发任务。它面向 agent 执行多步工程工作，不是通用聊天、单命令查询或低风险单文件改动的默认包装器。

## 适用场景

- 代码实现、bug 调试、重构、代码审查、TDD/test-first、技术文档同步。
- 涉及多模块、状态流、外部 contract、side effects、权限/数据流或用户可见行为的任务。
- 需要明确经历理解上下文、方案、实现、验证、交付这些阶段的工作。

## 默认边界

- `plan only` / `review only` / `explain only` 保持只读，不创建任务记录，不改文件，不 stage，不 commit。
- 单文件低风险任务走轻量路径，不强行委派、不切片、不创建任务记录。
- 默认不 commit。只有用户明确要求提交，或交付 diff 后确认提交，才允许 commit；默认不 push。
- 删除、覆盖、迁移、部署、发送消息、批量写入、联网改状态、付费调用等高副作用操作必须先确认。

## 目录结构

- `SKILL.md`：agent 执行规则和主流水线，是唯一的运行时入口。
- `references/`：按需加载的细节规则，入口索引见 `references/resource-map.md`。
- `references/prompts/`：委派 prompt 模板，通过每个文件的标题和 `触发：` 行自描述。
- `evals/evals.json`：行为型回归用例，用来验证加载本 skill 后是否按规则行动。
- `agents/openai.yaml`：宿主界面展示信息，不承载执行规则。

## 维护原则

- 先改 `SKILL.md` 的门槛，再同步相关 reference，避免主规则和细节规则打架。
- 新增参考文件时，从 `SKILL.md` 或 `references/resource-map.md` 直接可发现，不做深层跳转。
- 新增高风险规则时，同时补回归用例，尤其是写文件、commit、委派和只读模式边界。

# Test-Driven Development 分支

TDD 是进入 `Implement` 后的实现节奏，不改变主状态机、不跳过 `PlanApproval`、不强制创建任务台账。只有已启用任务台账时，才把 RED/GREEN/REFACTOR 过程写入 `task.md`；轻量任务在最终验证记录说明。

## 触发

满足任一条件时切入：

- 用户明确要求 TDD、test-first 或 red-green-refactor。
- 用户明确要求 test-first integration coverage。普通 integration tests 不自动等于 TDD；若这类验证需要 build、server、browser 或外部服务，仍受 `explicit_command_guard` 约束。
- 行为风险高且当前项目已有可维护 test harness：业务状态流、API payload/mapper/serializer/schema、权限/计费/保存/发布/删除、可复现 bug、多 boolean/enum 状态，或有稳定输入输出 contract 的 helper/util/domain logic。

默认不进入 TDD。文档、纯样式/layout、纯 rename/format/dead code、探索 spike，或没有可维护 test harness 时，不硬造测试体系；说明测试缺口，改用 targeted static check、现有验证命令或代码路径审查。

## 节奏

- **RED**：先写一个最小行为测试，失败原因必须是目标行为缺失。直接 pass、fixture 错、语法错或测试环境错误不算 RED。
- **GREEN**：只写让该测试通过的最小实现，不顺手扩大范围。
- **REFACTOR**：green 后再清理命名、结构或重复，并重跑相关验证。
- 一次只推进一个可观察行为；优先通过 public interface 验证。
- 如果行为 contract 不清楚，先问一个会改变测试目标的关键问题。

## 测试质量

- 测真实行为和可观察结果，不测 mock 是否被调用这种实现细节，除非调用本身就是 contract。
- 不为测试暴露 production-only API，不用 `any`、禁用 lint 或跳过检查隐藏问题。
- 先理解 side effect owner，再决定 mock 边界。
- mock data 必须匹配真实消费结构，避免测试过了但 runtime 路径仍错。

## 已先写实现时

- 不能宣称已经 TDD。
- 已启用切片时，把对应片标成 `rework`，补 RED 后再回 GREEN。
- 轻量任务则回到实现步骤重做 test-first，或明确记录为非 TDD 并走普通验证。

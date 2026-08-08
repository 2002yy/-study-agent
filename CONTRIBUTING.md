# Contributing

## 基本要求

- 当前进度只更新 `docs/PROJECT_STATUS.md`。
- 架构 owner 变更同步 `docs/ARCHITECTURE.md`。
- 领域语义变更同步 `domain_models.md`；硬约束同步 `state_invariants.md`。
- 不新增并列长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT。
- 实现未落地的设计必须明确标为 contract/planned，不能写成 shipped。
- 删除 product surface 前必须证明 route/UI/CSS/DOM class/compat/runtime owner 均已退场。
- 新功能必须配回归/失败边界/人工验收；优先测试 invariant，而不是偶然 UI 文本。

详细测试策略见 `docs/TESTING.md`，文档索引见 `docs/README.md`。

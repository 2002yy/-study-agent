# Study Agent

> **个人学习工作台**：长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”。
>
> 当前进度唯一入口：[`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)。

Study Agent 不是把聊天记录长期堆积起来的 Chatbot，也不是让多个角色各自维护一套“记忆真相”的角色扮演系统。当前产品主线是把学习过程收敛为可恢复、可验证、可追溯的学习状态：

```text
教学 / 练习
→ 资料与证据
→ 理解验证
→ 已确认 / 未解决
→ 下一步
→ 整理、恢复与继续学习
```

## 当前运行时

```text
React
  ↓
FastAPI
  ↓
Application Runtimes
├─ EvidenceRuntime
├─ LearningSessionRuntime
└─ ExtensionRuntime
  ↓
SQLite durable entities
```

- **React**：当前交互面。
- **FastAPI**：生产 API 与应用服务入口。
- **SQLite durable entities**：运行时事实来源。
- **EvidenceRuntime**：RAG、上传、外部研究、源码证据与恢复端口。
- **LearningSessionRuntime**：会话、聊天、学习设置、记忆、LearningClosure 与学习恢复。
- **ExtensionRuntime**：群聊、受控工具、工作流等实验能力；普通模式只通过单一 Lab 入口访问。

详细 owner 边界见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。

## P2-D：源码学习与验证

2026-08-08 已冻结源码学习的领域语义合同，但**不等于全部已经实现**。核心原则：

- `SourceEvidence` 固定到 exact commit / file / symbol / line，不被 CI 临时状态污染；
- CI 是独立的 `ValidationObservation`，失败或不可用不自动使源码证据失效；
- `LearningClaim` 使用受限 EvidenceSet：1 个 Primary + 0–4 个 Supporting；
- 用户掌握、源码 freshness、记忆 retention 是三个不同维度；
- 没有可靠 Primary Evidence 时只能形成 `LearningHypothesis`，不能伪装成正式 Claim；
- Persona 只改变教学表达，不改变 truth、evidence、mastery 或 freshness；
- GitHub / RAG / Web 都是 Evidence Provider，不存在全局“来源优先级”。

完整合同见 [`domain_models.md`](domain_models.md) 与 [`state_invariants.md`](state_invariants.md)。

## 产品面

普通用户稳定入口：

- 学习会话；
- 资料与来源；
- 学习成果；
- 设置。

实验能力：

- 群聊；
- 受控工具；
- 开发者诊断。

实验能力统一从 **Lab** 进入，默认休眠。旧 News 独立产品面与旧 Extension drawer 兼容 surface 已退出；仍保留的 durable workflow / capability 不等于独立产品面。

## 文档入口

| 需要了解 | 入口 |
|---|---|
| 当前做到哪里、下一步做什么 | [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) |
| 文档治理与完整索引 | [`docs/README.md`](docs/README.md) |
| 当前架构与 owner | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| 领域对象与生命周期 | [`domain_models.md`](domain_models.md) |
| 必须永远成立的规则 | [`state_invariants.md`](state_invariants.md) |
| 状态持久化/临时状态边界 | [`docs/STATE_MODEL.md`](docs/STATE_MODEL.md) |
| RAG 与 evidence provider | [`docs/RAG.md`](docs/RAG.md) |
| 记忆系统 | [`docs/MEMORY_SYSTEM.md`](docs/MEMORY_SYSTEM.md) |
| 上下文层级 | [`docs/CONTEXT_TIERS.md`](docs/CONTEXT_TIERS.md) |
| 模型路由 | [`docs/MODEL_ROUTING.md`](docs/MODEL_ROUTING.md) |
| 性能与缓存 | [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md) |
| 测试策略 | [`docs/TESTING.md`](docs/TESTING.md) |

旧 roadmap、旧迁移计划与旧架构文本统一保存在 [`docs/archive/`](docs/archive/)；它们只用于历史追溯，不再拥有当前进度或架构真值。

## 文档治理规则

1. `docs/PROJECT_STATUS.md` 是唯一当前进度 owner。
2. 不再新增并列的 `STATUS` / `ROADMAP` / `NEXT_PHASE` / `AUDIT` 长期入口。
3. 当前架构事实进入 `docs/ARCHITECTURE.md`；领域语义进入 `domain_models.md`；硬约束进入 `state_invariants.md`。
4. 专项文档只描述自己的子系统，不宣布全局当前阶段。
5. 历史计划保留，但必须明确标记为 archive/reference。

## 当前开发状态

当前处于 **P2-D**。P2-D-1 对应 Draft PR #115，源码 lexical match → innermost symbol mapping 与 exact-SHA CI association 已进入实现，但 CI 尚未绿色，因此不得合并。实时事实以 [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) 为准。

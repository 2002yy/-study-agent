# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-08-08  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**

本文件只维护当前事实、可复核证据、缺口和执行顺序。不得新增并列长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT 文档。

## 1. 当前结论

- **P1 运行时 owner 与普通模式收口：完成。**
- **P2-A 遗留样式/产品 surface owner 清理：完成。**
- **P2-B 平台配置治理：完成。**
- **P2-C 兼容层退出：完成。**
- **当前阶段：P2-D 源码学习与验证增强。**
- **当前切片：P2-D-1 / Draft PR #115。**

## 2. 当前切片：PR #115

PR：`P2-D-1: pin source symbols and CI to exact commits`

当前可复核事实：

- state：open；
- draft：true；
- head：`b1ae5623d716275b5f998e104b3b1bc5b218f1dd`；
- GitHub 当前报告 mergeable=true；
- 最新关联 CI workflow run `31192056375`：completed / **failure**；
- 因 CI 未绿色，**不得合并**。

该切片实现范围：

- wide GitHub search chunk 收窄到 deterministic lexical match line；
- match line → innermost parsed source symbol，不依赖 LLM 猜 symbol；
- 无 containing symbol 时保留 path+line fallback；
- commit-pinned GitHub checks 关联到 source-search result；
- CI payload SHA 必须与 snapshot SHA exact match；
- CI unavailable/failure 与 source-evidence validity 分离。

## 3. 2026-08-08 已冻结的 P2-D 语义合同

GrillMe 决策已经统一固定到稳定文档：

- [`../domain_models.md`](../domain_models.md)：领域对象、EvidenceSet、Claim/Revision、Understanding、Hypothesis、NextStep、Topic/Goal、Persona/provider 语义；
- [`../state_invariants.md`](../state_invariants.md)：不可破坏的硬约束；
- [`ARCHITECTURE.md`](ARCHITECTURE.md)：当前 runtime/owner/source-learning pipeline；
- [`STATE_MODEL.md`](STATE_MODEL.md)：durable/ephemeral/cache/derived state 边界。

重点冻结：

1. SourceEvidence 与 CI ValidationObservation 分离；
2. EvidenceSet = 1 Primary + 0–4 Supporting；
3. 自动源码扩展默认最多 one-hop；
4. confirmed / source freshness / retention 三轴分离；
5. LearningClaim 使用稳定 identity + immutable Revision；
6. 没有可靠 Primary → LearningHypothesis，不伪造 Claim；
7. blocking unresolved 才产生 NextStep；
8. durable Claim 只沉淀长期复用机制/边界/不变量/决策性事实；
9. duplicate/conflict 不由 LLM 静默覆盖；
10. project/general scope 分离，单仓库不自动泛化；
11. Topic / Goal / ResumePoint 分离，首页 action-first；
12. Persona 共享单一 durable learning truth；
13. GitHub/RAG/Web 是 provider，不是 truth type；
14. design-vs-implementation divergence 必须显式呈现。

**注意：合同冻结 ≠ 生产功能全部实现。** 生产 claim UI、durable CI history 等仍不在当前切片范围。

## 4. 当前运行时边界

```text
EvidenceRuntime
LearningSessionRuntime
ExtensionRuntime
        ↓ narrow ports
WorkspaceCoordinator
        ↓ view model
React WorkspaceView
        ↓
FastAPI application services
        ↓
SQLite durable truth
```

普通稳定入口：学习会话、资料与来源、学习成果、设置。群聊、受控工具与开发者诊断只通过单一 Lab 入口进入并默认休眠。

## 5. 已完成关键证据

| 主线 | 关键证据 |
|---|---|
| EvidenceRuntime 收口 | PR #101–#103 |
| LearningSessionRuntime 收口 | PR #104–#106 |
| ExtensionRuntime / 普通模式收口 | PR #107–#109 |
| P2-B CORS/config owner | PR #111，merge `6f743db0750e5cacf6370b2fee3cdd091b946f78` |
| P2-C old News route/model compatibility exit | PR #112–#113 |
| P2-C old Extension drawer surface exit | PR #114，merge `283c173e99f7a68985a536682155ce8948d54a70` |
| P2-C 最终同文件树绿色验证 | PR #114 head `8073da2adb033945d00d13e9db061ab9186b3d25`，CI run `31182503935` |

详细失败/修复过程保留在 Git history、PR/CI 与 archive 文档，不继续堆叠在唯一状态入口。

## 6. 下一执行顺序

### P2-D-1 立即项

1. 修复 PR #115 当前 CI failure；
2. 在同一有效 head/同文件树上获得完整绿色验证；
3. 确认 exact-SHA CI association 与 source validity 分离合同没有被为了过 CI 而放宽；
4. 绿色后再考虑 ready/merge。

### P2-D 后续验证

1. Firefox 核心流程抽样；
2. WebKit 核心流程抽样；
3. 至少一台实体手机验证：IME/input、scroll、drawer、Lab、recovery。

## 7. 冻结边界

当前不扩张：

- Provider replay 扩展；
- production Claim UI；
- durable CI observation history；
- 群聊能力扩张；
- News 独立产品化；
- executable agent / 多步自主执行。

后续关于主动检索、多步 tool calling、retry/降级、必须确认动作、长期写入时机等 Agent 主动性问题，尚未在本轮合同中冻结，不得提前当作既定设计。

## 8. 文档治理结果

2026-08-08 文档体系统一：

- `PROJECT_STATUS.md` 保持唯一进度 owner；
- 当前架构/领域/不变量/状态模型职责分离；
- 旧 roadmap / migration / architecture 文本迁入 `docs/archive/` 并保留原路径兼容指针；
- 专项文档只描述子系统，不再维护独立全局阶段。

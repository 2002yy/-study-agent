# Study Agent 项目表达与决策索引

> 更新：2026-08-21
> 本文件只用于项目介绍和决策导航，不拥有当前状态、架构或执行顺序。实时结论以 [`PROJECT_STATUS.md`](PROJECT_STATUS.md) 为准。

## 一句话介绍

Study Agent 是一个本地优先的个人学习工作台：它把聊天、资料、理解验证和下一步收敛为可恢复、可验证、可追溯的学习状态，而不是长期堆积聊天记录或让多个角色各自维护一套“记忆真相”。

## 当前可讲的工程主线

1. **单一学习真值** — SQLite 中的 Goal、Claim、Revision、SourceEvidence、UnderstandingEvidence 和 NextStep 各有明确 owner；Persona、教学评估和长期记忆不能覆盖学习真值。
2. **证据可追溯** — 源码证据固定到 repository / commit / file / symbol / line；provider 状态、检索分数和 CI 结果不混入证据身份。
3. **理解不能由 Agent 自证** — 只有显式 semantic closure 才能写入理解证据；跳过验证可以结束 Goal，但不能伪造 confirmed。
4. **可恢复的长流程** — ResearchRun、LearningClosureRun、RagWriteRun 与 durable ResumeContext 使用服务端状态，而不是只依赖浏览器请求是否仍然存在。
5. **外发真实性** — 联网搜索、历史消息、学习状态、长期记忆和本地证据是否实际外发由后端记录；失败或空结果不能伪装为已找到来源。
6. **工程门禁** — pytest、RAG baseline、Ruff、detect-secrets、mypy baseline、前端测试/构建、三浏览器 Golden Journeys 和 real-stack gates 共同保护主链路。

## 已冻结的 Grill 结论在哪里

P2-D GrillMe 决策 1–49 已经进入稳定合同，不在本文件复制第二份：

- [`../domain_models.md`](../domain_models.md)：领域对象、关系、生命周期和最小实体集；
- [`../state_invariants.md`](../state_invariants.md)：学习真值、证据、验证、恢复、工具与持久化硬约束；
- [`STATE_MODEL.md`](STATE_MODEL.md)：durable / ephemeral / derived / context 边界；
- [`PROJECT_STATUS.md`](PROJECT_STATUS.md)：这些合同当前实现到哪里、证据是什么、下一步是否 GO。

当前产品级决策同样只在状态 owner 维护：

- 独立 Learner Model 页面：`STANDALONE NO-GO`；
- GraphRAG：延期，不作为当前核心缺口；
- 推断型长期画像自动写回：延期，只允许用户确认的偏好；
- Android 实体手机验收：待真实设备与记录，不用自动化冒充；
- G16 外发真值止血：实现提交 `2662cd3` 与 legacy Golden Journey 验收修正 `a3f00de` 已快进交付到 `main`；完整 [CI #32499954659](https://github.com/2002yy/study-agent/actions/runs/32499954659) 全绿，止血交付门关闭。
- G12 可取消本地 RAG：最终 Grill 决策 1–24 已冻结，当前实施门为 GO；按 ChatTurn/operation owner 路线实施 cooperative cancellation，不新增 LocalRagRun。
- G18 深度调研（DeepResearch）：2026-08-22 Grill 决策 1–16 冻结，实施排期插队 G14 前；扩展 WebLookupRun 多轮迭代管线，仅证据链不写 LearningTruth，运行中转向为元数据注入（修订 G12 决策 10）。合同见 PROJECT_STATUS 第 11 节。
- G14 临时附件：2026-08-23 Grill 决策 1–16 + 验收门 v2 冻结，实施立即开始；thread 内共享库过滤隔离、随会话存活、一键转正幂等、双层 fail-closed（文本 embedding 跟随策略、vision 默认关）、删除绑定归档成功之后。合同见 PROJECT_STATUS 第 12 节。

## 展示边界

- 不再把已移除的 Streamlit 入口、旧测试数量或旧路线图当作当前事实。
- `PedagogyEvalRun` 是教学评估记录，不是学习者能力分数，也不是第二套长期画像。
- `LearnerModelSnapshot` 当前是只读派生 API；没有独立 UI、写回路径或 mastery 百分比。
- 实体手机、视觉对比度和真实屏幕阅读器验收仍需人工证据。
- “仅当前问题”约束所有回答、教学评估和 embedding 调用；`allow_local_evidence` 不等于允许全量资料云端 embedding。
- 最新 SHA、CI、缺口和下一步必须从 [`PROJECT_STATUS.md`](PROJECT_STATUS.md) 引用，避免本展示材料漂移。
- G16 按会话记忆 ask：2026-08-23 Grill 决策 1–14 + 验收门 v2 冻结，实施排期立即开始；三档 memory_policy（默认 auto）、会话级 ask、CAS 落库 thread 快照、可撤销徽章、审计三态字段。两轮审计修复 7 个问题（恢复判定/CAS 并发/审计位置/撤销语义/空 bundle/fail-closed/retry）。合同见 PROJECT_STATUS 第 13 节。

# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-07-27  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**证据与 AnswerClaim 真值合同已经封板；当前建立离线、record-only 的结构化 claim 质量基线，不接入生产回答。**  
> 当前分支：`agent/answer-claim-eval-baseline`。

本文件只维护当前事实、真实指标、缺口、执行顺序和门禁。历史细节以 Git 提交和 PR 为准。

## 1. 产品与架构边界

学习主路径：

```text
当前目标
-> 教学或练习
-> 资料与外部证据
-> 理解验证
-> 已确认内容 / 未解决缺口
-> 明确下一步
-> 整理与恢复
```

- RAG 服务于围绕自己的资料学习。
- Web Research 服务于需要外部事实时获得可信证据。
- GitHub 是源码学习高级研究工具，不是第二个执行产品。
- Memory 是学习连续性基础设施。
- Workflow 只属于高级诊断。
- React 只负责交互和可重建缓存；SQLite durable entities 是运行真值。
- planned / attempted / failed 不得覆盖 committed truth。
- 当前不推进新向量数据库、GraphRAG、原生移动端、可执行仓库代理、掌握百分比或并列长期状态文档。

## 2. 已完成主链

已完成：

- TaskContract 单一真值；
- LearningClosureRun 与总结闭环；
- ThreadSummaryState；
- 学习状态去伪精化；
- 结构化恢复卡与语义会话导航；
- UI 收敛、窄屏适配和五条 Golden Journey；
- RAG K1a–K1e 确定性基线和真实 Provider replay harness。

## 3. 已完成的证据与 claim 真值

### PR #61：G13 live / restore parity

Merge SHA：`597006e99919ea7e5f5b02f01b1536b446da9a55`，CI #1317 全绿。

- 正确读取 `RagResult.chunk`；
- local evidence 使用 `chunk_id`；
- live -> persisted -> restored 等价；
- 教学引用刷新后保持。

### PR #62：EvidenceSnapshot v1

Merge SHA：`fcfb9bc66750d10c822306fae735424e658b19ef`，CI #1340 全绿。

- `EvidenceRefV1 / EvidenceSnapshotV1 / ClaimEvidenceLinkV1`；
- 服务端拥有证据身份和生命周期；
- 新旧 Turn 使用现有 JSON 快照兼容持久化；
- React 优先读取服务端真值；
- pedagogy 引用与事实 claim link 分离。

### PR #63：ResearchRun source truth

Merge SHA：`f1b2a4f9d481a16e5c93e6ac8fb4c0f9ee2f45c2`，CI #1357 全绿。

- selected/rejected ResearchRun 来源进入 ChatTurn；
- 保存 Provider 状态、stop reason、URL/domain、相关度和排除原因；
- continuation/retry 不能切换来源 owner；
- 实时与恢复读取同一 `rag_snapshot`。

### PR #64：adopted evidence / diagnostics 分层

Merge SHA：`451bc4a78fc3eda6219083371591aa46c8e62900`，CI #1368 全绿。

- 普通层只显示 selected 或教学明确引用证据；
- candidate/read/rejected、分数和工具调用进入诊断详情；
- 无 selected 时不把候选包装成回答来源；
- 普通复制和诊断复制分离；
- 窄屏、链接换行和触控边界已处理。

### PR #65：AnswerClaimSnapshot v1

Merge SHA：`b700da1a2751769959ae1b41966f5da0a854162a`，CI #1389 全绿。

- `AnswerClaimV1 / AnswerClaimSnapshotV1`；
- final answer hash 和稳定 claim ID；
- claim kind/status/source、support type、confidence 和 evidence ID 校验；
- supplied/validated snapshot 只有 answer hash 匹配时才接受；
- validated claim links 回投 EvidenceSnapshot；
- streaming/interrupted/failed/abandoned 使用稳定 `turn_not_completed`；
- completed 且无 producer 时保存 final answer hash + `producer_unavailable`；
- continuation 在新 final answer 前使旧 claim truth 失效；
- retry 不继承父 Turn claims；
- partial commit 只能更新文本，不能覆盖服务端 route/rag/pedagogy 或注入伪造 claim；
- 旧 Turn 在内存中兼容投影，不静默改写数据库；
- 未修改 prompt、未增加模型调用、未用自然语言字符串推断 claim、未增加 UI。

## 4. 当前真实指标

### RAG K1

- corpus：12 份学习文档；
- retrieval：30 case / 26 answerable；
- answer-quality gold：10 case；
- source recall@K：0.923077；
- nDCG：0.903600；
- adaptive recall@K：0.942308；
- multi-source recall@K：0.9；
- stale / forbidden leakage：0；
- deterministic answerable supported：26/26；
- deterministic unanswerable block：4/4。

这些是固定 corpus 的回归合同，不代表真实模型最终质量。尚未有实际成功的正式真实 Provider benchmark。

### GitHub replay

- 15 个仓库；
- 17 个 case；
- 15 个 Provider replay；
- partial rate：0.7647；
- symbol mapping precision / recall / F1：0.625 / 0.4545 / 0.5263；
- CI association precision / recall / F1：0.3529 / 1.0 / 0.5217。

G10-D 可执行代理继续冻结。

## 5. 当前缺口

AnswerClaim 合同已经存在，但没有经过真实/模拟结构化 producer 的系统质量评测。当前未知：

- schema parse 成功率；
- factual / instructional / question / recommendation / uncertainty 分类准确性；
- claim coverage；
- unsupported claim rate；
- claim-evidence link precision / recall；
- answer hash mismatch 和 unknown evidence 的实际拒绝率；
- 空回答、不可回答、拒答、带不确定表达和复合回答的表现；
- Provider 延迟、token 和额外成本；
- 不同 Provider / model 的稳定性。

在这些指标形成前，不得把 claim producer 接入普通生产回答，也不得在 UI 展示“已支持 claim”。

## 6. 精确执行顺序

### P0-2c2b1：AnswerClaim 离线评测基线（当前）

目标：复用现有 RAG K1 的 10 个 answer-quality gold case，建立**不调用生产聊天、不修改 prompt、不写 ChatTurn**的 record-only harness。

范围：

1. 定义版本化 `AnswerClaimEvalCase`：
   - case ID；
   - question；
   - final answer；
   - answerable / refusal expectation；
   - expected claim texts/kinds；
   - expected evidence IDs；
   - expected claim-evidence links；
   - forbidden claim patterns。
2. 定义 producer adapter 输入/输出合同，只接受结构化 JSON；
3. 首个 deterministic fixture producer 用 gold 数据验证 evaluator，不作为模型质量结果；
4. evaluator 指标：
   - schema_valid；
   - claim precision / recall / F1；
   - kind accuracy；
   - claim coverage；
   - unsupported claim rate；
   - link precision / recall / F1；
   - refusal leakage；
   - answer-hash and evidence-ID rejection；
5. 报告必须包含 corpus/case/evaluator/producer fingerprint；
6. 输出 checked-in record-only snapshot；
7. 失败、无法解析或 unavailable 不得补造完成分数；
8. 不接生产 ChatService，不改普通 UI。

门禁：

- deterministic evaluator 自测满分；
- malformed / hallucinated / missing-claim / wrong-link / refusal-leakage 负例；
- snapshot fingerprint 稳定；
- 全量 CI。

### P0-2c2b2：真实 Provider claim replay

仅在 deterministic evaluator 稳定后：

- 使用现有 real-provider replay 基础设施；
- 固定 Provider/model/temperature/prompt/case fingerprint；
- report-only，默认不进普通 CI；
- 报告 parse rate、质量指标、latency、tokens 和成本；
- 质量未达标时不接生产。

### P0-3：架构真值与 Streamlit 清理

- 同步 `ARCHITECTURE_STATUS.md`、`STATE_MODEL.md`；
- 删除或迁移 `src/ui`；
- requirements 移除 Streamlit 并重新锁定；
- README / USER_GUIDE 同步；
- package diff 和全量回归。

### P1

1. RAG-K1f 真实 Provider 回答基线；
2. RAG-K2 结构化 parser 和 structure-aware chunking；
3. 学习成效基线。

### P2

1. 自适应 `LearningPlanRun / LearningUnit / AssessmentAttempt`；
2. GitHub 源码学习 24–30 case 质量收口；
3. G10-D 可执行代理继续冻结。

## 7. 统一验证要求

每个切片必须完成：

- 目标测试；
- 后端全量 pytest；
- RAG K1 baseline；
- Ruff；
- expanded mypy baseline 不扩大；
- package helper；
- detect-secrets；
- 前端全量 Vitest；
- TypeScript 与 Vite production build；
- 兼容和失败恢复；
- 更新本文件；
- 任一门禁未完成不得合并。

## 8. 当前执行状态

- 当前分支：`agent/answer-claim-eval-baseline`；
- 已完成：PR #61–#65；
- 当前任务：P0-2c2b1 AnswerClaim 离线 record-only 评测基线；
- 下一动作：定位 K1 answer gold、evaluator 和 replay report 结构，复用其 fingerprint 与 snapshot 模式；
- 合并策略：Draft PR -> evaluator 负例审查 -> 完整 CI -> 全绿合并。

## 9. 文档规则

- 当前状态只更新本文件；
- `ARCHITECTURE_STATUS.md` 只维护稳定 owner/边界；
- `STATE_MODEL.md` 只维护稳定数据模型；
- 不新增并列长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT。

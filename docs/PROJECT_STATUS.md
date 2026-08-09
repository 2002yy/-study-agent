# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-08-09  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**

本文件只维护当前事实、可复核证据、缺口和执行顺序。不得新增并列长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT 文档。

## 1. 当前结论

- **P1：完成。**
- **P2-A：完成。**
- **P2-B：完成。**
- **P2-C：完成。**
- **P2-D-1：完成。** commit-pinned source symbol + exact-SHA CI association 已进入 main。
- **P2-D-2A：完成。** normalized durable learning truth schema + repository 已进入 main。
- **P2-D-2B：完成。** deterministic SourceEvidence convergence 已进入 main。
- **P2-D-2C：完成。** atomic Claim / Hypothesis commit boundary 已进入 main。
- **D-2 mini Golden Journey：已在 PR #122 head 上通过完整 CI；本 PR 合并即关闭 D-2。**
- **P2-D GrillMe 决策 1–49：已冻结。**
- **下一实施批次：P2-D-3 — Semantic Closure + Understanding + Resume + Minimal UI。**

D-2C 后 main 基线：`c66d3cd2d24d63b3464465a7bdc4d4b37128bee4`。

D-2 mini Golden Journey：PR #122，验证 head `c04bde0fd0722e2e4617af5123f93222d569f453`，CI run `31308130930` 在代码/测试 head 上 completed / **success**。本文件的状态同步提交会触发该 PR 的最终同分支复验，仍以最终 head 绿色为合并门槛。

## 2. P2-D 已进入 main 的基础

### 2.1 P2-D-1 — commit-pinned source evidence

PR #115 squash merge：`9581b4acea6132e9e0ee8902a1cac9a61bbd6939`。

已具备：

- wide search chunk → deterministic lexical match line；
- match line → innermost parsed symbol；
- 无 symbol 时 path+line fallback；
- SourceEvidence identity 固定到 repository / commit / tree / file / symbol / lines；
- CI payload 必须 exact-SHA association；
- CI failure/unavailable 不使 SourceEvidence 失效；
- custom snapshotter 不隐式触发 live CI；
- 不创建第二套 parser / CI provider。

### 2.2 P2-D-2A — durable learning truth

PR #119 squash merge：`1c2c3456b9f403a17d86712e98741ea8f2bcfb34`。

Global SQLite schema 已升级到 v17，正式落地：

- LearningTopic；
- LearningGoal + prerequisite relation；
- LearningClaim；
- immutable ClaimRevision；
- immutable SourceEvidence；
- ClaimRevision ↔ Evidence role relation；
- UnderstandingEvidence ↔ ClaimRevision result relation；
- lightweight LearningHypothesis；
- lightweight NextStep。

`LearningTruthRepository` 是单一 transaction owner。已验证 fresh DB、v16→v17、migration rollback/recovery、FK/unique/check、restart readback、revision/source immutability、prerequisite cycle guard、legacy learning state 零自动迁移。

### 2.3 P2-D-2B — SourceEvidence convergence

PR #120 squash merge：`458de772fd589c9e56947d21f59e208baa826e75`。

已具备：

- turn/search candidate → durable SourceEvidence identity whitelist；
- query/rank/score/confidence/provider/CI/selection diagnostics 不进入 durable truth；
- deterministic Primary priority；
- exact identity dedupe；
- 同一 EvidenceSet 保持 same repository + commit + tree；
- exactly 1 Primary + 0–4 Supporting；
- supporting proof-dimension diversity；
- learning graph expansion 显式 `depth=1`；
- normal source learning 显式 `include_ci=False`。

Mini Journey 额外发现并修正一个跨层语义缺口：snapshot provider unavailable 不再被压扁成 `missing_source`，而是保留为 `provider_unavailable`。

### 2.4 P2-D-2C — Claim / Hypothesis commit

PR #121 squash merge：`c66d3cd2d24d63b3464465a7bdc4d4b37128bee4`。

已具备：

- `Claim + rev1 + SourceEvidence links` 单事务提交；
- 中途 SourceEvidence 冲突时 Claim shell / Revision / Evidence 全部 rollback；
- 无 qualified Primary → LearningHypothesis only；
- 有 Primary → source-backed Claim + immutable initial Revision；
- existing lineage reuse 只能显式指定 `existing_claim_id`；
- existing lineage 要求 topic/scope/kind 一致和显式 revision reason；
- 不做 embedding / LLM 自动同义合并；
- D-2 不决定用户 mastery。

## 3. D-2 mini Golden Journey

PR #122 的成功路径使用**当前 checkout 中真实的 Study Agent `src/application/github_source_evidence.py` 源码文本**，只把 provider 元数据固定为 deterministic fake snapshot，避免 CI 依赖公网：

```text
LearningTopic + LearningGoal
→ real Study Agent source text
→ GitHubSnapshotService deterministic line/symbol mapping
→ LearningSourceEvidenceService convergence
→ LearningOutcomeCommitService
→ Claim rev1 + SourceEvidence atomic commit
→ recreate LearningTruthRepository
→ same Topic / Goal / Claim / Revision / exact Evidence restored
```

同时验证：

```text
provider unavailable
→ convergence.provider_unavailable
→ LearningHypothesis only
→ 0 Claim / 0 Revision / 0 SourceEvidence
```

该 Journey 还确认 D-2 不会凭空创建 UnderstandingEvidence；理解确认属于 P2-D-3。

## 4. 仍然有效的迁移禁令

- `AnswerClaimV1` **不是** `LearningClaim`；
- `EvidenceRefV1 / EvidenceSnapshotV1` **不是** `SourceEvidence`；
- legacy `learning_state.confirmed_points` **不是** formal confirmed mastery；
- 旧 Markdown memory / session summary 不得批量晋升为 confirmed Claim；
- retrieval score / LLM confidence / provider status / selection reason 不得进入 durable SourceEvidence；
- CI ValidationObservation 不得并入 SourceEvidence identity。

## 5. 稳定合同 owner

- [`../domain_models.md`](../domain_models.md)：P2-D 领域对象与 1–49 决策；
- [`../state_invariants.md`](../state_invariants.md)：硬约束；
- [`ARCHITECTURE.md`](ARCHITECTURE.md)：runtime owner 与 evidence pipeline；
- [`STATE_MODEL.md`](STATE_MODEL.md)：durable / ephemeral / cache / context boundary；
- [`TESTING.md`](TESTING.md)：D-2/D-3/D-4 与 Golden Learning Journey 验收。

**合同冻结 ≠ 功能已上线。** 以下实现顺序仍是唯一当前执行顺序。

## 6. P2-D-3 — NEXT

目标：让 D-2 已存在的 durable truth 真正进入学习闭环，而不是继续依赖 legacy `learning_state` JSON 恢复。

### 6.1 Semantic Closure

- 普通 turn / retrieval 只产生 ephemeral candidate；
- 仅 semantic subsection closure 才允许 convergence → durable commit；
- 复用现有 `LearningClosureService` 的 source-current / retry / resumable orchestration 模式；
- 不把 MemoryRun / Markdown memory 改造成 Claim owner；
- user skip validation 时 Goal 可以继续/结束，但相关 Claim 不得伪造 confirmed。

### 6.2 UnderstandingEvidence

- 将现有 `PedagogyEvalRun` 作为理解验证输入来源之一；
- durable UnderstandingEvidence 保存 method / prompt / raw user response；
- 1 次验证覆盖 1–3 个 ClaimRevision，每个结果独立 pass / partial / fail；
- 不保存 evaluator chain-of-thought；
- agent 不能自我确认 mastery。

### 6.3 Durable Resume

ResumeContext 从 durable learning truth 派生，优先：

```text
Topic
→ active/focus Goal
→ confirmed/unverified Claims
→ blocking Hypothesis/unresolved
→ Primary NextStep
→ relevant SourceEvidence
→ 必要的最近局部 ChatTurns
```

旧 `learning_state` 只保留兼容 fallback，不 destructive migrate。

### 6.4 Minimal UI

复用现有：

- `LearningStrip`；
- `LearningPanel`；
- `EvidenceTrail`。

第一版只展示 Goal、少量 Claim、Primary/Supporting Evidence、Hypothesis、短 Understanding Validation、Primary NextStep。禁止引入知识图谱、Claim dashboard、Route editor、Retention dashboard。

## 7. P2-D-4 — AFTER D-3

- Primary unchanged → current；
- Primary materially changed → stale_candidate；
- removed / unmappable → source_changed / historical；
- corroborating support drift 不自动 stale；
- prerequisite support materially changed 可触发 stale_candidate；
- explicit revalidation → same Claim lineage + immutable next Revision；
- 完成 full Golden Learning Journey；
- Chromium + Firefox sample + WebKit sample + 实体手机验收。

## 8. 当前执行顺序

```text
P2-D-1                         ✅ complete
P2-D-2A                        ✅ complete
P2-D-2B                        ✅ complete
P2-D-2C                        ✅ complete
D-2 mini Golden Journey        ✅ validated; PR #122 final merge pending

P2-D-3                         ← NEXT
closure + understanding + resume + minimal UI

P2-D-4
freshness + revalidation + full Golden Journey
```

任何后续实现若改变该顺序或扩大 scope，必须先更新本唯一状态 owner，再执行。

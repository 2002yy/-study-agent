# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-08-09  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**

本文件只维护当前事实、可复核证据、缺口和执行顺序。不得新增并列长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT 文档。

## 1. 当前结论

- **P1 运行时 owner 与普通模式收口：完成。**
- **P2-A 遗留样式/产品 surface owner 清理：完成。**
- **P2-B 平台配置治理：完成。**
- **P2-C 兼容层退出：完成。**
- **P2-D-1 commit-pinned source evidence + exact-SHA CI：完成。**
- **P2-D GrillMe 决策 1–49：已冻结。**
- **当前实施批次：P2-D-2A — Durable Learning Truth Schema + Repository。**

当前 `main` 基线：`9581b4acea6132e9e0ee8902a1cac9a61bbd6939`。

P2-D-1 / PR #115 已在最终 head `67bdcb38d0ad112e3355b4d740e080118a67f6e8` 上通过完整 CI run `31304313646`（pytest、RAG K1、Ruff、detect-secrets、expanded mypy + baseline、frontend test/build、Browser Golden Journeys、real-stack browser gates），随后 squash merge 为 `9581b4acea6132e9e0ee8902a1cac9a61bbd6939`。

## 2. P2-D-1 已关闭

PR #115 已提供并进入 main：

- wide GitHub search chunk → deterministic lexical match line；
- match line → innermost parsed source symbol，不依赖 LLM 猜 symbol；
- 无 containing symbol 时保留 path+line fallback；
- commit-pinned GitHub checks / workflow runs 关联到 source-search result；
- CI payload SHA 必须与 snapshot SHA exact match；
- CI unavailable/failure 与 source-evidence validity 分离；
- custom snapshotter 默认不隐式触发 live CI；
- normal live path 可读 commit-pinned CI observation；
- 复用 `RepositoryStructureIndex`、`evidence_for_range`、`pin_evidence_refs`、`PaginatedGitHubChecksService`，没有创建第二套 parser/CI provider；
- refresh 时发现的 `match_line_range()` mypy 新 signature 已通过局部变量修正消除，**没有扩 mypy baseline**。

P2-D-2 以该 merge commit 为 source-candidate 基础，不再在旧 #115 branch 上叠实现。

## 3. 已冻结的 P2-D 合同

稳定 owner：

- [`../domain_models.md`](../domain_models.md)：领域对象、Agent 主动性、Route/prerequisite/focus、Artifact/context、P2-D v1 schema/UI/Golden Journey；
- [`../state_invariants.md`](../state_invariants.md)：不可破坏的硬约束；
- [`ARCHITECTURE.md`](ARCHITECTURE.md)：当前 runtime/owner/source-learning pipeline；
- [`STATE_MODEL.md`](STATE_MODEL.md)：durable/ephemeral/cache/context temperature 边界；
- [`TESTING.md`](TESTING.md)：D-2/D-3/D-4 与 Golden Learning Journey 验收。

核心合同：

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
14. goal-serving read-only retrieval 可自动，goal-expanding research 不可静默；
15. Tool chain 有界；默认最多一次有意义 retry；fallback 不冒充原 evidence type；
16. 外部写/发送/部署/付费/不可逆与 user-intent mutation 需要确认；
17. durable learning truth 只在 semantic closure 提交；
18. LearningRoute 是可变导航建议，不是 curriculum truth；
19. Goal prerequisite 稀疏、无环、可跳过；
20. 多 active Goal 时 pinned focus > 最近明确投入；
21. raw ChatTurn 可长期保留审计，但不是 resume truth；
22. LearningArtifact 不是第二 truth owner；
23. ResumeContext 从结构化 durable state 重建；
24. context compression 与 durable retention 分离；
25. P2-D v1 只正式落地 6 core + 2 light；
26. normalized SQLite，不用大 JSON blob / generic metadata 逃避 schema；
27. v1 UI 只做 Goal/Claim/Evidence/Hypothesis/Validation/NextStep；
28. P2-D 完成以 Golden Learning Journey 为门槛。

**合同冻结 ≠ 功能已上线。**

## 4. Current main gap matrix

### 4.1 ALREADY — 直接复用

| 能力 | 当前基础 | 结论 |
|---|---|---|
| commit-pinned GitHub snapshot | `GitHubSnapshotService` + persistent snapshot repository | 复用 |
| deterministic line/symbol evidence | P2-D-1 / PR #115 | 复用 |
| exact-SHA CI association | P2-D-1 + `PaginatedGitHubChecksService` | CI 仍是 observation |
| structure / code / graph indexes | snapshot-scoped cache | 复用 |
| bounded GitHub provider reads | request/page/work-item budgets | 复用 |
| ordered SQLite migration | `RuntimeDatabase` migration ledger / rollback | 新 schema owner |
| durable/resumable closure pattern | `LearningClosureRun` / `LearningClosureService` | 复用 orchestration 模式 |
| user evaluation run | `PedagogyEvalRun` + SQLite repository | D-3 Understanding 输入之一 |
| semantic session navigation | legacy `learning_state` projection | D-3 fallback |
| current learning UI | `LearningStrip` / `LearningPanel` | D-3 复用 surface |
| current evidence UI | `EvidenceTrail` | D-3 复用 Level 0–1 |

### 4.2 NOW — P2-D v1 真正缺失

1. normalized durable LearningTopic / Goal / Claim / ClaimRevision / SourceEvidence / UnderstandingEvidence / Hypothesis / NextStep；
2. durable Claim lineage owner；
3. durable SourceEvidence owner；
4. deterministic Evidence convergence → atomic ClaimRevision commit；
5. 无 Primary → Hypothesis only 的生产边界；
6. normalized UnderstandingEvidence 与多 ClaimRevision relation；
7. durable semantic ResumePoint；
8. source freshness / explicit revalidation / same-lineage new Revision；
9. 完整 Golden Learning Journey。

### 4.3 CONTRACT — 已冻结但当前不完整实体化

- LearningRoute；
- ClaimConflict / EvidenceConflict 独立 persistence/UI；
- GeneralizationCandidate；
- durable ValidationObservation history；
- Retention history；
- EvidenceRetrieval；
- LearningArtifact 自动化；
- LearningCheckpoint；
- Evidence Level 2 / Revision timeline。

### 4.4 LATER — 不阻塞 P2-D

knowledge graph、curriculum engine / Route editor、Retention scheduler、global stale center、CI monitoring center、Claim management dashboard、group-chat 扩张、News productization、executable agent / 多步外部写自动化、project→general 自动泛化 UI。

## 5. 旧对象迁移禁令

### 5.1 `AnswerClaimV1` 不是 `LearningClaim`

它服务单次 final answer projection，可以作为 candidate/diagnostic 输入，但不能 rename/bulk promote 为跨 session LearningClaim。

### 5.2 `EvidenceRefV1` / `EvidenceSnapshotV1` 不是 `SourceEvidence`

现有 turn projection 含 score、candidate lifecycle、provider status、selection/rejection reason。P2-D SourceEvidence 只保存 exact source identity；这些过程字段继续留在 ephemeral projection/cache。

### 5.3 legacy `confirmed_points` 不是 formal confirmed mastery

旧 `ChatThread.learning_state.confirmed_points`、Markdown memory、session summary 没有新 P2-D SourceEvidence + UnderstandingEvidence 双重证明。D-3 只允许兼容 fallback，不得 destructive/bulk promotion。

## 6. P2-D-2A — Durable Learning Truth Schema + Repository

### 目标

只解决“长期学习真值有没有稳定、可事务化、不可随意覆盖的存储 owner”。**本批不接聊天、不接 UI、不自动生成 Claim。**

### 实施范围

1. stable domain types：LearningTopic、LearningGoal、LearningClaim、ClaimRevision、SourceEvidence、UnderstandingEvidence，以及 lightweight LearningHypothesis / NextStep；
2. SQLite 下一版本 migration：
   - `learning_topics`；
   - `learning_goals`；
   - `learning_goal_prerequisites`；
   - `learning_claims`；
   - `claim_revisions`；
   - `source_evidence`；
   - `claim_revision_evidence`；
   - `understanding_evidence`；
   - `understanding_evidence_claims`；
   - `learning_hypotheses`；
   - `next_steps`；
3. 单一 `LearningTruthRepository` 作为事务 owner；
4. 基础 create/read/list + atomic ClaimRevision/Evidence relation commit；
5. schema 约束：ClaimRevision immutable、exactly-one-primary 在 commit boundary 强制、support≤4、prerequisite cycle guard、无 generic metadata JSON。

### D-2A 验收

- fresh DB migration；
- current DB upgrade；
- migration failure rollback；
- FK / unique / check constraints；
- repository transaction rollback；
- restart 后读回一致；
- 旧 answer/evidence/confirmed_points 零自动迁移。

## 7. P2-D-2B — SourceEvidence Convergence

将 P2-D-1 的 pinned candidates 转成 durable-ready SourceEvidence：normalize → dedupe → exactly 1 Primary → 0–4 Supporting；support role = corroborating/prerequisite；learning graph path 显式 `depth=1`；无 Primary 不形成 Claim-ready EvidenceSet；query/rank/score/CI/provider status 不进入 SourceEvidence。

## 8. P2-D-2C — Claim / Hypothesis Commit

`LearningGoal → candidates → convergence → claim-worthiness`：有合法 Primary 时 atomic commit Claim + rev1 + SourceEvidence；无 Primary 时 Hypothesis only。duplicate v1 只做保守 lineage reuse，不做 embedding 自动合并。

## 9. D-2 mini Golden Journey

```text
Topic + Goal
→ query real Study Agent source
→ commit-pinned candidates
→ convergence
→ Claim rev1 + SourceEvidence atomic commit
→ repository restart
→ same durable truth restored
```

并验证 no Primary → Hypothesis only、transaction failure 不留 partial truth。

## 10. P2-D-3 — Semantic Closure + Understanding + Resume + Minimal UI

D-2 真值层稳定后才接：semantic closure、UnderstandingEvidence、Goal lifecycle、NextStep、durable resume、legacy fallback，以及复用 `LearningStrip` / `LearningPanel` / `EvidenceTrail` 的最小 UI。普通 turn/retrieval 不实时写 Claim。

## 11. P2-D-4 — Freshness / Revalidation + Full Golden Learning Journey

加入 Primary/source drift 判断、context-triggered freshness、explicit revalidation、same Claim lineage + immutable rev2，最后完成 Chromium + Firefox sample + WebKit sample + 实体手机验证。

## 12. 当前执行顺序

```text
P2-D-1                       ✅ complete / merged

P2-D-2A                      ← NOW
schema + LearningTruthRepository

P2-D-2B
SourceEvidence convergence

P2-D-2C
Claim / Hypothesis commit

D-2 mini Golden Journey

P2-D-3
closure + understanding + resume + minimal UI

P2-D-4
freshness + revalidation + full Golden Journey
```

任何后续实现若改变这个顺序或扩大批次 scope，必须先更新本唯一状态 owner，再执行。

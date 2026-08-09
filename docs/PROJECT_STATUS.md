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
- **当前阶段：P2-D 源码学习与验证增强。**
- **P2-D GrillMe 决策 1–49：已冻结。**
- **当前实现前置：先关闭 P2-D-1 / PR #115，再进入 P2-D-2。**

当前 `main`：`27be83ac64013debf31590649eb054cbdfc68077`。

最近 main CI：run `31258820780`，completed / **success**。该 commit 来自 PR #117，只修复 360×520 narrow URL Golden Journey 的测量假阴性，没有放宽产品 CSS/行为门禁。

## 2. P2-D-1 / PR #115 当前事实

PR：`P2-D-1: pin source symbols and CI to exact commits`

当前可复核事实：

- state：open；
- draft：true；
- head：`b1ae5623d716275b5f998e104b3b1bc5b218f1dd`；
- PR metadata 的 base 仍指向较早 `283c173e99f7a68985a536682155ce8948d54a70`；
- 与当前 main `27be83...` 比较已经 **diverged**；共同 merge base 为 `82e6ac17c64291e490478336e909e8970910eaf9`；
- #115 与当前 main 各自都有独立提交，不能把旧 head 直接视为“只差一个 CI 修复”；
- 最新关联 CI run `31192056375`：completed / **failure**；
- pytest、RAG K1、Ruff、detect-secrets 均成功；真正阻塞点是 `Enforce mypy baseline`；
- mypy log 共 127 条 error，与 main baseline 的 known count 相同，但 #115 引入了新的 error signature，因此 baseline 正确阻止了 merge；
- 新增 signature 位于 `src/application/github_source_evidence.py`：`match_line_range()` 把先前字符串变量名 `line` 复用于整数匹配行，导致 `assignment` + `return-value` 两条 mypy error；
- **不得通过更新 baseline 来接受这两条新错误。** 应修正局部变量类型/命名后重新验证；
- 因 #115 尚未 refresh 到当前 main、CI 未绿色，**不得合并**。

### 2.1 #115 已实现且值得复用

- wide GitHub search chunk → deterministic lexical match line；
- match line → innermost parsed source symbol，不依赖 LLM 猜 symbol；
- 无 containing symbol 时保留 path+line fallback；
- commit-pinned GitHub checks / workflow runs 关联到 source-search result；
- CI payload SHA 必须与 snapshot SHA exact match；
- CI unavailable/failure 与 source-evidence validity 分离；
- custom snapshotter 不应因为普通 source search 隐式触发 live CI；
- normal live path 可以读 commit-pinned CI observation；
- 复用现有 `RepositoryStructureIndex`、`evidence_for_range`、`pin_evidence_refs`、`PaginatedGitHubChecksService`，不创建第二套 parser/CI provider。

### 2.2 P2-D-1 关闭门槛

必须按以下顺序完成：

1. 把 #115 refresh/rebase/cherry-pick 到当前 main `27be83...`，保留 #117 narrow-browser 修复；
2. 修复 `github_source_evidence.py` 新增 mypy signature，不扩 baseline；
3. 复核 deterministic line/symbol 与 exact-SHA CI contract 未因冲突处理而退化；
4. unit/integration 绿色；
5. full CI 绿色，包括 frontend、Browser Golden Journeys、real-stack gates；
6. 同一有效 head/同文件树验证后再 ready/merge。

**P2-D-2 不应在旧 #115 head 上继续叠实现。** 先把 D-1 变成 current-main 可复用基础。

## 3. 2026-08-09 已冻结的 P2-D 合同

稳定 owner：

- [`../domain_models.md`](../domain_models.md)：领域对象、Agent 主动性、Route/prerequisite/focus、Artifact/context、P2-D v1 schema/UI/Golden Journey；
- [`../state_invariants.md`](../state_invariants.md)：不可破坏的硬约束；
- [`ARCHITECTURE.md`](ARCHITECTURE.md)：当前 runtime/owner/source-learning pipeline；
- [`STATE_MODEL.md`](STATE_MODEL.md)：durable/ephemeral/cache/context temperature 边界；
- [`TESTING.md`](TESTING.md)：D-2/D-3/D-4 与 Golden Learning Journey 验收。

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
14. goal-serving read-only retrieval 可自动，goal-expanding research 不可静默；
15. Tool chain 有界；默认最多一次有意义 retry；fallback 不冒充原 evidence type；
16. 外部写/发送/部署/付费/不可逆与 user-intent mutation 需要确认；
17. durable learning truth 只在 semantic closure 提交，不边聊边污染长期状态；
18. LearningRoute 是可变导航建议，不是 curriculum truth；
19. Goal prerequisite 稀疏、无环、可跳过；
20. 多 active Goal 时 pinned focus > 最近明确投入，不做全局学习优化器；
21. raw ChatTurn 可长期保留审计，但不是 resume truth；
22. LearningArtifact 不是第二 truth owner；
23. ResumeContext 从结构化 durable state 重建；
24. context compression 与 durable retention 分离；
25. P2-D v1 只正式落地 6 core + 2 light；
26. normalized SQLite，不用大 JSON blob / generic metadata 逃避 schema；
27. v1 UI 只做 Goal/Claim/Evidence/Hypothesis/Validation/NextStep；
28. P2-D 完成以 Golden Learning Journey 为门槛。

**合同冻结 ≠ 功能已上线。** 实现状态以下述 gap matrix 与 D-2/D-3/D-4 为准。

## 4. PR #115 + current main gap analysis

### 4.1 ALREADY — 当前已有、直接复用

| 能力 | 当前基础 | 结论 |
|---|---|---|
| commit-pinned GitHub snapshot | `GitHubSnapshotService` + persistent snapshot repository | 复用，不重造 |
| structure / code / graph indexes | snapshot-scoped cache；`RepositoryStructureIndex` / graph semantic index | 复用 |
| bounded GitHub provider reads | request/page/work-item budgets | 复用 |
| exact-SHA checks cache | `PaginatedGitHubChecksService` + `ProviderCacheRepository` | 复用，CI 仍是 observation |
| ordered SQLite migration | `RuntimeDatabase` migration ledger / atomic rollback | 作为新 schema owner |
| durable/resumable closure pattern | `LearningClosureRun` / `LearningClosureService` | 复用 orchestration 模式，不把 MemoryRun 当 Claim owner |
| user evaluation run | `PedagogyEvalRun` + SQLite repository | 作为 UnderstandingEvidence 的输入来源之一 |
| semantic session navigation | `SessionService` 从 legacy `learning_state` 投影 objective/gap/next | P2-D-3 兼容 fallback |
| current learning UI | `LearningStrip` / `LearningPanel` | 复用 surface |
| current evidence UI | `EvidenceTrail` / helpers/tests | 复用 Level 0–1 展示 |
| PR #115 line/symbol + CI projection | 4-file draft slice | D-1 refresh 后作为 source candidate foundation |

### 4.2 NOW — P2-D v1 真正缺失

1. **没有 normalized durable LearningTopic / Goal / Claim / ClaimRevision / SourceEvidence / UnderstandingEvidence / Hypothesis / NextStep tables。** 当前 SQLite schema 到 v16，学习状态仍主要依赖 `chat_threads.learning_state` JSON 与 turn snapshots。
2. **没有长期 Claim lineage owner。** 现有 `AnswerClaimV1` 是单次最终回答 projection，identity 依赖 answer hash，不能代替跨会话 LearningClaim。
3. **没有 durable SourceEvidence owner。** 现有 `EvidenceRefV1` 混有 score/lifecycle/provider status/selection reason，是 turn projection，不符合最小 immutable source identity。
4. **没有 deterministic EvidenceSet convergence → atomic ClaimRevision commit service。**
5. **没有“无 Primary → Hypothesis only”的生产持久化边界。**
6. **没有 normalized UnderstandingEvidence 与多 ClaimRevision per-result relation。** `PedagogyEvalRun` 目前绑定 turn，且包含 broader evaluator fields。
7. **没有 durable semantic ResumePoint based on Goal/Claims/Hypothesis/NextStep。** 当前 navigation 仍从 legacy learning_state 生成。
8. **没有 source freshness / explicit revalidation / same-lineage new Revision production path。**
9. **没有覆盖完整 P2-D Golden Learning Journey 的集成/浏览器/设备验收。**

### 4.3 CONTRACT — 已冻结，但当前不要求独立表/完整 UI

- LearningRoute；
- ClaimConflict / EvidenceConflict 独立 persistence/UI；
- GeneralizationCandidate；
- durable ValidationObservation history；
- Retention history；
- EvidenceRetrieval；
- LearningArtifact 自动化；
- LearningCheckpoint 独立实体；
- Evidence UI Level 2 深审计 / Revision timeline。

### 4.4 LATER — 明确后置，不阻塞 P2-D

- knowledge graph；
- curriculum engine / Route editor；
- Anki / retention scheduler；
- global stale knowledge center；
- CI monitoring center；
- production Claim management dashboard；
- group-chat expansion；
- News productization；
- executable agent / 多步外部写自动化；
- project→general 自动泛化 UI。

## 5. 不能直接复用/迁移的旧对象

### 5.1 `AnswerClaimV1` 不是 `LearningClaim`

`AnswerClaimV1` 服务单次 final answer 的 factual assertion projection；其 identity、status、source 语义都与跨 session 学习 lineage 不同。可以作为 candidate/diagnostic 输入，但不能 rename 后持久化为 LearningClaim。

### 5.2 `EvidenceRefV1` 不是 `SourceEvidence`

现有 turn evidence projection 含 score、candidate/read/selected/rejected、provider status、selection/rejection reason。P2-D SourceEvidence 只保存 exact source identity；过程字段留在 ephemeral projection/cache。

### 5.3 legacy `confirmed_points` 不是正式 confirmed mastery

旧 `ChatThread.learning_state.confirmed_points`、Markdown memory、session summary 没有新 P2-D SourceEvidence + UnderstandingEvidence 双重证明。P2-D-3 必须 legacy fallback，不得 destructive/bulk promotion。

## 6. P2-D-2 — Durable Learning Truth + Evidence Convergence

### 目标

建立**长期学习真值的最小后端基础**：把 #115 提供的 commit-pinned source candidates 收敛成可持久化的 SourceEvidence / ClaimRevision，或者在证据不足时只创建 Hypothesis。

### 实施范围

1. 新增稳定 learning truth domain types：
   - LearningTopic；
   - LearningGoal；
   - LearningClaim；
   - ClaimRevision；
   - SourceEvidence；
   - UnderstandingEvidence type/schema；
   - lightweight LearningHypothesis；
   - lightweight NextStep。
2. 新增 SQLite 下一版本 migration，使用规范化关系表：
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
   - `next_steps`。
3. 新增单一 `LearningTruthRepository`（可拆内部 helpers，但一个事务 owner）：
   - create/read Topic/Goal；
   - atomic commit ClaimRevision + Evidence relations；
   - create Hypothesis；
   - NextStep 基础 persistence；
   - 理解证据表结构先落地，实际 closure mapping 在 D-3。
4. 新增 source evidence conversion/convergence application service：
   - consumes refreshed #115 pinned candidates；
   - exactly 1 Primary；
   - 0–4 Supporting；
   - supporting role = corroborating/prerequisite；
   - 去重 + 证明维度多样化；
   - 无合法 Primary → Hypothesis only；
   - one-hop 在 learning service 显式 enforced（对 graph 调用 depth=1）；
   - query/rank/score/CI/provider status 不进入 SourceEvidence。
5. duplicate v1 只做**保守 lineage reuse**：已明确属于同一学习问题/稳定 identity 时复用；不做 embedding 自动合并。

### 明确不做

- UI 大改；
- resume UX；
- source freshness/revalidation；
- durable CI history；
- retention；
- Route editor；
- Artifact；
- conflict management UI。

### D-2 测试

- migration from current schema + failure injection rollback；
- FK/unique/check；
- transaction rollback；
- SourceEvidence exact identity；
- exactly 1 Primary / support≤4；
- no Primary→Hypothesis；
- one-hop guard；
- process/debug fields 不进入 durable rows；
- AnswerClaim/EvidenceSnapshot/confirmed_points 不被误提升；
- same repo+commit index reuse / bounded provider calls。

### D-2 验收

给定一个真实 commit-pinned GitHub source candidate set，后端能够：

```text
Topic + Goal
→ converge Evidence
→ atomically persist Claim rev1 + SourceEvidence
```

或在没有 Primary 时：

```text
Topic + Goal
→ persist Hypothesis only
```

数据库重启后读回完全一致；任何事务失败不留下部分 Claim/Evidence。

## 7. P2-D-3 — Semantic Closure + Understanding + Resume + Minimal UI

### 目标

把 D-2 的 durable truth 接进真实学习过程：**不是建表成功，而是一次学习小节能可靠沉淀、验证并恢复。**

### 实施范围

1. 新增/明确 `LearningTruthCommitService` 或等价 application owner：
   - candidate → convergence → claim-worthiness → semantic closure → durable commit；
   - ordinary turn/retrieval 不实时写 Claim；
   - 复用 `LearningClosureService` 的 source-hash/idempotence/retry/source-current 模式，但不把新 Claim 真值继续塞进 MemoryRun/Markdown。
2. UnderstandingEvidence：
   - method = explain/apply/practice；
   - durable prompt + raw user response；
   - 一次 evidence 可关联 1–3 个 ClaimRevision；
   - 每个 relation 独立 pass/partial/fail；
   - 可从匹配当前 Claim 的 PedagogyEvalRun 投影，Agent 自己的解释不能产生 confirmed。
3. Goal lifecycle：active/blocked/completed/abandoned；
   - blocking unresolved 才阻塞 closure；
   - skip validation 可 completed，但 Claim unverified；
   - NextStep 默认 1 primary，optional≤2。
4. Resume：
   - durable Goal/Claims/Hypothesis/NextStep first；
   - legacy `learning_state` second/fallback；
   - 不依赖完整 Chat replay；
   - pinned focus/last active 语义恢复；
   - old confirmed_points 只展示兼容态，不提升 formal Claim。
5. API/view model：提供当前学习语义 projection。
6. 前端复用而非重建：
   - `LearningStrip` / `LearningPanel` 接 durable Goal/Claim/Hypothesis/NextStep；
   - `EvidenceTrail` 适配 Primary/Supporting SourceEvidence；
   - v1 只做 Evidence Level 0–1；
   - Hypothesis 与 Claim 视觉上必须可区分；
   - 不做知识管理 dashboard。

### 明确不做

- freshness/revalidation；
- Revision timeline；
- global stale；
- Route editor；
- Retention；
- Artifact automation；
- conflict UI。

### D-3 测试

- semantic closure 前不写 durable Claim；
- source changed before commit → reject stale commit；
- retry/recovery 不重复 revision；
- pass/partial/fail multi-Claim association；
- “懂了”不 confirmed；
- skip validation Goal completed + Claim unverified；
- provider unavailable 不生成假 Claim；
- refresh/restart 后无完整 Chat history 仍恢复；
- legacy fallback；
- Persona switch single truth；
- Chromium happy-path Golden Journey 到“完成 + reopen resume”。

### D-3 验收

用户能围绕一个源码机制：

```text
提出问题
→ 学习 + source-backed Claim
→ 做一次短理解验证
→ 完成 Goal
→ 关闭/重新打开
→ 看见“已确认 / 未解决 / 下一步”
```

恢复依赖 normalized durable learning state，而不是旧聊天全文。

## 8. P2-D-4 — Freshness / Revalidation + Full Golden Learning Journey

### 目标

证明 Study Agent 能长期维护“当时真的学会过”和“当前源码是否仍支持它”两种事实，完成 P2-D 全链验收。

### 实施范围

1. Source freshness service：
   - repo HEAD forward alone ≠ stale；
   - Primary material unchanged → current；
   - Primary material changed → stale_candidate；
   - Primary removed/unmappable → source_changed；
   - corroborating support drift → drift only；
   - prerequisite material drift → 可 stale_candidate。
2. freshness context-triggered：
   - resume/reopen relevant Topic；
   - prior Claim about to be used as premise；
   - explicit “检查以前学的现在还对不对”；
   - 不做后台全局 repo monitor。
3. explicit revalidation：
   - 新 commit 重新检索/收敛；
   - same Claim lineage；
   - new immutable Revision；
   - old Evidence / Understanding 永不覆盖；
   - 不产生 duplicate Claim。
4. CI observation 继续 runtime/read-time only；不引入 durable history。
5. UI 只加情境 stale warning / revalidate action；Revision management 深 UI 后置。
6. 完成 Decision 49 Golden Learning Journey 全链，包括 source change + revalidation。
7. 浏览器/设备收口：Chromium + Firefox sample + WebKit sample + 至少一台实体手机。

### D-4 强制边界

- GitHub unavailable → no fake Claim；
- no Primary → Hypothesis only；
- CI failure → SourceEvidence still valid；
- skip validation → completed Goal, unconfirmed Claim；
- corroborating drift → no stale；
- Primary changed → stale_candidate；
- resume without full chat；
- same semantic Claim → same lineage；
- CI refresh/cache failure 不阻塞 source learning。

### D-4 验收

Golden Learning Journey 必须完整通过：

```text
Goal
→ exact source Evidence
→ Claim/Hypothesis
→ Understanding
→ Goal closure
→ durable resume
→ source evolves
→ stale_candidate
→ explicit revalidation
→ same Claim lineage + rev2
```

并满足：

- full CI green；
- Firefox/WebKit 核心抽样通过；
- 实体手机 IME/input/scroll/drawer/Lab/recovery/source evidence wrap 人工验收通过；
- snapshot/index cache reuse 与 provider call boundedness 有可复核测试。

## 9. P2-D 结束后才考虑的方向

D-4 关闭之前不扩张：

- Provider replay 扩展；
- production Claim management dashboard；
- durable CI observation history；
- Retention scheduler；
- LearningRoute editor / curriculum engine；
- knowledge graph；
- global stale center；
- LearningArtifact 自动化体系；
- 群聊能力扩张；
- News 独立产品化；
- executable agent / 多步外部写自动化。

## 10. 当前执行顺序

```text
P2-D-1 / PR #115
refresh to current main
→ fix new mypy signatures
→ full green CI
→ merge

P2-D-2
Durable Learning Truth + Evidence Convergence

P2-D-3
Semantic Closure + Understanding + Resume + Minimal UI

P2-D-4
Freshness + Revalidation + Golden Journey + cross-browser/mobile closure
```

任何后续实现若改变这个顺序或扩大批次 scope，必须先更新本唯一状态 owner，再执行。
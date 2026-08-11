# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-08-10  
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
- **D-2 mini Golden Journey：完成。** PR #122 已合并进入 main。
- **P2-D-3A：完成。** Semantic Closure + durable Goal navigation 已进入 main。
- **P2-D-3B：完成。** bounded durable ResumeContext + read-only resume API 已进入 main。
- **P2-D GrillMe 决策 1–49：已冻结。**
- **P2-D-3C：完成。** durable learning truth surface（closure truth bridge、ResumeContext UI、LearningPanel/Strip/EvidenceTrail、goal-isolated confirmation）已进入 main。
- **P2-D-4C：完成。** backend 全链路 golden journey（真实源码 + 双 commit）已进入 main（35336cc）；前端学习侧栏缺陷修复（缺行/补给、摘要刷新、stale 角度刷新、server-only 断言）+ revalidation e2e journey 已进入 main（8fc1746）。
- **P2-D-4D：完成（自动验收部分）。** firefox/webkit sample + 5 项目 51/51 通过；实体手机验收清单已写入 docs/MOBILE_ACCEPTANCE_D4D.md，待执行人填写记录。
- **P2-E：下一实施批次。** 范围（2026-08-11 经现状调研确认，跳过 G 系列产品能力评审）：E-5 仓库清理 → E-1 验收收口 → E-2 backend 辅助模块直测补缺 → E-3 前端 surface 测试补缺。

当前 main 基线：`e05c191`（P2-D-4D）。

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

## 3. D-2 mini Golden Journey — COMPLETE

PR #122 merge：`a5112c4bec81ce9993edeeb88bf2a8779c826138`。

成功路径使用**当前 checkout 中真实的 Study Agent `src/application/github_source_evidence.py` 源码文本**，只把 provider 元数据固定为 deterministic fake snapshot，避免 CI 依赖公网：

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

该 Journey 还确认 D-2 不会凭空创建 UnderstandingEvidence；理解确认由 P2-D-3 semantic closure 负责。

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

## 6. P2-D-3 — COMPLETE

目标：让 D-2 已存在的 durable truth 真正进入学习闭环，而不是继续依赖 legacy `learning_state` JSON 恢复。

### 6.1 P2-D-3A — Semantic Closure + Understanding — COMPLETE

PR #123 merge：`0c481c2e32079d0cd371a43663598b32e2aae712`。

已具备：

- schema v18：`learning_goal_contexts` 与 `learning_goal_claim_revisions`；
- Goal navigation context 与 LearningGoal truth 分离；
- pinned focus 优先于最近 active/blocked Goal；terminal Goal 自动失去 pinned focus；
- D2C Claim/revision commit 原子写入 Goal ↔ ClaimRevision relation；
- 仅显式 semantic closure 才写 UnderstandingEvidence，不做 per-turn durable auto commit；
- durable UnderstandingEvidence 保存 method / validation prompt / raw user response；
- 一次验证覆盖 1–3 个 ClaimRevision，并分别得到 pass / partial / fail；
- evaluator unavailable / needs semantic review → partial，不能伪造 fail；
- explicit misconception reject → fail；
- partial / fail 不得静默完成 Goal；
- explicit user skip 可以完成 Goal，但不得制造 UnderstandingEvidence；
- semantic closure transaction 原子提交 UnderstandingEvidence/results + Goal status + optional NextStep；
- 不保存 evaluator chain-of-thought / confidence 作为 mastery truth。

### 6.2 P2-D-3B — Durable Resume — COMPLETE

PR #124 merge：`c7a3fa0d87ec8646c6063b853f4f370d23aa019a`。

`LearningResumeService` 从 durable Topic / focused Goal / latest ClaimRevision / SourceEvidence / latest Understanding / unresolved Hypothesis / active NextStep 派生 bounded ResumeContext：

- Claims ≤ 3；
- unresolved Hypotheses ≤ 3；
- 1 Primary NextStep + optional ≤ 2；
- Claim recency 由**最新 Revision activity**决定，旧 Revision 不重复进入 resume；
- Understanding 投影轴固定为 `proposed / attempted / partial / confirmed`；
- 默认不把 raw user validation response 放进 ResumeContext；
- Primary / Supporting Evidence 保留 exact source identity；
- `GET /sessions/{session_id}/learning-resume` 已提供 read-only API；
- durable path **不会调用 `SessionService.get_session()`**，恢复不需要重放完整 turns；
- 只有从未获得 durable Goal context 的真正 legacy thread 才走旧 navigation fallback；
- 已有 durable context 但没有 active Goal → `durable/no_active_goal`，绝不 resurrect legacy state；
- legacy `confirmed_points` 只作为 `legacy_confirmed_points` 展示，`claims` 始终为空，不升级为 formal Claim/mastery。

### 6.3 P2-D-3C - Minimal Durable Learning UI - COMPLETE

PR #125 merge：`e413072`。

目标不是增加管理后台，而是把 D3B ResumeContext 接到当前学习 surface，让用户直接看到“正在学什么、哪些 Claim 有 durable 依据、哪里还没解决、理解验证到哪一步、下一步是什么”。

复用现有：

- `LearningStrip`；
- `LearningPanel`；
- `EvidenceTrail`。

第一版只展示：

- 当前 Goal；
- 1–3 个 durable Claim；
- 每个 Claim 的 Understanding 状态；
- Primary Evidence + 可展开 Supporting Evidence（symbol → path/line）；
- unresolved Hypothesis，与 Claim 有明确视觉区别；
- Primary NextStep；
- backend 明确返回 `legacy_fallback` 时才显示 legacy compatibility 信息。

硬边界：

- `LearningPanel/Strip` 不自行读取或推断完整 chat history；
- durable ResumeContext 优先于 `lastChat.route.learning_state`；
- durable/no_active_goal 不得回退到旧 confirmed_points/objective；
- legacy confirmed_points 不得以 Claim/已掌握知识点样式呈现；
- 不引入知识图谱、Claim dashboard、Route editor、Retention dashboard；
- D3C 不实现 freshness/revalidation。

## 7. P2-D-4 — NEXT

- Primary unchanged → current；
- Primary materially changed → stale_candidate；
- removed / unmappable → source_changed / historical；
- corroborating support drift 不自动 stale；
- prerequisite support materially changed 可触发 stale_candidate；
- explicit revalidation → same Claim lineage + immutable next Revision；
- 完成 full Golden Learning Journey；
- Chromium + Firefox sample + WebKit sample + 实体手机验收。

### D-4A — Freshness evaluation service - COMPLETE

- 新服务 LearningFreshnessService.evaluate(claim, head_snapshot)：
  - freshness 是 on-demand derived 状态，不新增持久化表/migration；
  - Primary 在 HEAD 重定位（match_line_range + structure index重映射）；
  - path 不存在/无法重映射 → source_changed；
  - HEAD file_sha == 记录 file_sha → current（零内容比较）；
  - file_sha 不同 → symbol body 归一化比较（strip 尾空白、忽略空行）→ 相同 current / 不同 stale_candidate；
  - corroborating drift 只记录；prerequisite 实质变化可触发 stale_candidate；
  - provider 找不到→ unavailable，不推导 Claim false；
  - 归一化单元测试覆盖 TESTING.md L109–119 判定规则。

### D-4B — Resume freshness + UI + revalidation entry - COMPLETE

- GET /learning-resume 成列输出 freshness status + drift detail（案例化；
- LearningPanel 情境化提示：stale_candidate/source_changed 徽章 + 渐进披露（F1/F2）；
- 显式 revalidation 入口：新 closure run 带 claim 上下文，commit 复用 lineage；
- Playwright fixture + e2e 测试。

Backend completed (deferred items):
- resume projection 已带 freshness detail（status/head_commit/reason/primary/supporting_drift），
  evaluator 故障降级为 unavailable 不中断；
- POST /sessions/{session_id}/claims/{claim_id}/revalidate 已实现：
  同 lineage 新 Revision（reason=revalidated），missing claim / no active goal /
  no primary source 均显式拒绝并返回对应 404/409；
- revalidation 后立即回写 freshness status；
- 未完成项：LearningPanel UI 徽章 + 渐进披露、Playwright fixture + e2e
  （UI 层，见 D-4B-UI 分批或 D-4C 后处理）。

### D-4C — Full Golden Journey (AFTER D-4B) - COMPLETE

- 拓展 mini journey 到 step 1–17，用真实源码 + 双 commit 对；
- step 14–17：Primary 实质修改 → rev1/confirmed 保留、freshness → stale_candidate → 显式 revalidation → rev2 同 lineage；
- e2e golden journey 同步扩展。

Completed（35336cc + 8fc1746）:
- backend 侧 suspension 保留 rev1/confirmed → freshness stale_candidate → revalidate → rev2 同 lineage 已全链路验证；
- 前端缺陷修复：LearningStrip 缺行与来源补充、摘要刷新、stale/current 角度刷新、badge 标题 tooltip、server-only 断言（网络环境不可取时逐层降级而不报错）；
- LearningPanel「重新验证」按钮条件渲染守卫（仅 stale/source_changed 显示），单测锁定；
- e2e `stale_revalidation` journey：stale 条可见 → 重新验证 → 全部 current，desktop + mobile 双项目通过；golden-journeys manifest 期望 29 项已完成。

### D-4D — Cross-browser acceptance (AFTER D-4C) - COMPLETE (automation)

- playwright config 新增 desktop-firefox / desktop-webkit sample（仅 golden-journeys，避免双倍全量成本）；
- `channel: chrome` 限定到 chromium 项目（原先顶层 use 会让 firefox 报 Unsupported channel）；
- 核心 journey 在 firefox / webkit 上通过：golden-journeys 4 条 × firefox/webkit 8/8；
- teardown manifest 扩展为 53 项（4 golden journeys × 4 桌面/移动项目 + complex_content_narrow），全量 5 项目 51/51 通过；
- 实体手机验收步骤已写入验收记录 `docs/MOBILE_ACCEPTANCE_D4D.md`（人工执行，执行人填写后归档）。

Known environment notes:
- 本机 `npx playwright install chromium` 默认 CDN 不可达，使用 `PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright` 完成安装；
- 系统 Chrome（channel: chrome）下 complex-content linkRectCount 断言失败（渲染差异），headless shell 下通过；CI 保持默认 headless。

## 7.5 P2-E — Post-P2-D acceptance + test hardening (AFTER D-4D) - COMPLETE

范围（2026-08-11 现状调研确认；G 系列产品能力评审已排除）：

### E-5 — Repo cleanup - COMPLETE

- 删除 15 个已合并/过时的本地残留分支（codex/*、claude/*、P2-D-4A-freshness 等），保留 main + release-v0.8.0；
- 远程分支不动；不改变 main 内容。

### E-1 — Acceptance + docs/memory sync - COMPLETE (automation)

- 实体手机验收（人工）：按 docs/MOBILE_ACCEPTANCE_D4D.md 10 步执行并填写记录表（执行人/日期/浏览器/设备），完成后回写本 owner；
- docs 收口：TECH_STACK.md “后续 LearningClosureRun”已更新（G1 已实现）；memory/ 六个版本文件已同步到 P2-E 时代；
- 基线收口：8dcaf11。

### E-2 — Backend direct tests for helper modules - COMPLETE

- 覆盖审计结果：之前“17 个模块无测试”过保守；其中 6 个被 test_web_primitives / test_module_identity 直测覆盖、其余 9 个已有命名测试；
- 真正零测试只有 2 个：module_aliases.py + evidence_pinning.py，已补 16 个直测（tests/test_module_aliases.py 9 + tests/test_evidence_pinning.py 7）；
- 不改变产品行为，纯测试补缺。

### E-3 — Frontend surface tests - COMPLETE

- MarkdownMessage/StatusDot/RoadmapPanel/RoutePanel/roleCatalog/useRoleController 建立直测（6 个测试文件，24 个测试）；
- 不改变 UI 行为。
## 8. 当前执行顺序

```text
P2-D-1                         ✅ complete
P2-D-2A                        ✅ complete
P2-D-2B                        ✅ complete
P2-D-2C                        ✅ complete
D-2 mini Golden Journey        ✅ complete
P2-D-3A semantic closure       ✅ complete
P2-D-3B durable resume         ✅ complete

P2-D-3C minimal durable UI     ✅ complete

P2-D-4A freshness service      ✅ complete (PR #126)
P2-D-4B resume freshness + UI  ✅ complete (PR #126)
P2-D-4C full Golden Journey    ✅ complete (35336cc + 8fc1746)
P2-D-4D cross-browser          ✅ complete (automation 51/51; manual checklist in docs/MOBILE_ACCEPTANCE_D4D.md)

P2-E-5 repo cleanup            ← NEXT（删 15 个已合并本地残留分支）
P2-E-1 acceptance + docs sync  ← NEXT（手机验收人工部分 + 文档/memory 收口）
P2-E-2 backend direct tests    ← NEXT（src/web + src/application 17 模块直测）
P2-E-3 frontend surface tests  ← NEXT（MarkdownMessage/StatusDot/RoadmapPanel/RoutePanel/roles）

P2-E
post-P2-D acceptance + test hardening（不含 G 系列产品能力评审）
```

任何后续实现若改变该顺序或扩大 scope，必须先更新本唯一状态 owner，再执行。

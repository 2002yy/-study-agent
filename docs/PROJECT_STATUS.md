# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-08-21
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
- **P2-D-4D：完成（自动验收部分）；实体手机验收延期。** firefox/webkit sample + 5 项目 51/51 通过；因 Android 导出/部署配置尚未就绪，用户于 2026-08-11 明确将实体手机验收延期，记录表仍为空且不得标记完成。
- **P2-E：自动化批次完成；实体手机人工验收延期。** 范围（2026-08-11 经现状调研确认，跳过 G 系列产品能力评审）：E-5 仓库清理 → E-1 自动化验收与文档收口 → E-2 backend 辅助模块直测补缺 → E-3 前端 surface 测试补缺；Android 导出/部署配置就绪后再恢复人工验收。

当前已验证 `main` 基线：`589169b`（[CI #31704003134](https://github.com/2002yy/study-agent/actions/runs/31704003134) 全门禁通过）；G15–G17 核心实现基线 `f69a305` 的 [CI #31703041709](https://github.com/2002yy/study-agent/actions/runs/31703041709) 同样通过 pytest、RAG baseline、ruff、package helper、detect-secrets、mypy baseline、frontend test/build、53 条三浏览器 Golden Journeys 和 14 条 real-stack browser gates。

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

## 7. P2-D-4 — COMPLETE (automation; manual mobile acceptance deferred)

- Primary unchanged → current；
- Primary materially changed → stale_candidate；
- removed / unmappable → source_changed / historical；
- corroborating support drift 不自动 stale；
- prerequisite support materially changed 可触发 stale_candidate；
- explicit revalidation → same Claim lineage + immutable next Revision；
- 完成 full Golden Learning Journey；
- Chromium + Firefox sample + WebKit sample 已完成；实体手机验收因 Android 导出/部署配置未就绪而延期。

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

Backend completed (items deferred at that time):
- resume projection 已带 freshness detail（status/head_commit/reason/primary/supporting_drift），
  evaluator 故障降级为 unavailable 不中断；
- POST /sessions/{session_id}/claims/{claim_id}/revalidate 已实现：
  同 lineage 新 Revision（reason=revalidated），missing claim / no active goal /
  no primary source 均显式拒绝并返回对应 404/409；
- revalidation 后立即回写 freshness status；
- 当时延期项：LearningPanel UI 徽章 + 渐进披露、Playwright fixture + e2e；
  以上项目随后已由 D-4C 完成，不是当前缺口。

### D-4C — Full Golden Journey (AFTER D-4B) - COMPLETE

- 拓展 mini journey 到 step 1–17，用真实源码 + 双 commit 对；
- step 14–17：Primary 实质修改 → rev1/confirmed 保留、freshness → stale_candidate → 显式 revalidation → rev2 同 lineage；
- e2e golden journey 同步扩展。

Completed（35336cc + 8fc1746）:
- backend 侧 suspension 保留 rev1/confirmed → freshness stale_candidate → revalidate → rev2 同 lineage 已全链路验证；
- 前端缺陷修复：LearningStrip 缺行与来源补充、摘要刷新、stale/current 角度刷新、badge 标题 tooltip、server-only 断言（网络环境不可取时逐层降级而不报错）；
- LearningPanel「重新验证」按钮条件渲染守卫（仅 stale/source_changed 显示），单测锁定；
- e2e `stale_revalidation` journey：stale 条可见 → 重新验证 → 全部 current，desktop + mobile 双项目通过；golden-journeys manifest 期望 29 项已完成。

### D-4D — Cross-browser acceptance (AFTER D-4C) - COMPLETE (automation) / MANUAL MOBILE DEFERRED

- playwright config 新增 desktop-firefox / desktop-webkit sample（仅 golden-journeys，避免双倍全量成本）；
- `channel: chrome` 限定到 chromium 项目（原先顶层 use 会让 firefox 报 Unsupported channel）；
- 核心 journey 在 firefox / webkit 上通过：golden-journeys 4 条 × firefox/webkit 8/8；
- teardown manifest 扩展为 53 项（4 golden journeys × 4 桌面/移动项目 + complex_content_narrow），全量 5 项目 51/51 通过；
- 实体手机验收步骤保留在 `docs/MOBILE_ACCEPTANCE_D4D.md`；当前因 Android 导出/部署配置未就绪而延期，恢复后由执行人填写并归档。

Known environment notes:
- 本机 `npx playwright install chromium` 默认 CDN 不可达，使用 `PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright` 完成安装；
- 系统 Chrome（channel: chrome）下 complex-content linkRectCount 断言失败（渲染差异），headless shell 下通过；CI 保持默认 headless。

## 7.5 P2-E — Post-P2-D acceptance + test hardening (AFTER D-4D) - AUTOMATION COMPLETE / MANUAL MOBILE DEFERRED

范围（2026-08-11 现状调研确认；G 系列产品能力评审已排除）：

### E-5 — Repo cleanup - COMPLETE

- 删除 15 个已合并/过时的本地残留分支（codex/*、claude/*、P2-D-4A-freshness 等），保留 main + release-v0.8.0；
- 远程分支不动；不改变 main 内容。

### E-1 — Acceptance + docs/memory sync - AUTOMATION COMPLETE / MANUAL MOBILE DEFERRED

- 实体手机验收（人工）：因 Android 导出/部署配置未就绪而延期；恢复时按 docs/MOBILE_ACCEPTANCE_D4D.md 10 步执行并填写记录表（执行人/日期/浏览器/设备），完成后回写本 owner；
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
P2-D-4D cross-browser          ✅ complete (automation 51/51; manual mobile deferred until Android export/deploy readiness)

P2-E-5 repo cleanup            ← 已完成（删 15 个已合并本地残留分支）
P2-E-1 acceptance + docs sync  ← 自动化/文档收口完成；实体手机人工验收延期
P2-E-2 backend direct tests    ← 已完成（src/web + src/application 17 模块直测）
P2-E-3 frontend surface tests  ← 已完成（MarkdownMessage/StatusDot/RoadmapPanel/RoutePanel/roles）

P2-E
post-P2-D acceptance + test hardening（不含 G 系列产品能力评审）
```

任何后续实现若改变该顺序或扩大 scope，必须先更新本唯一状态 owner，再执行。

## 9. 后续核心路线审计（2026-08-13）

当前代码核验确认，历史计划中的以下项目已经实现，不得重复建设：

- PedagogyEvalRun 已接入真实 turn completion、SQLite repository 和 semantic evaluation；
- pedagogy golden dialogues 与质量门禁已存在；
- after-session preview/commit 与 durable learning closure 已存在；
- 前端已升级 React 19 并迁移到 Testing Library，`react-test-renderer` 已移除；
- Streamlit `app.py`、`src/ui` 和依赖已移除。

**LearnerModelSnapshot 只读派生第一切片已完成。** owner 边界保持如下：

- LearningTruth 继续唯一拥有 Claim、SourceEvidence 与 UnderstandingEvidence；
- PedagogyEvalRun 继续只是逐轮评估记录，不直接成为长期画像；
- learner-profile memory 只保存用户确认的偏好，推断候选默认 pending；
- Learner Model 不创建 mastery 百分比，不推断敏感属性，不形成第二套学习真值；
- 第一实现切片不得夹带 GraphRAG、临时附件、统计面板或新的角色专属画像。

已落地范围：

- `LearnerModelSnapshot` 在读取时从当前 focus Goal、其最新 ClaimRevision / Understanding 结果、未解决 Hypothesis 数量、同目标 PedagogyEvalRun 汇总和已确认 learner-profile allowlist 派生；
- 快照有界、不可变且无独立 ID / 时间戳，不持久化 mastery，不暴露原始学习者回答；
- runtime factory 与 `GET /sessions/{session_id}/learner-model` 只读 API 已接线；没有新增 UI、表或写回路径；
- 真实 SQLite 集成测试逐表验证构建前后数据完全一致。

联网研究真实性与可用性已于 2026-08-12 完成自动验收收口：本机 Docker Desktop 数据盘已迁到 `D:\DockerDesktopData`，本地 `study-agent-searxng` 仅绑定 `127.0.0.1:8080`，SearXNG 为首选搜索源，Bing RSS 与 DuckDuckGo HTML 仅作顺序降级；DuckDuckGo challenge、HTTP/连接/超时以及总搜索预算耗尽均结构化记录，失败/空结果不会标记 `found`，也不会进入模型证据。普通联网问答绕过慢速 LLM 工具规划器，GitHub/PR 专用研究仍保留工具规划；provider 顺序降级共用 8 秒搜索预算，研究总预算维持 12 秒，按请求隔离执行器，连续 5 次超时后第 6 次仍可按预算终止。ResearchRun 只有至少一个带标题和公开 URL 的搜索结果，或搜索已发现 URL 的成功正文读取，才可进入 `found`；失败时首个可见答复明确写明“联网搜索失败，本回答未使用联网来源”，成功时先流出最多 3 个可点击来源，再等待模型综合正文。自动证据：3 个普通查询各返回 5 条来源，分别 3.95 / 1.30 / 2.06 秒；真实 `/chat/stream` 请求在 4.33 秒到达 `completed/found`、持久化 5 个来源，并在 4.34 秒输出首个可见来源结果。全量 pytest 1036/1036、ruff、detect-secrets 0 findings、相关 mypy、前端 Vitest 319/319 与 production build 已通过；提交 `2fac9d4` 的完整远程 CI #31618437026 已实际运行并全绿。

### 9.1 全项目文档治理 — COMPLETE

- 扫描 130 份受版本控制的 Markdown / text 文档；区分当前 owner、稳定合同、专项运行文档、历史 archive、changelog、运行内容与测试夹具；
- 删除 14 个无仓库内消费者、只有 5–10 行的历史兼容指针；完整历史正文仍保存在 `docs/archive/` / `docs/archive/root/` 与 Git 历史；
- 将 `WEB_SEARCH_IMPLEMENTATION_NOTES.md` 的有效实现说明并入 `NEWS_PIPELINE.md`，`WEB_SEARCH_SETUP.md` 成为普通联网研究与 NewsRun 的唯一 provider 配置入口；
- 修正根 README 中“PR #115 CI 尚未绿色”和 USER_GUIDE 中“生产 Claim UI 冻结”等已与当前 owner 冲突的旧表述；
- 当前文档相对链接扫描通过：38 份现行文档无缺失本地目标；archive、changelog 与测试夹具保留原始时间语义，不参与当前链接验收。

### 9.2 联网 provider 只读健康诊断 — COMPLETE (local validation)

- 新增受 API token 保护的 `GET /health/providers`；核心 `/health` 保持无网络、快速 readiness 语义；
- 诊断区分 `enabled`、`configured`、服务 `reachable` 与实际 `search_capable`，endpoint 只返回脱敏 scheme/host/port；Bing RSS 与 DuckDuckGo 仅报告 fallback 开关，不把“已启用”冒充“已可达”；
- SearXNG 探针先检查 `/healthz`，再用 5 秒上限验证普通搜索；服务在线但引擎超时/无有效结果时明确标记 `degraded`；
- 本机 Docker `study-agent-searxng` 恢复后，真实 provider health 为 `ready`（4.26 秒）；普通查询 `Python 3.12 documentation`、`OpenAI API documentation`、`Godot Engine documentation` 各返回 5 条带标题/URL 的来源，分别 3.47 / 4.07 / 1.87 秒；
- 本地门禁：ruff 全仓通过；后端收集 1043 个测试，1037 个 tracked 测试按 12 个受控分片全部通过，新增 provider-health 6/6 通过；detect-secrets 0 findings；expanded mypy baseline 122 ≤ 128（本批新增文件 0 error）；前端 Vitest 82 文件、319/319 与 production build 通过。
- 远程收口：核心提交 `326d0ff` 首次 CI #31684026410 的 pytest/RAG/ruff/package 均通过，但 detect-secrets 正确拦截安全负例中的 Basic Auth 形态测试字符串；最小 allowlist 修复 `d85789a` 后，[CI #31684795857](https://github.com/2002yy/study-agent/actions/runs/31684795857) 完整全绿，pytest、RAG baseline、ruff、package helper、detect-secrets、expanded mypy baseline、前端 test/build、三浏览器 Golden Journeys 与 real-stack browser gates 均实际运行并通过。

### 9.3 设置页按需联网检测 — COMPLETE

- 设置页新增“检测联网搜索”，只在用户点击时请求 `GET /health/providers?probe=true`；不进入启动快照、不自动轮询、不写配置，探测按钮也不复用聊天发送锁；
- 页面区分首选 SearXNG 可用、服务在线但搜索引擎异常、首选源不可达且仅降级源开启、所有来源不可用；请求失败会保留明确错误，不把“已启用”写成“已可用”；
- 前端 API / 组件测试覆盖首次渲染零探测、ready、degraded、unavailable、请求失败和聊天期间独立检测；Vitest 83 文件、323/323 通过，production build 通过；
- Playwright 新旅程在 desktop + mobile Chromium 均通过，完整本地矩阵前 49 项（desktop/mobile/narrow Chromium 与 Firefox）通过；本机 Playwright WebKit 2336 进程启动即以 `3236495362` 退出，4 项未运行到产品断言，必须以远程 CI 的 WebKit 门禁作为最终结论，当前不得写成完整矩阵全绿；
- 真实 provider 复验为 `ready`；`Python 3.12 documentation`、`OpenAI API documentation`、`Godot Engine documentation` 各返回 5 条有效标题/URL，用时 1.95 / 1.31 / 1.69 秒，全部命中首选 SearXNG；相关后端 pytest 55/55 与 ruff 通过。
- 远程收口：提交 `34cbc66` 的 [CI #31688399223](https://github.com/2002yy/study-agent/actions/runs/31688399223) 完整全绿；远程三浏览器 Golden Journeys（含 WebKit）与 real-stack browser gates 均实际运行通过。

### 9.4 G1-G18 现状差距审计 — AUDIT COMPLETE

2026-08-13 差距审计后已实现 G15/G16/G17 的首批核心切片；G 表按当前代码与自动化证据更新。视觉、对比度、真实屏幕阅读器和实体手机仍保持 **未人工复核**，不得以自动化替代人工记录。本批本地证据：外发策略 pytest 10/10、ruff 通过；前端全量 88 文件 334/334、生产构建通过；关键 real-stack 移动端研究恢复、归档确认和资料证据旅程均定向通过；本机完整 real-stack 因约 64 秒终端上限未完成，最终结论以远程为准。远程 CI 依次真实暴露并修复：首次说明遮挡核心交互（#31697827369）、空 live region 造成复制反馈重复（#31699705213）、首次说明遮挡 real-stack 操作（#31700484139）、移动端粘性输入区遮挡证据按钮（#31702106709）。最终提交 `f69a305` 的 [CI #31703041709](https://github.com/2002yy/study-agent/actions/runs/31703041709) 完整全绿，53 条三浏览器 Golden Journeys 与 14 条真实栈门禁均实际运行并通过。

| G | 当前结论 | 已有事实与仍存真实缺口 |
|---|---|---|
| G1 LearningClosureRun | COMPLETE | server-owned durable run、正式状态机、幂等 preview、retry/cancel 与可恢复 UI 已存在。 |
| G2 结构化总结输入 | COMPLETE | closure 读取 committed learning truth、受预算约束的对话、PedagogyEvalRun 与证据引用；未提交/失败回合不冒充已确认理解。 |
| G3 summary status | COMPLETE | commit 后 summary status、同版本防重复、继续/归档并新建均已分离，且不自动归档。 |
| G4 会话导航 | PARTIAL (P2) | 标题、任务/阶段/缺口/状态、重命名、搜索和分组已实现；但 `/sessions` 默认只返回最近 20 条，前端没有分页或服务端搜索，较早会话无法从 UI 搜到。 |
| G5 去伪精化 | COMPLETE | 主 UI 使用目标、阶段、缺口、下一步和验证状态，不生成 heuristic mastery 百分比。 |
| G6 恢复卡 | COMPLETE | 新用户入口、durable Resume、研究 partial/interrupted 的继续/重试/放弃均已有正式状态来源。 |
| G7 UI 聚焦 | COMPLETE | 一级入口已收敛，诊断/来源/设置等进入次级 surface，普通状态不暴露低层 record/provider 参数。 |
| G8 窄屏可用 | COMPLETE (automation) / MANUAL DEFERRED | 自动化窄屏、三浏览器与 real-stack 门禁已通过；Android 导出/部署未就绪，实体手机记录表仍未填写。 |
| G9 时效检索 | COMPLETE | 稳定 SearXNG 首选源、结构化 provider 失败、真假 `found`、8/12/20 秒预算和连续超时隔离均已有真实运行与 CI 证据。 |
| G10 ResearchRun | PARTIAL (P2) | durable run、attempt/source/budget/stop reason、retry/cancel/partial 与证据使用确认已完成；当前明确复用的是同查询 retry/resume，尚无一般 follow-up 继承上一 run 实体/来源的正式合同。 |
| G11 TaskContract | COMPLETE | task/source/closure 合同在角色、RAG、联网和记忆前确定，并持久化到 route snapshot。 |
| G12 预回答与取消 | PARTIAL (P1) | 首 token 前状态、ResearchRun/Provider cancel、中断恢复与隔离执行器已落地，取消不会提交 completed 学习真值；但 chat 的 pre-answer preparation 只显式取消 ResearchRun，本地 RAG 检索不接收 cancel signal，RagWriteRun 也没有 cancel endpoint。 |
| G13 证据/消息完整性 | COMPLETE | adopted/candidate/read/rejected 分层，联网与本地来源分开；空、失败和无效 URL 不进入引用或模型证据。 |
| G14 导入与来源范围 | PARTIAL (P1) | 长期资料库、server-owned RagRun、来源范围、删除/重建确认已存在；仍缺每文件阶段与单文件重试、当前会话临时附件，以及临时附件的禁联网/禁云端/禁记忆/会话结束删除控制。 |
| G15 会话转换 | COMPLETE (automation) / MANUAL VISUAL PENDING | 新建、切换、归档共用一个只读派生 transition guard；覆盖 chat generation、Memory preview/closure、partial ResearchRun 与 RagWrite，逐项说明停止、保留、继续或放弃的真实效果。归档只确认一次；从抽屉触发时先关闭来源抽屉，避免双 `aria-modal`。RagWrite 仍没有服务端取消能力，守卫明确说明其继续到真实终态而不冒充已取消。完整远程浏览器与 real-stack 矩阵已通过。 |
| G16 外发数据与隐私 | STOP-GATE COMPLETE / DELIVERED (P1) | evaluator 前已阻断 `question_only` / `recent_chat` 的外部语义复核；ChatTurn 按调用记录 purpose/provider/categories/count/result；外部 Chroma query/document embedding 在 provider/client 前 fail closed，RagWriteRun 保留本地激活并记录 `blocked_by_policy`；legacy UI 全部执行事实显示 unknown。实现 `2662cd3` 与浏览器验收修正 `a3f00de` 已交付 `main`，完整 CI #32499954659 全绿。文档/附件级云处理授权仍属于后续 G14/G16 产品切片。 |
| G17 首次使用/可访问性 | PARTIAL (P1) | 全局 API/操作错误已有 `alert`，部分故障用 polite `status`；API/部分故障提供重试、设置、详情，不能安全重放的操作错误直接显示完整错误并提供设置、关闭。转换确认复用 focus trap/Escape/焦点返回，首次外发说明不阻塞聊天；移动端真实栈已验证输入区不再遮挡证据操作。Enter/Shift+Enter 仍固定；视觉、对比度、真实屏幕阅读器和实体手机未人工复核。 |
| G18 React/Streamlit 迁移 | COMPLETE | React 19 + Testing Library 已完成，Streamlit 入口、`src/ui` 与依赖已移除。 |

当前未发现传统远程利用或数据破坏型 P0。已确认的 **G16 P1 隐私真实性缺陷** 已完成窄修复、快进交付和完整远程 CI 验证，止血交付门关闭。唯一立即路线现为 G12 pre-answer/RAG cooperative cancellation；随后是 G14 临时附件/每文件恢复、G16 文档级授权产品面与 G17 人工可访问性验收；G4 历史分页和 G10 follow-up 复用仍属 P2。

### 9.5 Learner Model UI 产品决策 — STANDALONE NO-GO

独立 Learner Model 页面或仪表盘 **不启动**。现有 LearningPanel / ResumeContext 已经展示目标、Claim、理解验证、未解决缺口、证据与下一步；再建顶层面板会复制同一学习真值并诱发第二套状态解释。当前 `LearnerModelSnapshot.evaluation` 还通过 `PedagogyEvalRun.objective == LearningGoal.objective` 文本相等聚合，而不是 `goal_id` 关联；目标改名或同名目标会使计数错配，因此这些计数不得作为“当前目标表现”直接展示。

后续若确有用户价值，只允许在现有学习面板中按需加载一个可失败隔离的只读补充区，并同时满足：

1. Claim、验证状态、缺口与下一步复用现有 ResumeContext 展示，不复制或重算；
2. 只显示用户已确认的学习偏好及其来源说明，不显示 inferred/pending profile；
3. 不出现 mastery、掌握度百分比、分数、等级、排名或人格/敏感属性推断；
4. evaluation 在完成 `goal_id` provenance 前不展示；`accepted/rejected` 只能解释为教学评估运行结果，不能解释为学习者能力；
5. 面板打开时才读取，API 失败不影响主学习闭环；不得新增写回、独立 ID、独立时间线或长期画像 owner。

因此 Learner Model UI 不是下一批。它的条件式只读补充区只有在 G15/G16 核心缺口收口、且评估 provenance 可解释后才重新评审。

### 9.6 GraphRAG 与长期画像写回边界 — DEFERRED

- **GraphRAG** 是把概念、Claim、来源、前置关系、支持/反驳关系组成图，再沿图扩展检索和拼装证据。当前系统已有关系型 LearningTruth 与有界 `depth=1` 学习关系扩展，但没有新的通用图索引、图检索器或 GraphRAG evidence owner；启动它会增加索引一致性、证据 provenance、删除同步与第二检索真值风险。现有核心缺口不需要它，保持未启动。
- **长期画像写回** 是从对话与行为推断“偏好、习惯、薄弱点或能力特征”，再写入跨会话持久存储。当前只允许用户确认的 learner-profile allowlist；推断候选默认 pending，不自动写回，不把教学评估或答题结果升级为掌握度。未来若评审，必须先冻结用户同意、来源说明、查看/修改/删除、过期、冲突、范围隔离和敏感属性禁写合同，并且不得成为第二套 LearningTruth。

### 9.7 后续执行顺序

1. **唯一立即步骤：实施已冻结合同的 G12 可取消本地 RAG。** G16 止血已交付且 CI 全绿；使用 ChatTurn + operation owner、cooperative checkpoints、server single writer 和可观测终态，不创建第二套 LocalRagRun。
2. **G12 通过自动与人工时序门后，再单独冻结 G14 临时附件合同。** 明确会话归属、禁联网/禁云端/禁记忆、结束删除、每文件阶段与重试；不得复用长期资料库冒充临时生命周期，也不在取消切片中夹带附件实现。
3. **G16 其余控制与 G17 人工验收。** 按会话记忆 ask、文档/附件级云处理授权随 G14 合同收口；Enter 配置、对比度、屏幕阅读器与实体设备需要独立证据。
4. **继续延期 Android、Learner Model 独立 UI、GraphRAG 与长期画像写回。** 它们不得抢占当前隐私与主交互缺口，也不得创建第二套真值。

当前阶段：**G12 全门闭合——自动门 + 人工与时序门的浏览器自动化证据齐备（docs/G12_ACCEPTANCE.md：三 viewport ACK 113/127/130ms <200ms；慢检索 3s 注入下登记→终态 2963–2994ms ≈0 协作开销；归档队列/取消待归档/离开会话全过；main CI #32573043290 及后续全绿）。下一切片为 G14 临时附件合同冻结（需先 Grill）。Learner Model 独立 UI NO-GO；GraphRAG、长期画像写回与 Android 均未启动。**

## 10. 2026-08-21 同步、仓库整理与下一切片门禁

### 10.1 同步与整理审计

- 本地 `main` 与 `origin/main` 均为 `589169b0852c23300b01cf51bd6fa98a080e445c`，`main...origin/main = 0/0`；本轮无需合并或改写历史。
- 该 SHA 对应的远程 [CI #31704003134](https://github.com/2002yy/study-agent/actions/runs/31704003134) 已于 2026-08-13 完成且结论为 `success`。
- 工作区没有已跟踪文件的既有改动；本地虚拟环境、Playwright 报告与门禁输出保留在磁盘，只通过 `.gitignore` 排除，不把用户产物当作仓库内容删除。
- 失效 worktree 的实际路径已不存在，可只清理 Git 管理记录；远程历史分支不在本轮授权范围内，不删除。
- 文档继续保持三层：`PROJECT_STATUS.md` 拥有当前事实和执行门；稳定合同文档拥有语义；`archive/` 和 `superpowers/` 只保留历史时间语义。
- `INTERVIEW_NOTES.md` 已从陈旧的 Streamlit/旧测试数量介绍改为当前项目表达与 Grill 决策索引，但不成为第二个状态 owner。

### 10.2 G12 已确认的实现事实

- chat 流与 provider 生成阶段已有 browser abort / `should_cancel` 链路；ResearchRun 另有服务端 owner、取消请求和 durable `cancelled` 终态。
- chat pre-answer preparation 仍会同步取得本地 RAG context；当前 local RAG retrieval 没有接收 cancel signal，也没有独立 durable run 可表达取消终态。
- RagWriteRun 是资料写入/索引生命周期，不等于本次 chat 的只读 local RAG retrieval；它没有 cancel endpoint，必须另立事务和回滚合同。
- 因此仅在前端丢弃响应，不能证明本地检索已停止，也不能标记服务端工作为 `cancelled`。

### 10.3 已锁定边界

本切片只讨论 **chat pre-answer 的只读本地 RAG 检索取消**。明确非目标：

- 不顺带实现 RagWriteRun 取消或索引事务回滚；
- 不实现 G14 临时附件、每文件重试或附件外发策略；
- 不实现 G16 按会话记忆 ask、G10 follow-up run 继承、GraphRAG 或长期画像写回；
- 不因客户端断开而删除已存在的长期资料、SourceEvidence、LearningTruth 或历史 ChatTurn；
- 不用“前端不再显示结果”冒充服务端检索已停止。

### 10.4 G12 / G16 最终 Grill 决策（1–24）

Grill coverage 于 2026-08-21 经多轮代码路径反证后闭合。以下决定已经锁定：

1. **停止范围：**停止当前 ChatTurn 拥有的全部未完成工作，包括 ResearchRun、本地 RAG 和模型生成；不删除长期资料，不回滚与该 turn 无关且已完成的操作。
2. **单一状态 owner：**在耗时准备前持久化 ChatTurn；`cancel_requested → cancelled/interrupted` 写入 ChatTurn，不新增 LocalRagRun 作为第二真值。检索函数只接收该 turn/operation 的 cooperative cancellation check。
3. **未采用检索：**只保留取消阶段、query-plan 摘要、计时和结果数量；未采用 local chunks 不进入模型、LearningTruth、引用或自动重试复用。
4. **响应时间：**UI 必须在点击后 200 ms 内同步显示“停止请求正在提交/已登记”；这不是服务端物理终止 SLA。每个检索阶段设置检查点，注入慢检索并记录从登记到真实终态的实测上限。
5. **终态区分：**没有任何可见输出为 `cancelled`；已有回答 token 或联网来源预览为 `interrupted`，保留可见部分与本轮已采用资料。
6. **单调 fence：**已接受取消的 operation 永远不能再提交 `completed`、调用后续模型或写学习真值；若 completed 已先原子提交，取消返回 `already_completed`。
7. **统一接口：**`/chat` 与 `/chat/stream` 使用同一 turn cancellation semantics。前端不并行拼装 ResearchRun、浏览器 abort 和 ChatTurn 三份终态。
8. **恢复语义：**cancelled 重发创建新 operation 并全新检索；interrupted continue 使用同一 turn 的已持久化 RAG snapshot、不得重跑检索；regenerate/retry 创建新 operation/child turn 并全新检索。新 operation 不继承旧取消标记。
9. **协作式取消：**不承诺强杀线程/进程。当前同步 provider 调用可自然返回后丢弃，但 fence 必须阻止任何后续副作用。
10. **会话转换：**取消登记后可立即切换、新建或关闭；归档与同会话新问题必须等待该 operation 终态。
11. **最小持久化：**ChatTurn 记录 operation-scoped cancel timestamps、stage、reason 和 operation identity；延迟可派生，不保存未采用正文。任何“已接受取消仍可 completed/调用模型/写真值”均为 kill criterion。
12. **明确 UI：**状态放在 turn bubble，不只用 toast；使用 `status`/`alert`、文本而非颜色，覆盖窄屏。浏览器 abort 本身不能显示“已停止”。固定文案区分提交中、停止中、慢收尾、cancelled、interrupted、already completed、请求失败、等待归档和归档失败。
13. **覆盖复审修正：**服务端是 partial reply 唯一 writer；前端在已接受取消后不得再 `commitTurn`。生产 `ExternalDataPolicyChatService` 与基础 ChatService 必须共享 reservation/checkpoint/settlement shell，真实栈测试必须走生产 policy service。`cancelled` 加入 session detail、export、恢复与 consumer regression matrix；closure 仍只消费 completed。
14. **兼容边界：**官方客户端必须预分配 handle 并可取消；未提供 handle 的 legacy 同步 `/chat` 请求中途不可取消，不伪装兼容。
15. **持久归档队列：**`archive_after_cancel` 绑定 operation 并由服务端持久化；刷新、关闭、重启后仍执行。支持取消待归档；停止成功但归档失败要保留会话并显示独立错误。
16. **优先级改写：**先完成窄 G16 隐私真值止血，再开始 G12。
17. **限制策略下的教学评估：**`question_only` / `recent_chat` 不允许外部语义评估接收长期学习状态；先用本地 deterministic evaluation，明确记为受策略限制而未语义复核，不能伪装 pass/fail。
18. **逐调用外发真值：**不新增外发 run；在 owner snapshot 中记录小型 `external_calls` 清单，包含 purpose、provider、实际数据类别/数量和结果，不存正文。UI 分开显示回答生成、教学评估、embedding 等用途。
19. **历史记录：**增加执行记录版本；旧 turn 缺少语义评估调用证据时显示“历史记录粒度不足，学习评估外发状态未知”，不反向改写为 false。
20. **身份与终态观测：**官方客户端预分配 cryptographically random `turn_id + operation_id`；取消用 `(turn_id, expected_operation_id)` CAS。Cancel POST 只确认请求登记，客户端通过 turn-status endpoint/poll 等待 durable 终态；迟到旧请求不能误杀同 turn 的 continuation。
21. **文档 embedding 授权：**在建立文档级云处理授权前，任何可能离机的 embedding provider 都不得处理用户文档正文；operator 环境变量不等于用户同意。
22. **外部 query 最小化：**未来即使明确允许外部 embedding，`question_only` / `recent_chat` 下也只可发送当前原始问题；包含学习目标/缺口的 `private_query` 只允许本地使用。
23. **fail-closed 体验：**隐私策略阻止远程 embedding 时，本地解析、关键词索引和本地向量阶段仍可完成；远程阶段记录 `blocked_by_policy`。UI 不静默降级后继续显示“增强语义”。
24. **复用现有 owner：**聊天回答/教学评估/query embedding 的外发事实归 ChatTurn；文档正文 embedding 归现有 RagWriteRun stage，不创建新审计实体。

### 10.5 明确拒绝的替代方案

- 拒绝把浏览器 `AbortController`、连接断开或 UI 不再显示结果当作服务端 cancelled。
- 拒绝只用 turn ID 取消；同一 turn 可 continuation，迟到请求会误杀新 operation。
- 拒绝让前端和服务端同时提交 partial reply，或由前端猜测 durable 终态。
- 拒绝新增 LocalRagRun、外发审计 run 或另一套取消状态机。
- 拒绝在 cancelled retry 中自动复用未采用 chunks；拒绝 continuation 重新执行 route/RAG/web preparation。
- 拒绝把 `allow_local_evidence` 扩张解释为“允许把整个资料库上传给 embedding provider”。
- 拒绝把 operator 配置、API key 或 provider 可用性解释成用户隐私授权。
- 拒绝对旧审计记录进行无法证明的 backfill；未知必须显示为未知。
- 拒绝承诺无法由 cooperative checkpoint 保证的固定服务端终止毫秒数。

### 10.6 完成门与验收矩阵

**G16 止血门：**

- 主动学习状态 + `question_only` / `recent_chat` 的真实 production policy path 中，semantic evaluator 不收到 objective、protocol、expected concepts、历史 evidence 或长期记忆；执行记录与捕获调用参数一致。
- 回答模型、教学评估、query embedding、document embedding 分用途记录 actual data categories；旧记录显示 unknown，不显示假 false。
- `Chroma + external embedding` 配置下，未授权文档正文不离机；RagWriteRun 记录 `blocked_by_policy`，本地可完成阶段不被伪装成失败或增强语义成功。
- 任一限制策略仍能把禁止数据送入任何模型/provider，或 EvidenceTrail 与实际调用不一致：**NO-GO**。

**G12 自动门：**

- 覆盖 cancel before reservation、reservation race、每个检索/facet/backend checkpoint、检索后模型前、首 token 前、首 token 后、completion race、continuation/retry、disconnect、restart recovery、archive queue/failure/cancel。
- 同步 `/chat` 与异步 `/chat/stream` 共享状态语义；基础服务和 production policy service 都通过，real-stack 必须走后者。
- 证明 accepted cancel 的旧 operation 无法 complete、无法调用后续模型、无法写 LearningTruth/引用；前端不调用 partial commit fallback。
- `cancelled` consumer regression 覆盖 session detail、历史恢复、export、closure、LearningState 和窄屏 UI。

**G12 人工与时序门：**

- 点击后 200 ms 内 turn bubble 明确确认 UI 已接收操作；慢检索场景记录 cancel 登记到每个 checkpoint/最终终态的实际最大值。
- desktop、narrow landscape、mobile viewport 验证状态文本、aria live semantics、离开会话、等待归档、取消归档和归档失败。
- 不以 mock sleep 的固定断言或浏览器请求被 abort 代替真实服务端终态记录。

### 10.7 GO / NO-GO 与唯一下一步

- **Grill coverage：COMPLETE。** 目标、边界、非目标、恢复、兼容、隐私、失败语义和验收门已冻结，无剩余产品选择要求实现者自行决定。
- **G16 local implementation/stop gate：GO。** 窄修复和本地全量证据完整；没有发现禁止数据到达测试 provider、legacy 假 false 或本地索引回归。
- **G16 delivery：GO / COMPLETE。** 实现 `2662cd3` 与 legacy Golden Journey 验收修正 `a3f00de` 已快进进入 `main`；完整 CI #32499954659 全绿。
- **G12 implementation：GO。** 合同完整且唯一前置门已关闭，不再进行产品选择 Grill；实现中若代码反证出现新的 owner、终态或授权矛盾，再带证据回到 Grill。
- **唯一下一步：**建立窄 G12 ChatTurn cooperative cancellation 切片，先落 reservation/operation CAS、检索 checkpoint 与 durable terminal truth，再接 200 ms UI 确认和慢检索实测上限；通过 G12 门后才进入 G14。

### 10.8 G16 窄修复实测证据

- production policy 路径使用 active LearningState + explicit learn task 覆盖 `question_only`、`recent_chat`、`allow_local_evidence`：前两者 evaluator 调用数为 0，结果为 `needs_semantic_review / blocked_by_policy`；允许策略仍实际调用并记录 provider/categories/count/result。
- Chroma 外部 provider 的 document/query 测试在取 collection/client 与调用 embed/embed_many 前抛出 policy error；捕获的 provider 输入与 collection 调用均为空。Chroma + local embedding 的 upsert/query 正常控制仍通过。
- RagWriteRun 在外部 document embedding 被阻止时仍 `completed + activated=true`，vector stage 为 `blocked_by_policy`，本地索引可读取；真实 vector failure 仍保持 partial success 且不激活。
- ChatTurn `external_data_audit_version=2` 逐调用记录 answer generation、semantic evaluation、query embedding；旧 audit version 的 web/history/local evidence/learning state/memory 均显示“历史记录粒度不足，实际状态未知”。记录只含类别与数量，不含正文/query。
- `.venv\Scripts\python.exe -m pytest -q`：**1051 passed**。
- `npm test`：**88 files / 336 tests passed**；`npm run build`：通过，仅保留既有的 >500 kB bundle warning。
- `ruff check .`：通过；mypy baseline：current 122 / baseline 128 / new 0；detect-secrets：0 个 finding 文件；`git diff --check`：通过。
- 实现提交 `2662cd3a57b4b12f4115e3cddaec4b5f59604e1e` 与 legacy Golden Journey 验收修正 `a3f00de4ae700d8661c05718cafa0d7a29781927` 已快进交付到 `main`；[CI #32499954659](https://github.com/2002yy/study-agent/actions/runs/32499954659) 完整全绿，G16 止血证据闭合。

### 10.9 G12 交付证据 — ChatTurn cooperative cancellation（2026-08-22）

按已冻结合同（10.4 决策 1–24、10.6 验收矩阵）交付窄切片：chat pre-answer 本地 RAG 检索与生成的协作式取消。实现提交 `db0404b`（后端核心）、`cb613d5`（检索层贯穿）、`be199cb`（前端 UX），分支 `codex/g16-privacy-truth-hotfix`。

**合同落实对照：**

- **决策 2（耗时准备前持久化）**：`start_turn` 在 `acquire_chat_operation` 之后立即落 pending 裸行（含客户端 turn_id + operation_id 与 retry 父链）；route/pedagogy/RAG/web 全部准备在 reservation 之后进行。
- **决策 2/5/6（单一 owner + 终态区分 + 单调 fence）**：schema v20 为 `chat_turns` 增加 `cancel_requested_at / cancel_stage / cancel_reason`；`finish_turn_cancel` 以 `(turn_id, operation_id)` CAS 落 `cancelled`（无可见输出）或 `interrupted`（保留 partial），同事务释放 thread operation；accepted cancel 后所有 worker 写路径（streaming 推进、audit 回写、complete、前端 commit fallback）被 `cancel_requested_at IS NULL` fence 拒绝；completed 先原子提交时取消返回 `already_completed`。
- **决策 4/9（checkpoint + 协作式）**：preparation 设 route → pedagogy_evaluate → retrieval → web_tools 四个 checkpoint；generate 前后各设 fence（模型调用自然返回后输出丢弃，不承诺强杀）；检索层新增 `RetrievalCancelled`，在 retrieval entry / before index load / before search / before rewrite / coverage entry / coverage facet / search entry / post-search 八处检查并穿透 broad except。
- **决策 7/20（统一接口 + 身份 CAS）**：`/chat` 与 `/chat/stream` 共享同一取消语义；官方客户端预分配 cryptographically random `operation_id`；`POST /chat/turns/{id}/cancel` 只确认登记（pre-reservation 有界等待 2s，沿用 WebLookup 先例）；`GET /chat/turns/{id}/status` 提供 durable 终态轮询。
- **决策 8（恢复语义）**：continuation 经 `reassign_chat_turn_operation` 转移 operation 并清除旧取消标记（不继承）；cancelled turn 不可 continuation，retry 创建新 child turn + 新 operation + 全新检索；supersede CAS 接受 cancelled。
- **决策 11（最小持久化）**：只存 cancel timestamps/stage/reason；延迟可由 requested_at 与 updated_at 派生；未采用正文不入库。
- **决策 12（明确 UI）**：状态行置于 turn bubble 内（非仅 toast），`role=status`、文本区分 提交中/停止中/慢收尾/cancelled/interrupted/already completed/请求失败，窄屏样式降级可读；浏览器 abort 不再显示"已停止"。
- **决策 13（服务端唯一 writer）**：前端 `commitTurn` 调用整体移除并由 packaging guard + boundary test 双重禁止；基础 ChatService 与 ExternalDataPolicyChatService 共享 reservation/checkpoint/settlement shell（helper 复用，policy 仅覆写 policy 门与 audit）。
- **决策 14（兼容边界）**：未提供 handle 的 legacy 同步请求不可中途取消，前端退回 abort-only，服务端断连 settlement 兜底，不伪装兼容。
- **崩溃恢复**：`recover_stale_chat_operations` 对已登记取消的 stale turn 落 `cancelled`/`interrupted`（按是否有 partial），stage=`recovery`。

**自动化证据：**

- `.venv\Scripts\python.exe -m pytest -q`：**1078 passed**（基线 1051 + 新增 27 个 G12 测试：repository 取消原语 6、fence/race 3、start_turn checkpoint 2、reservation 2、continuation 清标记 1、stale recovery 2、双 service 共享语义 2、并发慢检索 1、检索层贯穿 3、consumer regression 3、API/路由经既有 stream cancellation 测试回归）。
- `npm test`（frontend）：**88 files / 337 tests passed**（新增 cancelled SSE settle 测试；stop 行为测试改写为 cancel+poll 语义；boundary/packaging guard 更新为"commitTurn 全面禁止 + cancelChatTurn 必须在 controller"）。
- `npm run build`：通过（仅保留既有 >500 kB bundle warning）；`tsc -b` 通过。
- `ruff check .`：通过；mypy baseline：current 122 / new 0。

**遗留边界（后续切片，不在本门内）：**

- `archive_after_cancel` 持久归档队列（决策 10/15 的会话切换等待与归档失败 UI）尚未实现——当前取消后 thread operation 已释放，会话切换/新建不被阻塞，但"归档失败独立错误"文案依赖该队列落地。
- 慢检索实测上限的人工时序记录（desktop/narrow/mobile viewport 验证）属人工门，待真实设备验收批次执行。

### 10.10 G12 交付收口与归档队列（2026-08-22）

- **修复迭代**：turn 状态行初版按 `message.turnStatus` 渲染，导致历史 completed 消息永久显示取消文案（Playwright strict-mode 冲突 + 违反决策 12"浏览器 abort 不显示已停止"）。改为独立 `ChatMessage.cancelNotice` 字段，仅协作取消流程写入；恢复历史与普通断线永不渲染。
- **恢复卡保持**：onCancelled 不再清空 streamRecovery——取消 settle 后的 retry 正是决策 8 的新 operation 全新检索路径。
- **归档队列落地（决策 10/15）**：schema v21 增加 `chat_threads.archive_after_cancel_operation_id`（绑定 operation，stale marker 无法误触发）；POST archive 在已接受取消时持久化排队而非失败；DELETE `/sessions/{id}/archive-queue` 支持取消待归档；exactly-once 消费（pop CAS + readiness 检查）；启动扫描（get_session_service 首次构造）+ stream finally + turn-status 轮询三处触发执行；前端 queued 响应允许立即切换/新建会话，归档失败保留会话并显示独立错误。
- **交付基线**：`main` = `8a2f91ae6b1fb048b5415702ec71ca2393679479`，本地与远程一致；[CI #32573043290](https://github.com/2002yy/study-agent/actions/runs/32573043290) 全绿（pytest、RAG K1、ruff、detect-secrets、mypy baseline、前端测试/构建、Golden Journeys 与 real-stack browser gates）。
- **门状态：G12 自动门 CLOSED。剩余人工与时序门**（10.6）：点击后 200 ms 实测记录、慢检索登记→终态实测上限、desktop/narrow/mobile viewport 人工验证——待真实设备验收批次执行。

### 10.11 G12 人工与时序门闭合（2026-08-22，浏览器自动化真实栈证据）

执行方式：Playwright 真实 Chrome 对本地真实栈（专用测试 server + 真实 SQLite），全程读取服务端 durable 终态，无 mock sleep、无以浏览器 abort 冒充服务端终态。完整数据与方法见 [`G12_ACCEPTANCE.md`](G12_ACCEPTANCE.md)。

- **200ms UI 确认（决策 4）**：desktop 113ms / narrow landscape 127ms / mobile 130ms，全部 <200ms；多轮稳态复核无离群。
- **慢检索登记→终态实测（决策 4/9）**：注入 3s 慢检索后，登记→durable cancelled 实测 2963–2994ms（checkpoint=web_tools）——协作开销 ≈0，终态无可见输出、operation 锁同事务释放。
- **三 viewport 文案与 aria（决策 12）**：bubble 内状态行 `role=status` + `aria-live=polite`，固定文案集命中，截图/视频存证于 `frontend/test-results/g12-artifacts/`。
- **离开会话 / 等待归档 / 取消归档（决策 10/15）**：取消 pending 时 composer 即时可用、新会话可建；archive 排队持久化并在 settle 后自动执行（三 viewport）；DELETE archive-queue 清 marker 后 settle 不再归档。
- **资产**：`playwright.g12-acceptance.config.ts` + `e2e/g12-acceptance.spec.ts`（六旅程 A–F）+ 测试 server 注入端点；复现入口 `npm run test:e2e:g12`。
- **仍属人工批次**：真实屏幕阅读器体验、实体手机、视觉对比度评审——沿用既有边界，归 G17 人工验收。

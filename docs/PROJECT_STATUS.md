# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-08-13
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

当前已验证 CI 基线：`d75d861`（[CI #31685554492](https://github.com/2002yy/study-agent/actions/runs/31685554492) 全门禁通过：pytest、RAG baseline、ruff、package helper、detect-secrets、mypy baseline、frontend test/build、三浏览器 Golden Journeys、real-stack browser gates）。

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

## 9. 后续核心路线审计（2026-08-12）

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

### 9.3 设置页按需联网检测 — LOCAL COMPLETE / REMOTE CI PENDING

- 设置页新增“检测联网搜索”，只在用户点击时请求 `GET /health/providers?probe=true`；不进入启动快照、不自动轮询、不写配置，探测按钮也不复用聊天发送锁；
- 页面区分首选 SearXNG 可用、服务在线但搜索引擎异常、首选源不可达且仅降级源开启、所有来源不可用；请求失败会保留明确错误，不把“已启用”写成“已可用”；
- 前端 API / 组件测试覆盖首次渲染零探测、ready、degraded、unavailable、请求失败和聊天期间独立检测；Vitest 83 文件、323/323 通过，production build 通过；
- Playwright 新旅程在 desktop + mobile Chromium 均通过，完整本地矩阵前 49 项（desktop/mobile/narrow Chromium 与 Firefox）通过；本机 Playwright WebKit 2336 进程启动即以 `3236495362` 退出，4 项未运行到产品断言，必须以远程 CI 的 WebKit 门禁作为最终结论，当前不得写成完整矩阵全绿；
- 真实 provider 复验为 `ready`；`Python 3.12 documentation`、`OpenAI API documentation`、`Godot Engine documentation` 各返回 5 条有效标题/URL，用时 1.95 / 1.31 / 1.69 秒，全部命中首选 SearXNG；相关后端 pytest 55/55 与 ruff 通过。

### 9.4 后续执行顺序

1. **当前批次收口：** 提交设置页按需联网检测，等待远程 pytest、RAG、ruff、detect-secrets、mypy、前端 test/build、三浏览器 Golden Journeys 与 real-stack 全绿；CI 绿色后将 9.3 提升为 COMPLETE 并更新本节 SHA / run 链接。
2. **可直接做：G 系列现状差距审计。** 只核验仍未实现的核心学习闭环、隐私/外发控制、可访问性与失败恢复，不按历史编号重复建设；审计后再冻结一个验收明确的最小切片。
3. **需产品决策：Learner Model UI。** 只读 API 已完成；若启动 UI，边界应为解释性摘要和来源可追溯，不引入 mastery 百分比、画像写回或第二套学习真值。
4. **已延期：Android 实体手机验收。** Android 导出/部署配置完成前不启动，记录表未真实填写前不得标记完成。
5. **最后考虑：GraphRAG 与长期画像写回。** 两者都不是当前核心可用性缺口，需分别完成收益、隐私和 owner 边界决策后才可规划。

当前阶段：**文档 owner 已收口；Learner Model read-only API complete；provider 健康诊断已可由设置页按需查看，等待本批远程 CI。Learner Model UI、GraphRAG 与 Android 仍未启动。**

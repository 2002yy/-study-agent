# Study Agent 联网研究质量整改任务书（Codex 施工版）

> 状态：**C1–C100 全部冻结**  
> 目标仓库：`2002yy/study-agent`  
> 施工原则：**P0 → P1 → P2 分阶段推进；前一阶段未过验收 Gate，不得进入下一阶段。禁止一次性重构整个联网系统。**  
> 本任务书优先级高于施工过程中临时产生的“更优雅架构”冲动；如发现冻结决策与当前代码存在硬冲突，只允许记录冲突、给出最小替代方案和证据，不得自行改写目标。

---

## 0. 这次整改要解决什么

当前核心问题不是“搜索次数太少”，而是：

1. 第一次搜索命中二手资料后，系统可能过早把“有资料”当成“证据足够”。
2. 来源评估目前主要判断 relevance/directness/可读性，不拥有 claim-aware 证据门槛。
3. Deep Research 的 notes/memo 仍然偏文本拼接，缺少 Claim → Evidence → Gap → Conflict 的结构化研究状态。
4. 最终 synthesis 容易重新自由发挥，造成资料堆砌、因果分析不足、不确定性被抹平。
5. 如果直接靠“更多搜索/更多 read”修复，会显著放大延迟、token 和 provider 成本。

**整改目标：**

把 Deep Research 从：

```text
Planner → Search → Read → Notes → Answer
```

升级为：

```text
Question
→ Claim Plan
→ Gap-directed Search
→ Candidate Pool
→ Read Scheduler
→ Evidence Extraction
→ Claim-Evidence Graph
→ Conflict / Independence Analysis
→ Evidence Gate / Stop Interception
→ ResearchBrief
→ Synthesis
→ Final Claim Audit
→ Answer
```

并保持 Standard Search 的轻量路径，不让所有联网问题都承担 Deep Research 成本。

---

# 1. 不可破坏约束（Codex 必须先读）

## 1.1 禁止一次性大重构

不得在第一批任务中：

- 删除或重写现有 `WebLookupService` 主路径；
- 替换现有 `EvidenceRefV1` / `AnswerClaimV1` 体系；
- 新建一整套数据库表来承载 Claim Graph；
- 默认打开新 Claim Engine；
- 改掉 Standard Search 的行为；
- 为“架构整洁”移动大量现有文件；
- 把 P0/P1/P2 合成一个 PR/一个提交。

## 1.2 复用现有基础设施

当前仓库已有以下资产，优先复用：

- `src/application/web_lookup_service.py`
  - durable `WebLookupRun`
  - checkpoint / resume / cancellation
  - standard/deep research 分流
  - 现有 read budget 与 provider 状态
- `src/web/source_assessment.py`
  - deterministic basic screening
  - relevance / directness / URL dedupe
- `src/web/concurrency.py`
  - `run_bounded()` 有界并发 + request-level timeout
- `src/web/deep_research.py`
  - Deep Research auto-escalation 独立判断层
- `src/domain/evidence.py`
  - server-owned `EvidenceRefV1`
  - server-owned `ClaimEvidenceLinkV1`
  - evidence snapshot 与 known evidence ID 约束
- `src/domain/answer_claims.py`
  - final-answer claim snapshot
  - deterministic claim identity
  - unknown evidence ID 拒绝
- `src/evals/quality_gates.py`
  - fixture-driven eval 基础
- `tests/test_answer_claim_eval.py`
  - claim precision/recall、unsupported claim、unknown evidence link 等现成测试思想

**注意：**
研究阶段的 `ResearchClaim` 与最终答案阶段的 `AnswerClaimV1` 是不同生命周期，**不要强行合并成同一个 dataclass**；但必须复用 server-owned evidence ID、known-ID validation、claim/evidence evaluator 的设计思想。

## 1.3 第一阶段仍存在 WebLookupRun.research_context

新 ResearchState 第一版存：

```text
WebLookupRun.research_context["claim_engine"]
```

必须带：

```json
{"schema_version": 1}
```

不要先拆数据库表。等 schema 稳定且真实体量证明有必要，再单独迁移。

---

# 2. Codex 开源实现：只借 Runtime 思想，不照抄 Research 质量层

本任务书已参考 OpenAI `openai/codex` 当前开源实现（检查时 main 参考提交：`21c58c90f2298587c6519e077d0692ce4c563d37`）。

重点参考文件：

- `codex-rs/core/src/session/turn.rs`
- `codex-rs/core/src/hook_runtime.rs`
- `codex-rs/core/src/session/rollout_budget.rs`
- `codex-rs/core/src/compact.rs`
- `codex-rs/ext/web-search/web_run_description.md`

### 必须吸收

1. **统一 Agent Loop**
   - model requests tool → execute → tool result → continue
   - model attempts final message → system still可拦截

2. **Stop Hook 思想**
   - 模型“认为做完”不等于系统真的允许结束
   - Study Agent 对应 `ResearchStopGate`

3. **PostToolUse 思想**
   - read 成功后立即把结果结构化进入 server-owned ResearchState
   - 不等最终 synthesis 再处理一大坨 notes

4. **Runtime Budget**
   - budget 由 runtime 所有
   - LLM 可见剩余预算，但不能修改 hard ceiling

5. **Compaction / Checkpoint**
   - 压缩 model context，不压掉 durable ResearchState

6. **Steering**
   - 用户中途 steering 要修改结构化 ResearchState / Claim priority

### 不得照抄

Codex OSS 通用 turn loop 中，“model no longer needs follow-up / assistant message only”可以结束；Deep Research **不能**以此作为最终停止依据。

Study Agent 必须：

```text
needs_follow_up =
    model_needs_follow_up
    OR research_gate_blocked
    OR critical_conflict_open
    OR user_steering_pending
```

---

# 3. 冻结决策总表 C1–C100

以下均为冻结需求；标注 `TUNABLE_DEFAULT` 的仅数值可由实验校准，原则不可改。

### C1–C10
- **C1**：停止条件改为 Claim-aware Evidence Gate，而不是“搜到资料/跑够轮数”。
- **C2**：不同 Claim 类型使用不同 evidence requirement；不能一套来源门槛覆盖所有问题。
- **C3**：来源角色至少区分 primary / authoritative_secondary / independent_secondary / community / aggregator。
- **C4**：多源支持按独立来源簇计算，不按 URL 数量；保留 origin/provenance/independence 信息。
- **C5**：后续搜索必须由 Evidence Gap 定向驱动，不做泛化同义改写。
- **C6**：二手来源可作为 lead_source，但不能自动升级为强 evidence；应追原始出处。
- **C7**：Claim 状态至少区分 SATISFIED / PARTIALLY_SATISFIED / UNRESOLVED；后续 C74 增加 UNAVAILABLE。
- **C8**：冲突来源不得多数投票；按来源角色、时间、直接性、独立性、具体性处理，必要时保留 unresolved。
- **C9**：搜索轮数只是预算上限；真正停止依据是 critical claims、gap 饱和、预算耗尽或来源不可得。
- **C10**：最终生成前必须构建 ResearchBrief + Claim-Evidence Binding + Synthesis Planner。

### C11–C20
- **C11**：Claim 采用初始生成 + 研究中受控动态发现。
- **C12**：区分 ResearchQuestion / Hypothesis / FactualClaim / AnalyticalClaim，未验证猜测不得伪装事实。
- **C13**：LLM 提议 Claim/结构，代码拥有 Claim Graph 与状态。
- **C14**：Claim 分 CRITICAL / MAJOR / CONTEXT 优先级；Critical 决定研究闭环。
- **C15**：ClaimEvidenceLink 至少支持 SUPPORTS / CONTRADICTS / QUALIFIES / BACKGROUND / LEAD。
- **C16**：Critical factual claim 的正式 evidence 原则上必须来自成功正文读取，snippet 只能是 candidate/lead。
- **C17**：Evidence Gate 使用 Hybrid：LLM 做语义判断，代码做 deterministic hard gate。
- **C18**：LLM 只能绑定 server-owned evidence IDs，不能自由文本伪造来源。
- **C19**：动态 Claim 必须经过 Proposal Gate，限制范围漂移与预算爆炸。
- **C20**：Claim semantic merge 保留 canonical ID + alias，不能破坏历史引用。

### C21–C30
- **C21**：Source Role 使用 deterministic metadata + LLM semantic classification 的混合判定。
- **C22**：来源独立性按 EvidenceCluster 处理，不按 URL/domain 简单计数。
- **C23**：Critical claim 的强支持/强反驳冲突自动生成 ConflictGap 并优先追更直接/更新来源。
- **C24**：最终答案的重要 factual claim 不得脱离 Claim Graph。
- **C25**：最终回答必须经过 Final Answer Auditor。
- **C26**：ResearchBrief 使用结构化对象，不是自由 rolling memo。
- **C27**：保留现有 EvidenceRef 层；ResearchEvidence/ClaimEvidenceLink/ResearchClaim 建在其上。
- **C28**：第一阶段继续扩展 WebLookupRun.research_context，不立即新建独立 DeepResearchRun/数据库表。
- **C29**：Claim Engine 先 shadow rollout，再 active；必须有 feature flag/模式切换。
- **C30**：建立 40–60 题 Research Quality Benchmark，覆盖来源、冲突、时效、社区、数字、因果和不可回答任务。

### C31–C40
- **C31**：借鉴 Codex Stop Hook：Evidence Gate 作为“结束拦截器”，模型想结束不等于系统允许结束。
- **C32**：Codex 通用 agent loop 可借；assistant-only≈完成不能作为 Deep Research 终止依据。
- **C33**：借鉴 PostToolUse：每次 read 后立即结构化 evidence 入库，不等 synthesis 再处理 notes。
- **C34**：每个 Gap 默认生成 2–4 个并行 query（TUNABLE），按复杂度动态决定。
- **C35**：吸收 Codex 的 primary/citation-direct-support 规则，但关键部分必须由代码 Gate 硬化。
- **C36**：借鉴 Codex compaction：ResearchState 永久保留，模型上下文可压缩成 ResearchCheckpoint。
- **C37**：借鉴 Codex runtime budget：固定轮数升级为 Search/Read/Token/Time 等统一 Budget Controller，并向模型暴露剩余预算。
- **C38**：研究预算按 Claim importance + gap severity + marginal gain 动态分配。
- **C39**：用户 steering 直接修改 ResearchState/Claim priority 和剩余预算，而非只追加自然语言。
- **C40**：借鉴 Codex 统一 Agent Loop + Hook 架构；WebLookupService 最终只做 orchestration adapter，不继续膨胀。

### C41–C50
- **C41**：同一 Gap 的 query 结果先汇总成 CandidatePool，再统一 dedupe/cluster/rank/read。
- **C42**：Query Batch 追求检索意图多样性（Discovery/Primary/Provenance/Verification），不是同义句改写。
- **C43**：Evidence Role/Requirement 是候选排序硬约束，相关性总分不能覆盖角色缺失。
- **C44**：Read Scheduler 优化 Expected Information Gain，而不是仅搜索排名/相关度。
- **C45**：采用小批 Search/Read → Gate → 再决定是否继续的 progressive research。
- **C46**：Deep 默认 soft reads=12、hard cap=16，并保留约 1/3 给 gap/conflict（全部为 TUNABLE_DEFAULT）。
- **C47**：废弃“正文头部截断”作为主要读取策略，改为结构化定位 + claim-aware 局部深读。
- **C48**：raw-read budget 与 model-visible evidence budget 分离。
- **C49**：EvidenceExtractor 默认批处理 2–4 页，不做一页一次 LLM。
- **C50**：EvidenceExtractor 只输出语义关系/跨度/角色建议，不能拥有 Claim 状态。

### C51–C60
- **C51**：连续 2 个 query batches 无实质 Evidence Gain 判 saturation；Critical/Conflict 最多额外第 3 批（TUNABLE）。
- **C52**：Evidence Cache 基于 canonical URL + body hash + extractor version，可跨 run 复用但受 freshness policy 约束。
- **C53**：query concurrency 3–4、read concurrency 3，采用小波次并发（TUNABLE）。
- **C54**：Research 子任务使用 capability routing：research_fast / research_reasoning，不硬编码单一模型。
- **C55**：Final Auditor 最多触发一次 targeted semantic repair，禁止开放式 self-reflection 循环。
- **C56**：soft deadline≈6min、hard≈8min，并为 synthesis/audit 预留时间（TUNABLE）。
- **C57**：Claim Budget 按 importance × gap severity × expected marginal gain 动态分配，不平均切片。
- **C58**：Candidate rerank 必须批量处理 cheap-filter 后的 top-N，禁止每候选一次 LLM。
- **C59**：争议性/因果 Claim 强制一次 counter-evidence pass；普通简单事实不强制。
- **C60**：Dynamic Claim 增加 expected impact / expected research cost gate。

### C61–C70
- **C61**：20 题 Shadow Set 是 P0 诊断实验，不是正式上线判据；正式 release 用 50–60 题。
- **C62**：Benchmark Gold 主要标 question surfaces / claim requirements / source roles / conflicts / forbidden closure，而非固定长答案。
- **C63**：同时建设 Frozen Corpus 回归集和 Live-Web 集成集。
- **C64**：Baseline 与 Shadow/Active 比较必须控制同问题、同时间窗口、同 provider/网络；Frozen 集则使用完全相同 corpus。
- **C65**：False Closure Rate 是 veto metric，超阈值时其他指标再好也不得发布。
- **C66**：Primary Retrieval Rate 只统计“要求且确实存在可公开访问 primary”的 Critical Claims。
- **C67**：Critical Claim Coverage 统计 SATISFIED 或被正确标为 PARTIAL/UNRESOLVED/UNAVAILABLE 的关键面；遗漏才失败。
- **C68**：Critical factual claim Citation Entailment 第一版目标 ≥95%，成熟 ≥98%。
- **C69**：Useful Read Ratio 统计贡献 SUPPORT/CONTRADICT/QUALIFY 或高价值 LEAD 的成功读取页面；首版 >60%，成熟 >70%。
- **C70**：Deep Research P90 elapsed 目标 ≤8min；简单任务可提前结束，不设 3min 下限。

### C71–C80
- **C71**：Research Trace 是一等功能，记录 Claim/Gap/Query/Candidate/Read/Evidence/Gate/Stop/Budget 全链路及理由。
- **C72**：失败原因结构化分类：search/read/access/parse/extractor/budget/time/synthesis/audit/cancel 等，禁止统称 read_failed。
- **C73**：Search provider 瞬时失败 bounded retry 一次，再 fallback；provider failure 不能被解释成“网上没有资料”。
- **C74**：正式 Claim 状态升级为 SATISFIED / PARTIALLY_SATISFIED / UNRESOLVED / UNAVAILABLE。
- **C75**：网页读取采用 bounded fallback ladder：static → alternate extraction → format-specific → optional rendered reader → UNAVAILABLE。
- **C76**：PDF 是一级 document_type，保留 page/section evidence locator。
- **C77**：JS-heavy 页面需要 rendered capability 或替代公开端点；没有能力时标 READ_JS_REQUIRED，不伪装已读。
- **C78**：登录墙/付费墙不绕过；标 READ_LOGIN_REQUIRED，寻找合法公开同源/替代来源。
- **C79**：403/反爬 bounded retry + alternate reader/provider；同域连续 block 启动 domain circuit breaker。
- **C80**：Extractor timeout/invalid schema/provider failure 只 bounded retry；失败页面可为 read_raw，但不能成为 eligible evidence。

### C81–C90
- **C81**：Synthesis 默认只读取 ResearchBrief + Claim Graph projection + ClaimEvidenceLinks + 必要 spans，不重新吃整堆原始网页。
- **C82**：Research Answer 默认 answer-first：先结论，再原因/证据，再细节/不确定性。
- **C83**：后台严格区分 FACT / INFERENCE / JUDGMENT，前台自然表达，不机械套三段标题。
- **C84**：最终文章结构围绕 User Question Surface，而不是围绕搜到的资料主题。
- **C85**：Timeline 只在时间顺序会实质改变解释时生成，不作为固定模板。
- **C86**：因果/争议 AnalyticalClaim 默认构造至少 2 个 plausible competing explanations（除非证据明显单一）。
- **C87**：AnalyticalClaim 必须可向下追溯到 Factual Claims + reasoning relations，不允许“模型感觉如此”。
- **C88**：Community evidence 默认只能证明 observed discourse，不能自动推断 population sentiment。
- **C89**：Citation 贴近其支持的 factual claim，不把多个来源堆到段落末。
- **C90**：有直接 primary 支持时优先单引；多源用于 corroboration/冲突/多视角，而非装饰可信度。

### C91–C100
- **C91**：最终不确定性措辞必须受 Claim State 约束，PARTIAL/UNRESOLVED/UNAVAILABLE 不得被美化成确定事实。
- **C92**：Final synthesis 不具有事实发现权；新事实要么删除/降格，要么在预算允许时返回 research。
- **C93**：后台研究深度与前台回答长度解耦，答案长度由问题复杂度/关键面/解释需要决定。
- **C94**：复杂答案采用 progressive disclosure：核心结论 → 关键分析 → 细节 → 未确认部分。
- **C95**：来源列表不是正文替代品；只有用户要求/报告场景才单列完整来源。
- **C96**：Conflict Synthesis 优先解释冲突产生原因（时间/定义/地域/口径/原始来源），无法解释再保留 unresolved。
- **C97**：Numeric Claim 绑定适用的 value/unit/base/comparison/time/context，禁止裸数字。
- **C98**：Current/news research 分离 event_at / published_at / updated_at / retrieved_at。
- **C99**：Standard Search 与 Deep Research 保持体验/成本边界；只有复杂调查/冲突/因果/决策等进入完整 Claim Engine。
- **C100**：最终 Synthesis 进入 benchmark：Completeness/Analytical Depth/Evidence Discipline/Uncertainty Fidelity/Clarity 各0–2分，均分≥8/10；Evidence Discipline或Uncertainty Fidelity=0则 veto。


---

# 4. 目标内部数据模型（第一版）

P0 只实现必要字段，避免一开始做满所有属性。

```text
ResearchState
├─ schema_version
├─ mode                    # shadow | active
├─ facets[]
├─ claims[]
├─ evidence_links[]
├─ source_clusters[]
├─ gaps[]
├─ contradictions[]
├─ search_attempts[]
├─ trace[]
├─ budget
├─ checkpoint
└─ brief
```

建议最小类型：

```text
ResearchFacet
- id
- question_surface
- importance
- status

ResearchClaim
- id
- facet_id
- text
- kind: research_question | hypothesis | factual | analytical
- importance: critical | major | context
- status: pending | searching | satisfied | partial | unresolved | unavailable | contested
- evidence_requirement
- parent_id
- alias_to
- created_by
- created_reason

ResearchEvidenceLink
- claim_id
- evidence_id
- relation: supports | contradicts | qualifies | background | lead
- strength
- source_role
- source_cluster_id
- locator
- caveats

EvidenceGap
- id
- claim_id
- gap_type
- desired_source_role
- priority
- attempt_count
- status

ResearchTraceEvent
- ts
- event_type
- claim_id?
- gap_id?
- evidence_id?
- reason
- budget_before
- budget_after
```

**Evidence ID 必须引用 server-owned evidence，不允许 LLM 任意生成。**

---

# 5. Feature Flag / Rollout 模式

新增配置：

```text
RESEARCH_CLAIM_ENGINE_MODE=off|shadow|active
```

语义：

- `off`：完全 legacy
- `shadow`：legacy 用户回答不变；Claim Engine 独立记录研究判断/实验数据，不影响 final
- `active`：只对 `research_mode=deep` 启用新控制面

默认必须是：

```text
off
```

直到 P0 Shadow 通过。

---

# 6. P0 —— Contracts + Shadow + 20 题诊断实验

## P0 目标

**不改变用户可见 Deep Research 回答。**

只完成：

1. ResearchState 合同；
2. Claim Planner 最小版；
3. Source Role / Evidence Requirement 最小版；
4. Hard Evidence Gate；
5. Research Trace；
6. Shadow runner / replay harness；
7. 20 题高质量陷阱集；
8. 指标计算；
9. 从现有 Deep Research 输出投影到 Shadow Claim Engine；
10. 能回答“legacy 为什么提前结束”。

P0 不追求完整新搜索调度器，不做生产切换。

---

## P0 新增文件建议

优先采用新子包，**不移动现有文件**：

```text
src/web/research/
├─ __init__.py
├─ models.py
├─ claim_planner.py
├─ source_roles.py
├─ evidence_gate.py
├─ trace.py
├─ metrics.py
└─ shadow.py
```

测试：

```text
tests/research/
├─ test_models.py
├─ test_claim_planner.py
├─ test_source_roles.py
├─ test_evidence_gate.py
├─ test_trace.py
├─ test_shadow.py
└─ test_metrics.py
```

Fixtures：

```text
tests/fixtures/research_shadow/
├─ cases.json
├─ frozen_search/
└─ frozen_reads/
```

工具脚本：

```text
tools/run_research_shadow.py
tools/report_research_shadow.py
```

如仓库现有测试组织规则不允许 `tests/research/` 子目录，可保持平铺，但职责必须相同。

---

## P0 修改现有文件

### `src/application/web_lookup_service.py`

只做最小接线：

- create 时初始化 `claim_engine` context（仅 shadow/active）
- checkpoint 时一起持久化
- deep research 的 legacy 流程保持不变
- shadow mode 在适当 checkpoint 后调用 `ResearchShadowObserver`
- **不得**把现有 `_execute_deep()` 整体重写

### `src/web/source_assessment.py`

P0 不改为“真相判断器”。

只允许：

- 保留 deterministic relevance/directness
- 为新 source-role 层暴露稳定 metadata
- 不把 `evidence_confidence()` 升级成最终 Claim confidence

### `src/domain/evidence.py`

原则上 P0 不改 schema。

如 ResearchState 需要稳定 evidence ID helper，可提取/复用，但不得破坏 `EvidenceSnapshotV1` 兼容性。

### `src/domain/answer_claims.py`

P0 不改主 contract。

仅在 evaluator 复用确有必要时抽取共用 validation helper；不能让 ResearchClaim 直接继承 AnswerClaim。

### `src/evals/quality_gates.py`

不要继续无限膨胀。
优先新增：

```text
src/evals/research_quality.py
```

并从现有 eval runner 接入。

---

## P0 Hard Gate 最小规则

至少覆盖：

1. snippet-only 不能满足 Critical factual claim；
2. `official_statement` 类型 claim 若要求 primary，primary=0 则不能 SATISFIED；
3. unknown evidence ID → schema/validation failure；
4. read failed / extractor failed → 不能成为 eligible evidence；
5. 多个 URL 同源 cluster 只计一个独立源；
6. strong support + strong contradict → CONTESTED/UNRESOLVED，不允许直接 SATISFIED；
7. provider failure → UNAVAILABLE，不等于“没有资料”；
8. no-primary-exists 且 targeted attempts 已饱和 → PARTIAL/UNRESOLVED，可结束；
9. critical claims 必须全部处理后才能允许 final；
10. model-supplied `satisfied=true` 不得覆盖 code gate。

---

# 7. P0 必做：20 题 Shadow Research Experiment

## 7.1 性质

这是 **诊断实验**，不是上线 release gate。

20 题中 1 题 = 5pct，样本太小，不用于宣称最终稳定性。

## 7.2 题型

10 类 × 2 题：

1. secondary-only trap
2. duplicate-source trap
3. old-primary trap
4. conflicting-source / conflicting-primary
5. no-primary-exists
6. community-opinion
7. numerical claim
8. causal-analysis
9. simple factual
10. unanswerable / unverifiable

每题 fixture 至少标：

```text
question
critical_surfaces
claim_requirements
primary_exists
primary_accessible
expected_source_roles
known_source_clusters
known_conflicts
forbidden_closure_conditions
```

不要写死一篇长自然语言标准答案。

## 7.3 对比

```text
Legacy Deep Research
vs
Claim Engine Shadow
```

Frozen replay 优先保证公平；另补一轮 Live-Web 观察 provider/reader 现实问题。

## 7.4 必须记录

```text
False Closure Rate
Primary Retrieval Rate
Useful Read Ratio
Independent Cluster Count
Critical Claim Coverage
Citation Entailment (如当轮已有最终 claim)
Search Count
Query Count
Read Count
Useful Read Count
LLM Calls
Token Usage
Elapsed Time
Stop Reason
Failure Reasons
Budget Exhaustion
```

### Useful Read Ratio

```text
贡献至少一个：
SUPPORTS / CONTRADICTS / QUALIFIES / high-value LEAD
的成功读取页面
/
全部成功读取页面
```

目标第一版：`>60%`，成熟：`>70%`。

## 7.5 P0 退出条件

P0 允许进入 P1 的最低条件：

- 所有 hard-gate deterministic tests 通过；
- Shadow trace 可完整解释每个 false closure；
- unknown evidence ID 无法绕过；
- snippet-only 无法满足 Critical；
- provider failure 与 no-results 可区分；
- 20 题实验完整生成对比报告；
- 没有发现 Claim Engine 无界增长/死循环；
- legacy 用户回答路径在 `off` 和 `shadow` 模式下保持兼容。

**P0 不要求达到最终 Release KPI。**

---

# 8. P1 —— Active Core：Gap-directed Research + Budget + Stop Gate

P0 过后才开始。

## P1 目标

让新 Claim Engine 在 feature flag `active` 下真正控制 Deep Research：

```text
Claim
→ Gap
→ diverse queries
→ CandidatePool
→ rank
→ read waves
→ extract
→ evidence links
→ gate
→ continue/stop
```

Standard Search 保持旧轻量路径。

---

## P1 新增模块

```text
src/web/research/
├─ gap_planner.py
├─ scheduler.py
├─ source_cluster.py
├─ extractor.py
├─ budget.py
├─ checkpoint.py
└─ failure.py
```

### 复用

- `src/web/concurrency.py::run_bounded`
- 现有 gateway/search/read
- WebLookupRun checkpoint/resume/cancel

---

## P1 修改 `src/application/web_lookup_service.py`

目标是**变薄**，但不要一口气拆完。

逐步改为：

```text
WebLookupService
├─ legacy standard path
├─ legacy deep path
└─ claim-engine adapter
```

禁止把所有 Claim/Gate/Scheduler 算法重新塞回此文件。

### 必须移出的新职责

- claim planning
- gap planning
- candidate ranking
- source clustering
- evidence extraction
- gate evaluation
- budget calculation

`WebLookupService` 只做：

- lifecycle
- durable checkpoint
- provider adapter
- cancellation
- feature-flag dispatch

---

## P1 Query 策略

同一 Gap 一批默认 2–4 queries（TUNABLE），但必须覆盖不同 SearchIntent：

```text
discovery
primary
provenance
verification
community
counter_evidence
```

禁止生成四个纯同义改写。

一批结果先汇总 CandidatePool，再：

```text
canonicalize
→ cheap filter
→ dedupe
→ cluster
→ role-fit
→ batch rerank
→ read scheduler
```

### 改掉现有“first non-empty variant break”的行为

只在 Claim Engine active path 改。
Legacy path暂不动，防止 P1 扩散回归范围。

---

## P1 Read Scheduler

排序优先级：

```text
hard evidence requirement
→ source-role fit
→ claim relevance
→ new source cluster
→ expected information gain
→ freshness
→ read cost
```

小波次：

```text
Critical: 初始读 2–3 clusters
Major:    初始读 1–2
Context:  默认不主动深读
```

wave 结束立即 Gate。

---

## P1 Evidence Extraction

禁止：

```text
facts = content[:1200]
```

第一版即使还没有完整 progressive reader，也必须：

1. 对 read body 做 chunking；
2. claim-aware chunk selection；
3. EvidenceExtractor 批量处理 2–4 pages；
4. 输出严格 schema；
5. 写入 `ResearchEvidenceLink`；
6. extractor 失败 → read_raw，不是 eligible evidence。

---

## P1 Source Independence

第一版用启发式 cluster 即可：

```text
canonical URL
origin link
same quoted source
key sentence overlap
same numbers/wording
same official announcement
```

输出：

```text
source_cluster_id
origin_source
independence_score/proposal
```

不用一开始构建完整 citation graph。

---

## P1 Saturation

`TUNABLE_DEFAULT`：

- 连续 2 query batches 无实质 Evidence Gain → SATURATED
- Critical/Conflict 允许额外第 3 批

Evidence Gain 至少看：

```text
new eligible evidence
new independent cluster
better source role
new contradiction
new provenance lead
claim status improvement
```

不是看 result_count。

---

## P1 Runtime Budget

建议默认：

```text
soft_reads = 12
hard_reads = 16

query_concurrency = 3~4
read_concurrency = 3

soft_deadline = 6min
hard_deadline = 8min
```

全部 `TUNABLE_DEFAULT`。

必须预留：

- gap/conflict reserve：约 1/3 read budget
- synthesis/audit 时间 reserve

Budget 由 code 所有；模型只能看到剩余预算、建议如何分配。

---

## P1 Stop Gate

在模型准备结束 / research synthesis 前运行：

```text
ResearchStopGate
```

若存在：

- untreated Critical
- primary-required but primary missing且尚未饱和
- open Critical Conflict
- eligible evidence不足
- extractor pending
- user steering pending

则：

```text
BLOCK_FINAL
+
structured continuation instruction
```

否则：

```text
ALLOW_SYNTHESIS
```

Stop Gate 不接受模型自报“已经够了”。

---

# 9. P1 失败恢复

必须引入结构化 `ResearchFailureReason`：

```text
SEARCH_PROVIDER_FAILED
SEARCH_EMPTY
READ_TIMEOUT
READ_HTTP_ERROR
READ_ACCESS_BLOCKED
READ_LOGIN_REQUIRED
READ_JS_REQUIRED
READ_PARSE_EMPTY
READ_UNSUPPORTED_FORMAT
EXTRACTOR_TIMEOUT
EXTRACTOR_PROVIDER_FAILED
EXTRACTOR_INVALID_SCHEMA
BUDGET_EXHAUSTED
TIME_EXHAUSTED
SYNTHESIS_FAILED
AUDIT_FAILED
USER_CANCELLED
```

### Claim 状态

```text
SATISFIED
PARTIALLY_SATISFIED
UNRESOLVED
UNAVAILABLE
```

### Run 状态语义

```text
COMPLETED
= Critical 都已 satisfied 或 legitimately unresolved

PARTIAL
= 至少一个 Critical 因系统/预算/访问限制未完成

FAILED
= 没有足够 evidence 生成 meaningful grounded answer
```

“事实未知”不得等价为 “系统失败”。

---

# 10. P2 —— Reader/Synthesis/Audit/Production Quality

P1 核心控制面稳定后才做。

## P2 Reader

### 修改

`src/web/article_reader.py`

从单纯 `max_chars_per_article` 逐步升级为 reader boundary：

```text
html_static
article_extract
pdf
rendered_browser(optional)
```

不要删除原接口；可在内部 delegate。

### Progressive Page Reading

废弃头部截断作为主策略：

```text
probe metadata/headings/structure
→ claim-aware locate
→ targeted section deep read
```

Raw-read budget 与 model-visible evidence budget 分离。

### PDF

一级 document_type：

```text
page
section
excerpt/hash
```

进入 evidence locator。

### JS / Login / 403

- JS 无 rendered capability → READ_JS_REQUIRED
- login/paywall → READ_LOGIN_REQUIRED，不绕过
- 403 bounded retry + alternate reader/provider + domain circuit breaker

---

## P2 Cache

新增/复用持久缓存：

```text
canonical_url
retrieved_at
body_hash
body/raw locator
extractor_version
evidence_extraction
freshness_class
```

同 run 禁止重复 read/extract。

跨 run cache 依 freshness policy：
- 稳定技术文档长 TTL
- current news 短 TTL

---

# 11. P2 ResearchBrief + Synthesis

新增：

```text
src/web/research/brief.py
src/web/research/synthesis.py
src/web/research/auditor.py
```

## ResearchBrief

结构化：

```text
question
question_surfaces[]
executive_findings[]
claims[]
  id
  text
  state
  supports[]
  contradictions[]
  uncertainty
unresolved_gaps[]
timeline[]
competing_explanations[]
synthesis_guidance
```

最终模型不得重新读取全量网页堆。

## Synthesis 规则

必须实现/验证：

- answer-first
- question-surface oriented
- FACT / INFERENCE / JUDGMENT 后台分离、前台自然表达
- timeline conditional
- causal/controversial → competing explanations
- community discourse ≠ population sentiment
- claim-near citation
- primary direct evidence 优先
- uncertainty wording 受 Claim State 约束
- final synthesis 不具有事实发现权
- research depth 与 answer length 解耦
- progressive disclosure
- conflict 原因解释
- numeric claim context
- event_at vs published_at 分离

---

# 12. P2 Final Answer Auditor

检查：

```text
Citation entailment
Critical claim coverage
Unsupported new factual claims
Uncertainty preservation
Conflict preservation
Numeric context
Date discipline
```

动作：

- unsupported factual claim → 删除/降格
- missing citation → 修复
- uncertainty lost → targeted rewrite
- major issue → 最多一次 semantic repair
- 禁止无限 critique/rewrite loop

复用 `src/domain/answer_claims.py` 的 server-owned known evidence ID 约束和现有 answer-claim eval 思路。

---

# 13. 50–60 题正式 Release Benchmark

P2/active 生产默认前必须完成。

## 13.1 两套测试

### Frozen Corpus

固定：

```text
search results
page bodies
metadata
access failures
```

用于算法回归、版本对比。

### Live Web

用于：

```text
provider quality
real reader behavior
freshness
anti-bot/access reality
latency
```

---

## 13.2 覆盖类型

至少覆盖：

- current news
- company/product policy
- software/API docs
- academic/research
- game controversy/community
- quantitative/numeric
- historical + current mix
- conflicting source
- duplicate/repost
- no-primary
- unavailable/blocked
- causal analysis
- simple factual control group

---

## 13.3 Release Metrics

### Veto

```text
False Closure Rate <= 5~8%
```

目标成熟 `<5%`。

False Closure 超线，禁止 release。

### Primary Retrieval Rate

定义只统计：
“要求 primary 且 primary 确实存在且公开可访问”的 Critical Claims。

目标：

```text
>= 90%
```

### Critical Claim Coverage

```text
>= 90%
```

“正确标 PARTIAL/UNRESOLVED/UNAVAILABLE”算已处理；
Planner 完全遗漏才是 coverage failure。

### Citation Entailment

Critical factual claims：

```text
>= 95%
```

成熟目标 `>=98%`。

### Useful Read Ratio

```text
> 60%
```

成熟 `>70%`。

### Latency

```text
P90 Deep Research <= 8 min
```

简单任务可远早于 3min 结束。

### Synthesis Human Score

五维，每项 0–2：

```text
Answer Completeness
Analytical Depth
Evidence Discipline
Uncertainty Fidelity
Clarity / Redundancy
```

平均：

```text
>= 8/10
```

Veto：

- Evidence Discipline = 0 → fail
- Uncertainty Fidelity = 0 → fail

---

# 14. Regression Test Matrix

每批提交至少包含对应测试。

## 14.1 P0 deterministic fixtures

必须有：

1. first-round 8 secondary + 0 primary → official claim 不得 satisfied
2. 10 copied articles from one origin → independent cluster = 1
3. official body read supports claim → satisfied
4. snippets only → critical 不得 satisfied
5. read failed → 不得进入 eligible evidence
6. extractor failed → read_raw only
7. old official vs newer official → temporal conflict
8. conflicting independent sources no primary → unresolved/contested
9. community sentiment claim → official-only 不足
10. no primary after targeted saturation → unresolved/partial，可停止
11. one critical satisfied + one untreated → Stop Gate block
12. provider failed → unavailable，不是 no-results
13. unknown evidence ID → reject
14. duplicate claim merge retains alias/canonical
15. dynamic claim cap 生效

## 14.2 P1 integration/replay

必须覆盖：

- query intent diversity
- CandidatePool merge
- hard role requirement before soft relevance
- information-gain ranking
- wave read → gate → next wave
- 2-batch saturation
- conflict reserve
- budget reserve
- 6/8min deadline behavior（fake clock）
- cancellation/resume
- checkpoint restore
- steering changes priority
- domain circuit breaker
- fast/reasoning model routing fallback

## 14.3 P2 synthesis

必须覆盖：

- ResearchBrief 不含 raw-page dump
- unsupported final fact 被 audit
- PARTIAL 不被写成“已确认”
- community discourse 不被写成“大多数玩家”
- conflicting claims 不被 silent majority vote
- numeric claim 缺 base/time 被 audit
- current-event published_at/event_at 区分
- auditor 最多 repair once

## 14.4 现有回归

必须保持：

- WebLookupRun durable lifecycle
- cancellation
- follow-up lineage
- Standard Search
- Deep Research escalation
- existing evidence snapshot tests
- existing answer claim tests
- API contracts
- frontend research progress/steering（如已有相关测试）

---

# 15. 施工顺序与提交纪律

Codex 必须按以下最小批次提交，不允许跳阶段：

## P0-A：Contract only

- models
- schema validation
- evidence ID rule
- unit tests

**不得接生产流程。**

## P0-B：Gate + Trace

- deterministic evidence gate
- research trace
- unit fixtures

## P0-C：Shadow Harness

- shadow observer
- 20-case fixtures
- metrics/report

运行 20 题并产出报告。

**只有人工确认 P0 报告后才进入 P1。**

---

## P1-A：Gap + CandidatePool

- gap planner
- query intents
- candidate merge
- role fit
- clustering basic

## P1-B：Scheduler + Extractor

- read waves
- batch extractor
- eligible evidence
- marginal evidence gain

## P1-C：Budget + Stop Gate

- runtime budget
- saturation
- stop interception
- failure states
- resume/steering

此时 `active` 仍默认关闭。

运行 Frozen + 小规模 Live。

---

## P2-A：Progressive Reader

- section locate
- PDF
- JS/login/block states
- cache/circuit breaker

## P2-B：ResearchBrief + Synthesis

- structured brief
- competing explanations
- answer-first synthesis

## P2-C：Final Auditor + Release Benchmark

- final claim audit
- one repair max
- 50–60 frozen/live benchmark
- release report

只有 Release Gate 通过后：

```text
RESEARCH_CLAIM_ENGINE_MODE=active
```

才可考虑成为 Deep Research 默认。

---

# 16. 每批 Codex 输出要求

每完成一个最小批次，Codex 必须报告：

```text
1. 本批目标
2. 修改文件
3. 新增文件
4. 关键行为变化
5. 没有改变的行为
6. 测试命令
7. 测试结果
8. 新增/更新 fixtures
9. 风险 / 尚未实现项
10. 是否满足该批 Exit Gate
11. git diff 摘要
12. commit SHA（如已提交）
```

禁止只说“实现完成”。

---

# 17. 防范围膨胀规则

施工中若发现额外问题：

### 立即修

仅当：

- 会破坏当前批测试；
- 会导致证据/状态错误；
- 是安全/数据损坏问题；
- 不修无法继续当前阶段。

### 记录 backlog，不在当前批修

包括：

- UI 美化
- unrelated refactor
- provider 全面重构
- 新数据库架构
- 新浏览器引擎
- 多 agent research
- 全局 LLM router 重写
- “顺便”清理整个 web 包

新增 backlog 要写：

```text
发现
影响
为何不属于当前批
建议优先级
```

---

# 18. TUNABLE_DEFAULT：只能通过实验调整

以下数值不是协议，只是首轮默认：

```text
soft reads                 = 12
hard reads                 = 16
gap/conflict reserve       ≈ 1/3
queries per gap            = 2–4
no-gain saturation         = 2 batches
critical extra batch       = 1
query concurrency          = 3–4
read concurrency           = 3
extract batch              = 2–4 pages
soft deadline              ≈ 6 min
hard deadline              ≈ 8 min
Useful Read Ratio target   > 60%
False Closure release      <= 5–8%
```

修改这些数值必须引用：

```text
Shadow/Benchmark before
Shadow/Benchmark after
质量变化
成本变化
```

禁止凭感觉调整。

---

# 19. 最终 Definition of Done

这次联网整改只有同时满足下列条件才算完成：

1. Claim Engine active path 不再因为“第一批结果非空”自动结束；
2. Critical Claim 有明确 evidence requirement；
3. snippet-only 无法满足需正文支持的 Critical factual claim；
4. 需要 primary 时会主动追 primary；找不到能正确 unresolved/unavailable；
5. 重复转载不会被算作多个独立证据；
6. strong conflict 会创建 ConflictGap，而不是多数投票；
7. Search/Read 由 Evidence Gain 调度，Useful Read Ratio 达标；
8. 研究有硬 budget / saturation / deadline，不无限循环；
9. ResearchState 可 checkpoint/resume；
10. provider/read/extractor 失败不会伪装成“网上没有资料”；
11. 最终回答围绕用户问题、answer-first、能做 competing explanations；
12. final factual claims 受 server-owned evidence IDs 约束；
13. uncertainty/conflict 状态不会被 synthesis 抹掉；
14. 20 题 Shadow 诊断完成；
15. 50–60 题 Frozen + Live Release Benchmark 达到 Gate；
16. Standard Search 无明显性能/行为回归；
17. legacy Deep Research 在 flag off 时仍可工作；
18. 所有现有测试 + 新增研究测试通过。

---

# 20. Codex 开工指令（直接执行）

```text
请按照《Study Agent 联网研究质量整改任务书（Codex 施工版）》施工。

硬约束：
1. C1–C100 已冻结，不重新讨论架构。
2. 只做 P0-A：Contract only。
3. 不进入 P0-B/P0-C/P1/P2。
4. 不重写 WebLookupService。
5. 不改 Standard Search 行为。
6. 不替换现有 EvidenceRefV1 / AnswerClaimV1；ResearchClaim 建在其上并引用 server-owned evidence IDs。
7. 第一版 ResearchState 放 WebLookupRun.research_context["claim_engine"]，schema_version=1。
8. 每个新行为必须配 unit test / fixture。
9. 运行相关回归测试；若出现失败，先定位是否由本批引入。
10. 完成后按任务书第16节格式汇报，并停下等待下一批，不自动继续。

开始前先读取并总结与 P0-A 直接相关的当前实现：
- src/application/web_lookup_service.py
- src/domain/evidence.py
- src/domain/answer_claims.py
- src/evidence/evidence_ref.py
- src/web/source_assessment.py
- src/web/deep_research.py
- src/evals/quality_gates.py
- tests/test_answer_claim_eval.py
以及现有 WebLookup/Research 相关测试。

如果现有代码已实现任务书中的某部分，复用并证明，不重复造轮子。
```

---

# 21. 当前仓库基线备注

施工前必须验证 main 当前状态，不得只依赖本任务书描述。

已确认的几个当前基线：

- `source_assessment.py` 当前主要判断 usability/directness，不判断 truth；`worth_reading` 门槛较宽。
- `web_lookup_service.py` 当前存在 query variant 命中首个非空结果后 `break` 的 legacy 行为；Claim Engine active path 要在 P1 改，但 P0 不动 legacy。
- standard research 当前 read budget 默认约 `max_reads=3 / max_chars_per_source=6000 / max_total_chars=16000`；Deep Research 新预算另行控制。
- `concurrency.py` 已有 bounded executor，可复用。
- `deep_research.py` 已有独立 auto-escalation，不纳入 Claim Engine 重构。
- `domain/evidence.py` 已有 server-owned EvidenceRefV1/ClaimEvidenceLinkV1。
- `domain/answer_claims.py` 已有 final-answer claim contract 和 known evidence ID validation。
- answer-claim eval 已覆盖 unknown evidence link、unsupported claim、claim/link precision/recall 等，可复用思想。

---

**执行终点：先完成 P0-A，然后停。**

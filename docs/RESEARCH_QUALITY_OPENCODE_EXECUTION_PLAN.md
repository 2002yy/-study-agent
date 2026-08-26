# Study Agent 联网研究质量整改：OpenCode 详细施工计划

> 适用仓库：`2002yy/study-agent`
> 
> 上位规范：`docs/RESEARCH_QUALITY_CODEX_TASKBOOK.md`
> 
> 状态：C1–C100 已冻结。本文件不重新做架构决策，只把冻结决策拆成适合 OpenCode 小批施工的执行剧本。
> 
> 总原则：**一次只推进一个 batch；每个 batch 独立计划、独立修改、独立测试、独立停机。前一 batch 未通过 Exit Gate，不得自动进入下一 batch。**

---

## 1. 为什么要为 OpenCode 再拆一层

原任务书适合作为“总设计合同”，但如果直接交给 OpenCode 一个长会话执行，仍有几个风险：

1. 模型可能为了“完成任务”跨越 P0/P1/P2 边界；
2. 上下文越来越长后，容易忘记某个禁止项；
3. 同一会话同时规划、施工、审查，容易自我确认；
4. 测试失败时，模型可能继续补丁式改动，逐渐扩大范围；
5. 免费/低价模型更需要短上下文、明确文件边界和可验证结果。

因此 OpenCode 版采用：

```text
总任务书（冻结设计）
        ↓
OpenCode 执行计划（阶段/批次）
        ↓
每批 Task Card（本次唯一允许做的事）
        ↓
Planner → Builder → Reviewer → Tests → Stop
```

---

## 2. OpenCode 使用方式：推荐结构

### 2.1 项目规则

建议后续新增根级 `AGENTS.md`，但只写短规则，不复制 C1–C100 全文。

`AGENTS.md` 负责长期强约束：

- 任何 research-quality 任务必须先读取 `docs/RESEARCH_QUALITY_CODEX_TASKBOOK.md`；
- 再读取本执行计划中“当前 batch”；
- 不得自动进入下一 batch；
- 默认最多修改 4 个 production files + 对应 tests；若超出必须停止并报告原因；
- 不得修改 Standard Search 行为，除非当前 batch 明确允许；
- 不得重写 `WebLookupService`；
- 不得替换现有 `EvidenceRefV1 / AnswerClaimV1`；
- 每批结束必须运行指定测试并输出 diff summary。

### 2.2 不建议把总任务书直接塞进 `opencode.json.instructions`

原因：总任务书很长，若每轮都强制注入，会浪费上下文。

建议：

- `AGENTS.md` 只保留短规则；
- agent 在需要时主动 Read 总任务书相关章节；
- 当前 batch 的 Task Card 可放在 `.opencode/commands/` 或直接作为一次性提示词。

### 2.3 推荐 4 个角色

后续可放到 `.opencode/agents/`：

#### `research-planner`

权限：只读，不编辑。

职责：

- 读取当前 batch；
- 检查现有代码；
- 列出 exact files；
- 给出最小实现方案；
- 列出不可破坏约束和测试；
- **不修改代码。**

#### `research-builder`

权限：允许 edit/write；bash 只开放测试、格式化、git diff/status 等必要命令；git push 必须 ask/deny。

职责：

- 只执行 planner 已批准的当前 batch；
- 禁止顺手清理无关代码；
- 修改后运行 focused tests；
- 失败则修复当前 batch，不扩大范围。

#### `research-reviewer`

权限：只读；允许 `git diff`、测试读取。

职责：

- 检查冻结决策是否被违反；
- 查 False Closure 风险；
- 查 server-owned ID 约束；
- 查 fallback 是否把 UNAVAILABLE 写成 UNRESOLVED；
- 查是否意外改变 Standard Search；
- **不得自己修代码。**

#### `research-benchmark`

权限：可运行 benchmark/test，不允许修改 production code。

职责：

- 执行 20 题 Shadow；
- 后续执行 50–60 题 Release benchmark；
- 输出指标和失败 case；
- 不自行调参。

### 2.4 会话原则

推荐一个 batch 一个新会话，或至少在阶段切换时新建会话。

不要让一个 OpenCode 会话从 P0-A 一路跑到 P2。

---

# 3. 每个 Batch 的固定协议

每批 OpenCode 都执行以下 6 步。

## Step 1：Preflight

必须先输出：

```text
Current batch:
Allowed production files:
Allowed test files:
Forbidden files/areas:
Frozen decisions used:
Current git status:
```

如果工作区已有与本批无关的未提交改动：

- 不覆盖；
- 不 reset；
- 不 stash；
- 报告冲突并仅在安全范围内继续。

## Step 2：Read-only audit

先读代码，不改。

必须回答：

1. 现有实现在哪里；
2. 可以复用什么；
3. 最小新增接口是什么；
4. 哪些现有行为必须保持；
5. 当前 batch 是否真的需要所有计划文件。

## Step 3：Implementation plan

输出 exact diff plan，例如：

```text
CREATE src/research/contracts.py
MODIFY src/application/web_lookup_service.py (仅加入 shadow state bootstrap，不改变 legacy answer path)
CREATE tests/research/test_contracts.py
```

若 production files >4：默认停止，拆成两个 batch。

## Step 4：Implement

只做本批。

## Step 5：Verify

必须按顺序：

```text
focused unit tests
→ affected regression tests
→ formatting/lint/type checks（若仓库已有）
→ git diff --check
→ git diff summary
```

## Step 6：Stop report

固定输出：

```text
Batch status: PASS / FAIL / PARTIAL
Changed files:
Behavior changed:
Behavior intentionally unchanged:
Tests run:
Tests passed/failed:
Known limitations:
Frozen decisions satisfied:
Next batch: <name> (NOT STARTED)
```

然后停。

---

# 4. P0：先建立研究控制面的“骨架”，不改变用户答案

P0 的总目标：

> Claim Engine 能计算、能追踪、能评测，但 legacy Deep Research 仍决定最终答案。

P0 期间 `claim_engine_shadow` 是唯一允许的新模式；不得默认 active。

---

## P0-A0：现状契约审计（只读）

### 目标

确认可复用的事实层和生命周期，避免重复造轮子。

### 必读

- `src/domain/evidence.py`
- `src/domain/answer_claims.py`
- `src/application/web_lookup_service.py`
- `src/web/source_assessment.py`
- `src/web/concurrency.py`
- `src/web/deep_research.py`
- `tests/test_answer_claim_eval.py`

### 输出

`docs/research_quality/P0_A0_CONTRACT_AUDIT.md`

只允许新增这一个 docs 文件；不改 production code。

### Exit Gate

必须明确：

- ResearchClaim 与 AnswerClaimV1 不合并；
- Research evidence 使用 server-owned evidence IDs；
- 第一版 ResearchState 存 `research_context["claim_engine"]`；
- legacy path 的停止条件和输出位置已定位。

**通过后停。**

---

## P0-A1：Research Contracts v1

### 建议新增

`src/research/contracts.py`

### 只实现数据合同，不实现算法

至少包含：

```text
ResearchQuestion
ResearchClaim
ResearchClaimKind
ResearchClaimPriority
ResearchClaimState
ClaimEvidenceRelation
ResearchClaimEvidenceLink
EvidenceGap
ConflictGap
EvidenceCluster
ResearchBudget
ResearchTraceEvent
ResearchBrief（仅 schema，可暂不使用）
```

Claim state：

```text
SATISFIED
PARTIALLY_SATISFIED
UNRESOLVED
UNAVAILABLE
```

### 约束

- schema versioned；
- deterministic validation；
- 不允许任意 evidence ID；
- 不引入数据库；
- 不改 WebLookupService。

### Tests

`tests/research/test_contracts.py`

覆盖：

- round-trip serialization；
- invalid enum；
- duplicate IDs；
- bad evidence relation；
- missing critical fields；
- UNRESOLVED/UNAVAILABLE 区分。

### Exit Gate

所有 tests 通过；production behavior 0 变化。

---

## P0-A2：ResearchState + persistence adapter

### 建议新增

- `src/research/state.py`
- `tests/research/test_state.py`

### 可修改

`src/application/web_lookup_service.py` **最多只加 bootstrap / persist helper 调用**。

### 目标

实现：

```text
research_context["claim_engine"] = {
  "schema_version": 1,
  ...
}
```

支持：

- create empty state；
- load/validate existing state；
- checkpoint round-trip；
- unknown/old schema 安全降级为 shadow unavailable，不影响 legacy。

### 禁止

- 改 legacy stop；
- 改 search/read；
- 改 final synthesis。

### Exit Gate

已有 WebLookupRun regression tests 全绿；旧 run 无 claim_engine 仍可 resume。

---

## P0-A3：Research Trace v1

### 建议新增

- `src/research/trace.py`
- `tests/research/test_trace.py`

Trace event 至少支持：

```text
claim_created
gap_created
query_planned
search_completed
candidate_ranked
read_completed
evidence_extracted
claim_linked
gate_evaluated
stop_blocked
stop_allowed
budget_changed
failure_recorded
```

### 强制字段

```text
timestamp
run_id
event_type
claim_id? / gap_id? / evidence_id?
reason
budget_before?
budget_after?
```

### 目标

先能写 trace，不要求 UI 展示。

### Exit Gate

Trace failure 不能让 legacy research 失败。

---

# 5. P0-B：Evidence Gate Shadow

## P0-B1：Evidence requirement policy

### 建议新增

- `src/research/policy.py`
- `tests/research/test_policy.py`

### 目标

将 C2/C3/C14/C16/C17/C21 等落成明确 requirement。

Community sentiment 与官方事实不能套同一规则。

### 禁止

不做网页 role classifier LLM；只做 contract/policy。

---

## P0-B2：Deterministic Evidence Gate

### 建议新增

- `src/research/evidence_gate.py`
- `tests/research/test_evidence_gate.py`

### 第一版只实现硬规则

输入：ResearchState。

输出：

```text
PASS / BLOCK / PARTIAL
open_critical_claims
gaps
conflicts
reasons
```

必须覆盖：

- Critical 没有 eligible evidence → BLOCK；
- snippet-only 不满足正文要求；
- unknown evidence ID 无效；
- duplicate source cluster 不算多个独立来源；
- strong support + strong contradiction → ConflictGap；
- UNAVAILABLE 不等于 SATISFIED；
- budget exhausted 时可转 partial，但不能假装 satisfied。

---

## P0-B3：Stop interceptor（Shadow only）

### 建议新增

- `src/research/stop_gate.py`
- 对 `web_lookup_service.py` 做最小集成
- `tests/research/test_stop_gate_shadow.py`

### 行为

legacy 准备结束时：

```text
legacy_would_stop = true
↓
shadow gate 计算
↓
记录：
- shadow_would_pass
- shadow_would_block
- missing critical claims
- gap reasons
↓
仍按 legacy 输出
```

### 关键指标

新增：

```text
legacy_would_stop_but_shadow_blocked
```

这就是 False Closure prevention candidate。

### Exit Gate

**用户答案必须与 legacy 完全一致**（除了内部 trace/context）。

---

# 6. P0-C：20 题 Shadow Experiment

## P0-C1：Benchmark schema / frozen fixture format

### 建议新增

- `src/evals/research_quality.py`
- `tests/fixtures/research_quality/README.md`
- `tests/research/test_research_quality_eval.py`

Gold 不写固定文章，写：

```text
question
critical_surfaces
expected_claims
required_source_roles
primary_exists
known_conflicts
freshness_requirement
forbidden_closure_conditions
```

---

## P0-C2：20 个陷阱题

10 类 × 2：

1. secondary-only
2. duplicate-source
3. old-primary
4. conflicting-primary
5. no-primary-exists
6. community-opinion
7. numerical-original-source
8. causal-competing-explanations
9. simple-factual
10. unanswerable/unverifiable

### 要求

至少一半做 frozen corpus；另一半可先只定义 live case metadata。

---

## P0-C3：Shadow runner

记录：

```text
False Closure
Primary Retrieval
Useful Read Ratio
Independent Cluster Count
Critical Claim Coverage
Citation Entailment（如当前阶段可测）
Search Count
Query Count
Read Count
LLM Calls
Elapsed
Failure Reasons
```

P0 阶段未实现新 scheduler 时，Useful Read Ratio 可只记录 legacy baseline。

---

## P0-C4：跑第一次 baseline vs shadow

必须输出报告：

`docs/research_quality/P0_SHADOW_REPORT.md`

重点不是达 Release Gate，而是定位：

- Shadow Gate 是否抓到二手来源提前结束；
- 是否大量误 BLOCK 简单事实；
- Claim planner/fixture 是否遗漏 critical surface；
- 当前数据结构能否解释失败。

### P0 Exit Gate

P0 通过标准：

1. legacy 用户可见行为不变；
2. ClaimState/Trace/Gate 可持久化和恢复；
3. 20 题 runner 可重复；
4. False Closure case 能输出明确 claim/gap 原因；
5. 没有 unknown evidence ID 绕过 Gate。

**P0 未通过，禁止进入 P1。**

---

# 7. P1：搜索与证据调度器（仍先 Shadow）

P1 目标：

> 让 Claim Engine 不只是“判断不够”，还知道“下一步该搜什么、读什么”。

---

## P1-A1：SearchIntent + Gap Planner contracts

### 新增

- `src/research/search_intent.py`
- `tests/research/test_search_intent.py`

结构：

```text
SearchIntent {
  gap_id
  claim_id
  gap_type
  desired_source_roles[]
  time_window
  queries[]
  domain_hints[]
  exclude_domains[]
  attempt
  priority
  query_purposes[]
}
```

query purpose：

```text
discovery
primary
provenance
verification
counter_evidence
community
```

---

## P1-A2：Gap-directed Query Planner

### 新增

- `src/research/gap_planner.py`
- `tests/research/test_gap_planner.py`

### 规则

- 一个 gap 默认 2–4 queries（TUNABLE）；
- 禁止只做同义改写；
- provenance gap 优先追原出处；
- conflict gap 搜最新/直接/原始/反方；
- LLM 失败要有 deterministic fallback。

### 注意

Planner 只生成 SearchIntent，不执行 search。

---

## P1-B1：CandidatePool

### 新增

- `src/research/candidate_pool.py`
- `tests/research/test_candidate_pool.py`

### 复用

`src/web/source_assessment.py` 继续做 cheap deterministic screening。

### 新增能力

- 跨 query 合并；
- canonical URL dedupe；
- query purpose provenance；
- 来源簇 candidate hints；
- 不再 `first non-empty → break`。

### Shadow 集成

先让 legacy 仍按旧 query 执行；new pipeline 可以额外计算 CandidatePool，但不能改变 answer。

---

## P1-B2：Source Role + EvidenceCluster

### 新增

- `src/research/source_role.py`
- `src/research/evidence_cluster.py`
- 对应 tests

### Source roles

```text
primary
authoritative_secondary
independent_secondary
community
aggregator
unknown
```

### Independence

考虑：

- canonical URL；
- 同一官方公告转载；
- 明确引用同一原始来源；
- 高文本重合；
- 相同独家报道源。

不得只按 domain 去重。

---

## P1-C1：Candidate Rank / Expected Information Gain

### 新增

- `src/research/candidate_ranker.py`
- `tests/research/test_candidate_ranker.py`

排序两层：

```text
Hard fit:
- evidence requirement
- desired role
- independence need

Soft rank:
- relevance
- directness
- freshness
- provenance potential
- information gain
- read cost
```

必须有测试证明：official primary relevance 0.70 仍应高于已重复的 secondary relevance 0.99，若当前 gap 明确缺 primary。

---

## P1-C2：Read Scheduler + ResearchBudget

### 新增

- `src/research/scheduler.py`
- `src/research/budget.py`
- tests

### 复用

`src/web/concurrency.py::run_bounded()`。

### TUNABLE_DEFAULT

```text
soft reads = 12
hard reads = 16
reserve ~1/3 for gap/conflict
query concurrency = 3–4
read concurrency = 3
soft deadline = 6min
hard deadline = 8min
```

### Progressive wave

```text
read top 2–3
→ ingest evidence
→ gate
→ only then next wave
```

不得一次启动全部 16 reads。

---

## P1-D1：EvidenceExtractor contracts + batch extraction

### 新增

- `src/research/evidence_extractor.py`
- `tests/research/test_evidence_extractor.py`

输入：2–4 page selected chunks + active claims/gaps。

输出：

```text
evidence_notes
claim relations
anchored spans
source-role proposal
provenance leads
new claim proposals
contradictions
```

### 强约束

- Extractor 不得修改 Claim status；
- returned evidence_id 必须已存在；
- exact/fuzzy anchor 失败 → UNANCHORED；
- UNANCHORED 不满足 Critical hard gate；
- extractor failure → raw read 仍保留，但不是 eligible evidence。

---

## P1-D2：Evidence Progress / Saturation

### 新增

- `src/research/progress.py`
- tests

Material progress：

- 新独立 cluster；
- 更强 source role；
- Critical support/contradiction；
- 时间范围解决；
- 高价值 provenance lead；
- Claim state materially improved。

连续两批无 progress → saturation；Critical/Conflict 可额外一批（TUNABLE）。

---

## P1-E：完整 Shadow orchestration

### 目标

把：

```text
Gap → Query batch → CandidatePool → Rank → Read wave
→ Extract → Link → Gate → next Gap
```

在 shadow 中真正跑起来。

### 集成原则

`WebLookupService` 只调用一个新的 orchestration adapter，例如：

`src/research/orchestrator.py`

不要把上述逻辑继续堆进 `_execute_deep()`。

### P1 Exit Gate

重新跑 20 题 Shadow。

重点检查：

```text
Useful Read Ratio > 60%（第一版目标）
Primary Retrieval 显著优于 baseline
False Closure 明显下降
没有 5–10x 搜索/read runaway
简单 factual 不被过度研究
```

具体参数可调；原则不可改。

P1 未通过不得 active。

---

# 8. P2：Reader、失败恢复、Synthesis 与 Release

## P2-A1：Progressive Reader

### 新增建议

- `src/research/reader.py`
- `src/research/page_selection.py`
- tests

### 替换的只是 Deep Research 新路径

现有 `ArticleReader` / legacy reader 保留。

新 reader 区分：

```text
probe 3–5k useful chars
normal 8–12k
deep primary raw 20–30k
```

但 model-visible 只送 claim-aware selected chunks。

---

## P2-A2：Failure taxonomy + fallback ladder

至少：

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

### 关键语义

```text
UNRESOLVED = 调查后仍无法确定
UNAVAILABLE = 系统/访问条件导致无法验证
```

不得互换。

---

## P2-A3：PDF / JS / 登录墙 / 反爬

### PDF

一级 document type；保留 page/section locator。

### JS-required

若没有 rendered browser capability：标 `READ_JS_REQUIRED`，寻找公开 alternate；不伪装成功。

### login/paywall

不绕过；找公开原文/同源发布稿。

### anti-bot

一次 bounded retry → alternate reader/provider → domain circuit breaker。

---

## P2-B1：Evidence Cache

### 新增

- `src/research/cache.py`
- tests

key 至少：

```text
canonical_url
body_hash
extractor_version
```

search cache 另带 provider/query/freshness TTL。

同一 run 禁止重复读相同 body。

---

## P2-C1：ResearchBrief

### 新增

- `src/research/brief.py`
- tests

结构：

```text
question
executive_findings
claims
supports
contradictions
uncertainty
unresolved_gaps
timeline (optional)
competing_explanations (conditional)
synthesis_guidance
```

最终 synthesis 不再读取全部 raw pages。

---

## P2-C2：Synthesis Planner

### 新增

- `src/research/synthesis.py`
- tests

规则：

- answer-first；
- 围绕 user question surfaces；
- fact / inference / judgment 后台严格区分；
- timeline 仅在时间顺序改变解释时使用；
- causal/controversial claim 至少比较 2 个 plausible explanations；
- community evidence 不自动外推总体玩家；
- citation 紧贴 factual claim；
- claim state 决定措辞强度；
- answer length 与研究深度解耦。

---

## P2-C3：Final Auditor

### 新增

- `src/research/final_auditor.py`
- tests

检查：

```text
critical surface coverage
unsupported new fact
citation entailment
uncertainty fidelity
conflict preservation
numeric context
date discipline
```

最多一次 targeted repair；禁止无限 critique loop。

---

# 9. 50–60 题 Release Benchmark

P2 全功能 shadow 完成后，冻结一套正式 benchmark。

### 两条线

#### Frozen regression

用于 deterministic regression；gate/scheduler/extractor/synthesis 改动比较。

#### Live web integration

用于 provider、search freshness、真实网页读取、站点失败恢复。

### Release Gates

第一版建议：

```text
False Closure             <= 5–8%   [VETO]
Primary Retrieval         >= 90%
Critical Claim Coverage   >= 90%
Citation Entailment       >= 95%
Useful Read Ratio         >= 60%
P90 elapsed               <= 8 min
Synthesis human score     >= 8/10 average
```

Synthesis 两个 veto：

```text
Evidence Discipline = 0 → FAIL
Uncertainty Fidelity = 0 → FAIL
```

### TUNABLE_DEFAULT

以下只能由 benchmark 调整：12 soft / 16 hard reads；2 batches saturation；read concurrency 3；6min soft / 8min hard；Useful Read 60% 初始门槛；False Closure 5–8% 初始 release 范围。

不允许凭感觉改。

---

# 10. OpenCode 施工命令建议

后续可添加 `.opencode/commands/`，但一条命令只代表一个 batch。

例如：

```text
/research-p0-a0
/research-p0-a1
/research-p0-a2
/research-p0-a3
/research-p0-b1
...
```

命令提示必须包含：

```text
Read docs/RESEARCH_QUALITY_CODEX_TASKBOOK.md only as needed.
Read docs/RESEARCH_QUALITY_OPENCODE_EXECUTION_PLAN.md section <batch>.
Execute ONLY <batch>.
Do not start the next batch.
Use the fixed 6-step batch protocol.
Stop after the Stop report.
```

注意：OpenCode command 只提交提示，不代表隔离子任务；真正 reviewer 隔离使用 subagent。

---

# 11. 模型分工建议（不硬编码具体型号）

不要把业务代码依赖某个 OpenCode 模型名。

OpenCode 使用时按能力分：

```text
Planner / architecture audit
→ strongest reasoning model available

Builder
→ strongest coding model available with good tool use

Reviewer
→ reasoning/review model，最好与 Builder 不同或至少新会话

Benchmark bookkeeping / fixture generation
→ cheaper fast model where safe
```

Research 产品内部仍使用 `research_fast / research_reasoning` capability routing；不要把 OpenCode 的施工模型配置写进 Study Agent 运行时代码。

---

# 12. 每阶段推荐提交粒度

不要 P0 一个 commit。

建议：

```text
P0-A0 docs audit
P0-A1 contracts
P0-A2 state persistence
P0-A3 trace
P0-B1 policy
P0-B2 evidence gate
P0-B3 shadow stop gate
P0-C1 eval schema
P0-C2 fixtures
P0-C3 runner
P0-C4 shadow report
```

每个 commit 应：单一意图；测试通过；可独立 revert；不依赖未来 batch 才能恢复 legacy 行为。

P1/P2 同理。

---

# 13. OpenCode 每批的复制提示词模板

```text
你正在维护 2002yy/study-agent。

冻结总规范：docs/RESEARCH_QUALITY_CODEX_TASKBOOK.md
执行计划：docs/RESEARCH_QUALITY_OPENCODE_EXECUTION_PLAN.md

本次唯一任务：<BATCH_ID + NAME>

严格规则：
1. 先读取总规范中与本批相关的决策，以及执行计划中的本批章节。
2. 先做只读 audit，输出 exact files / invariants / tests，再开始修改。
3. 只允许完成本批，不得提前实现下一批。
4. 默认不修改超过 4 个 production files；若必须超过，停止并解释如何拆分。
5. 不得重写 WebLookupService；只允许本批明确规定的最小 adapter/integration。
6. 不得替换 EvidenceRefV1 / ClaimEvidenceLinkV1 / AnswerClaimV1。
7. 不得改变 Standard Search，除非本批明确允许。
8. 不得把 UNAVAILABLE 与 UNRESOLVED 混淆。
9. 修改后运行 focused tests + affected regression tests + git diff --check。
10. 最后输出固定 Stop report，并停止。不要开始下一批。

当前工作区如有与本批无关的未提交改动，不得 reset/stash/覆盖。
```

---

# 14. Reviewer 提示词模板

```text
只审查，不修改代码。

检查当前 batch 是否违反：
- C1–C100 冻结需求；
- 当前 batch 文件边界；
- legacy/Standard Search 不可破坏约束；
- server-owned evidence ID；
- Claim state ownership；
- UNRESOLVED vs UNAVAILABLE；
- False Closure 风险；
- 测试是否真的覆盖本批 Exit Gate。

输出：BLOCKER / MAJOR / MINOR / PASS。
每个问题必须给文件和代码位置、失败场景、为何违反冻结决策。
不要自行修复。
```

---

# 15. 第一轮实际建议怎么开工

如果现在开始用 OpenCode，不要从 P0-A1 直接写代码。

推荐顺序：

```text
Session 1
P0-A0 只读契约审计
↓ STOP

Session 2
P0-A1 Research Contracts v1
↓ tests
↓ reviewer
↓ STOP

Session 3
P0-A2 State persistence adapter
↓ tests
↓ reviewer
↓ STOP

Session 4
P0-A3 Trace
...
```

也就是说，第一轮只要 P0-A0 + P0-A1 做扎实即可；不要追求单会话做完整个 P0。

---

# 16. 什么时候允许从 Shadow 切 Active

必须同时满足：

1. P0 完整 Exit Gate 通过；
2. P1 20 题 Shadow 明显降低 False Closure；
3. Primary Retrieval 提升；
4. Useful Read Ratio 不低于第一版目标；
5. 没有明显 runaway search/read；
6. simple factual case 不被 Deep Research 过度展开；
7. failure taxonomy 不把工具失败伪装成事实不可知；
8. reviewer 无 BLOCKER；
9. 用户明确决定进入 limited active rollout。

Active 也应先 feature flag / limited mode，不直接删除 legacy。

---

# 17. 最终完成定义

项目完成不是“C1–C100 都有代码文件”。必须达到：

```text
研究控制面结构化
+ false closure 明显下降
+ primary/provenance chase 有效
+ read scheduler 不乱读
+ failure/uncertainty 语义正确
+ synthesis 清晰且不自由新增事实
+ 50–60 题 benchmark 过 Gate
+ Standard Search 不承担 Deep Research 全成本
+ legacy 可回退
```

到那时再考虑数据库迁移、移除 legacy、进一步模型/成本优化和更丰富 UI；这些都不属于当前 P0。
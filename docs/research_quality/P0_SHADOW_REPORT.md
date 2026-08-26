# RQCE-P0-C5 Shadow Report (gold-blind baseline vs shadow)

> 组件诊断报告，不是 Release Gate。Shadow 输入只来自预记录 projection；Gold 只在 decision 完成后评分。live baseline 的 closed 是 operational search-status proxy，不是实际 answer-generation transcript。

- cases fixture: `tests\fixtures\research_quality\frozen_trap_cases.json`
- transcripts fixture: `tests\fixtures\research_quality\legacy_transcripts.json`
- evaluated frozen cases: 10

## Frozen 10 聚合指标

- closed runs: 10/10
- false closures (baseline 误闭环): 7
- shadow blocked runs: 6
- caught false closures (shadow 抓到): 6
- missed false closures (shadow 漏抓): 1
- overblocked correct closures (shadow 误 BLOCK): 0
- primary retrieval rate: 4/7 (57.14%)
- mean useful read ratio: 1.00 (contributing reads 15/15)
- mean evidence-linked critical claim coverage: 90.00% (covered 10/11)
- metric caveat: synthetic frozen transcripts contain no deliberately wasted successful reads; the 1.00 useful-read result is fixture-bound, not a production KPI.

## 按类别分布

| category | total | false closures | caught |
|---|---:|---:|---:|
| causal_competing_explanations | 1 | 1 | 1 |
| community_opinion | 1 | 0 | 0 |
| conflicting_primary | 1 | 1 | 0 |
| duplicate_source | 1 | 1 | 1 |
| no_primary_exists | 1 | 0 | 0 |
| numerical_original_source | 1 | 1 | 1 |
| old_primary | 1 | 1 | 1 |
| secondary_only | 1 | 1 | 1 |
| simple_factual | 1 | 0 | 0 |
| unanswerable_unverifiable | 1 | 1 | 1 |

## 逐 case 诊断

| case_id | closed | false_closure | violated | shadow | shadow reasons | open critical | primary retrieval | coverage | useful read ratio |
|---|---|---|---|---|---|---|---|---:|---:|
| trap-secondary-only-frozen | True | True | primary_not_read | block | critical:claim_0:eligible_support_clusters=0/1, critical:claim_0:primary_required | claim_0 | False | 100% | 1.00 |
| trap-duplicate-source-frozen | True | True | independent_sources_below_minimum | block | critical:claim_0:eligible_support_clusters=1/2 | claim_0 | False | 100% | 1.00 |
| trap-old-primary-frozen | True | True | freshness_unmet | block | critical:claim_0:eligible_support_clusters=0/1, critical:claim_0:freshness_required, critical:claim_0:primary_required | claim_0 | True | 100% | 1.00 |
| trap-conflicting-primary-frozen | True | True | conflict_unresolved | pass | - | - | True | 100% | 1.00 |
| trap-no-primary-exists-frozen | True | False | - | pass | - | - | False | 100% | 1.00 |
| trap-community-opinion-frozen | True | False | - | pass | - | - | False | 100% | 1.00 |
| trap-numerical-original-frozen | True | True | primary_not_read | block | critical:claim_0:eligible_support_clusters=0/2 | claim_0 | False | 100% | 1.00 |
| trap-causal-competing-frozen | True | True | conflict_unresolved | block | critical:claim_0:eligible_support_clusters=1/2, critical:claim_1:eligible_support_clusters=1/2 | claim_0, claim_1 | True | 100% | 1.00 |
| trap-simple-factual-frozen | True | False | - | pass | - | - | True | 100% | 1.00 |
| trap-unanswerable-frozen | True | True | question_unverifiable | block | critical:claim_0:eligible_support_clusters=0/2 | claim_0 | False | 0% | 1.00 |

## Live 10 operational observation

- search API status=ok: 10/10
- cases with benchmark-relevant candidates: 2/10
- candidates: 50 total / 10 benchmark-relevant
- reads: 6/6 successful
- cases with provider errors: 8/10
- boundary: this is provider/search/reader evidence only; it uses no model synthesis and produces no shadow decision.

## Live 10 semantic projection + shadow

- projection completed: 8/10; unavailable: 2
- external calls: 14 logical / 17 attempts; failed attempts: 5
- projected public documents: 4
- live benchmark-relevant evidence projection: 1/10 cases produced eligible evidence; 9 produced none
- persisted payload boundary: URL/title/source metadata, structured labels, hashes and audit only; no page body, prompt or raw model output.

| case_id | projection | closed proxy | false_closure | shadow | reasons | primary | coverage | useful |
|---|---|---|---|---|---|---|---:|---:|
| trap-secondary-only-live | completed | True | True | block | critical:claim_0:eligible_support_clusters=0/2 | False | 0% | 0.00 |
| trap-duplicate-source-live | unavailable | - | - | unavailable | claim_projection_unavailable | - | - | - |
| trap-old-primary-live | completed | True | True | block | critical:claim_0:eligible_support_clusters=0/2 | False | 0% | 0.00 |
| trap-conflicting-primary-live | completed | True | True | block | critical:claim_2:eligible_support_clusters=0/2, critical:claim_3:eligible_support_clusters=0/2 | False | 0% | 0.00 |
| trap-no-primary-exists-live | completed | True | True | block | critical:claim_2:eligible_support_clusters=0/2 | False | 0% | 0.00 |
| trap-community-opinion-live | completed | True | True | block | critical:claim_3:eligible_support_clusters=0/2 | False | 0% | 0.00 |
| trap-numerical-original-live | completed | True | True | block | critical:claim_2:eligible_support_clusters=0/2, critical:claim_3:eligible_support_clusters=0/2 | False | 0% | 0.00 |
| trap-causal-competing-live | completed | True | True | block | critical:claim_3:eligible_support_clusters=0/1, critical:claim_3:primary_required | False | 0% | 0.00 |
| trap-simple-factual-live | completed | True | False | pass | - | True | 0% | 0.75 |
| trap-unanswerable-live | unavailable | - | - | unavailable | claim_projection_unavailable | - | - | - |

- live false closures: 7; caught: 7; missed: 0; overblocked: 0

## Combined evaluated cases

- evaluated: 18/20
- false closures: 14; caught: 13; missed: 1; overblocked: 0
- primary retrieval: 5/13 (38.46%)
- useful reads: 18/19; macro=0.60

## RQCE-P0 Exit Gate 自检

1. **legacy 用户可见行为不变**：transcript 是离线 eval 输入，未触碰 WebLookupService 或任何 runtime 路径。
2. **ClaimState/Trace/Gate 可持久化和恢复**：runner 在进程内构造 ResearchState 并经 build_research_state 严格校验；既有持久化 adapter（A2）与 trace writer（A3）未改。
3. **20-case harness repeatability**: **PASS / COMPLETE** — frozen fixtures deterministically re-runnable; live execution protocol, schema and runner re-executable; 20-case report regenerable from structured inputs (live web URLs/results are not required byte-identical).
3b. **20-case diagnostic outcome**: **NO-GO for production activation** — 8/10 live cases produced no eligible evidence projection; live baseline closure is an operational search-status proxy, not a real answer-generation transcript.
3c. **live benchmark-relevant evidence projection**: 1/10 cases produced eligible evidence; 9 produced none.
4. **False Closure case 输出明确 claim/gap 原因**：逐 case 的 open_critical_claims 与 shadow_reasons 已记录于上表。
5. **没有 unknown evidence ID 绕过 Gate**：runner 拒绝未知 doc_id 引用；build_research_state 校验 known_evidence_ids。


## P0 Exit Decision

**RQCE-P0-C5: PASS / COMPLETE.** 20-case Shadow harness delivered and regenerable; production activation remains NO-GO: live evidence projection coverage is low (8/10 no eligible projection) and live baseline closure is an operational proxy. Dominant observed bottleneck: pre-projection retrieval coverage. Current evidence primarily implicates query planning/SearchIntent and legacy relevance/candidate recall; P1 must first classify the no-projection live cases before choosing the implementation target. Local audit + remote HEAD CI green required before RQCE-P1.

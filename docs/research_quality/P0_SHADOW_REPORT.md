# RQCE-P0-C4 Shadow Report (baseline vs shadow)

> 诊断报告，不是 Release Gate。重点定位：Shadow Gate 是否抓到二手来源提前结束、是否误 BLOCK 简单事实、fixture 是否遗漏 critical surface、当前数据结构能否解释失败。

- cases fixture: `tests\fixtures\research_quality\frozen_trap_cases.json`
- transcripts fixture: `tests\fixtures\research_quality\legacy_transcripts.json`
- evaluated frozen cases: 10

## 聚合指标

- closed runs: 10/10
- false closures (baseline 误闭环): 7
- shadow blocked runs: 4
- caught false closures (shadow 抓到): 4
- missed false closures (shadow 漏抓): 3
- overblocked correct closures (shadow 误 BLOCK): 0
- primary retrieval rate: 44.44%
- mean useful read ratio: 1.00
- mean critical claim coverage: 100.00%

## 按类别分布

| category | total | false closures | caught |
|---|---:|---:|---:|
| causal_competing_explanations | 1 | 1 | 0 |
| community_opinion | 1 | 0 | 0 |
| conflicting_primary | 1 | 1 | 0 |
| duplicate_source | 1 | 1 | 1 |
| no_primary_exists | 1 | 0 | 0 |
| numerical_original_source | 1 | 1 | 1 |
| old_primary | 1 | 1 | 0 |
| secondary_only | 1 | 1 | 1 |
| simple_factual | 1 | 0 | 0 |
| unanswerable_unverifiable | 1 | 1 | 1 |

## 逐 case 诊断

| case_id | closed | false_closure | violated | shadow | open critical | primary retrieval | coverage | useful read ratio |
|---|---|---|---|---|---|---|---:|---:|
| trap-secondary-only-frozen | True | True | primary_not_read | block | claim_0 | False | 100% | 1.00 |
| trap-duplicate-source-frozen | True | True | independent_sources_below_minimum | block | claim_0 | False | 100% | 1.00 |
| trap-old-primary-frozen | True | True | freshness_unmet | pass | - | True | 100% | 1.00 |
| trap-conflicting-primary-frozen | True | True | conflict_unresolved | pass | - | True | 100% | 1.00 |
| trap-no-primary-exists-frozen | True | False | - | pass | - | False | 100% | 1.00 |
| trap-community-opinion-frozen | True | False | - | pass | - | False | 100% | 1.00 |
| trap-numerical-original-frozen | True | True | primary_not_read | block | claim_0 | False | 100% | 1.00 |
| trap-causal-competing-frozen | True | True | conflict_unresolved | pass | - | True | 100% | 1.00 |
| trap-simple-factual-frozen | True | False | - | pass | - | True | 100% | 1.00 |
| trap-unanswerable-frozen | True | True | question_unverifiable | block | claim_0 | False | 100% | 1.00 |

## RQCE-P0 Exit Gate 自检

1. **legacy 用户可见行为不变**：transcript 是离线 eval 输入，未触碰 WebLookupService 或任何 runtime 路径。
2. **ClaimState/Trace/Gate 可持久化和恢复**：runner 在进程内构造 ResearchState 并经 build_research_state 严格校验；既有持久化 adapter（A2）与 trace writer（A3）未改。
3. **20 题 runner 可重复**：frozen 10 题已跑且确定性可重跑；live 10 题无 corpus，超出 P0 离线范围（留待真实 web 运行）。
4. **False Closure case 输出明确 claim/gap 原因**：逐 case 的 open_critical_claims 与 shadow_reasons 已记录于上表。
5. **没有 unknown evidence ID 绕过 Gate**：runner 拒绝未知 doc_id 引用；build_research_state 校验 known_evidence_ids。

> RQCE-P0 Exit Gate 通过后禁止自动进入 RQCE-P1；需人工确认本报告。

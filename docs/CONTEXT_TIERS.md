# Context Tiers

> Context 是推理输入，不等于 durable truth。本文定义上下文装配优先级与污染边界。

## Tier 0 — 当前用户意图与安全边界

当前问题、当前 LearningGoal、明确约束、最新用户修正。最高优先级。

## Tier 1 — Committed learning truth

- current Claim Revision；
- committed EvidenceSet；
- Understanding status；
- blocking unresolved；
- active NextStep。

这层只消费已提交对象，不混入搜索候选或模型猜测。

## Tier 2 — 当前 evidence working set

- exact-commit source snippets；
- one-hop structural relations；
- RAG/Web provider results；
-当前检索的 ValidationObservation。

这里可以包含 ephemeral candidates，但 candidates 不因为进入 prompt 就升级为 durable evidence。

## Tier 3 — Recent learning interaction

近期对话、当前例子、用户刚才的复述、短期 pedagogy observation。用于保持连贯，不拥有长期 truth。

## Tier 4 — Long-term memory / summaries

用户稳定偏好、历史背景、conversation summary。作为辅助 context，不覆盖 Topic/Goal/Claim/Understanding 的正式状态。

## Tier 5 — Persona / style

语气、角色表达、例子偏好、社交氛围。最低 truth authority；不得改变上层事实或 mastery judgement。

## Context 裁剪原则

```text
Current Goal
> committed truth
> directly relevant evidence
> recent interaction
> long-term summaries
> persona decoration
```

当预算不足时优先裁掉弱相关候选、重复 evidence、旧对话和 Persona 装饰，不裁掉当前 Goal、关键 prerequisite 或 committed truth。

## Source exploration

源码自动结构扩展最多一跳。更深关系必须开启新的显式 retrieval；不得为了“多给模型上下文”把半个仓库静默塞进 prompt。

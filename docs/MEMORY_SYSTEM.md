# Memory System

> 记忆系统帮助保持用户背景与学习连续性，但**不拥有第二套学习真值**。当前进度看 [`PROJECT_STATUS.md`](PROJECT_STATUS.md)。

## 1. 记忆与学习真值不是同一件事

```text
Memory
- 用户偏好
- 稳定背景事实
- 会话摘要
- 角色关系/互动上下文

Learning Truth
- LearningGoal
- LearningClaim / Revision
- SourceEvidence
- UnderstandingEvidence
- Hypothesis / NextStep
```

记忆内容可以帮助解释和恢复，但不能通过“摘要里写了用户懂了”把 Claim 自动变为 confirmed。

## 2. 单一 owner

- durable runtime / learning truth：应用服务 + SQLite/正式领域持久化；
- memory files/records：记忆 owner；
- Persona：只消费记忆，不独立维护 mastery truth；
- Markdown export：人类可读，不作为并发写入 owner。

## 3. 写入原则

- planned / attempted / partial / failed 不覆盖 committed truth；
- 模型提出的 memory candidate 在 commit 前只是候选；
- 批量写入必须可明确区分成功、部分成功、失败；
- 用户可审计长期记忆的来源与用途；
- 角色短期“这轮解释似乎有效”只属于 ephemeral pedagogy context。

## 4. 与 Understanding 的边界

`confirmed` 需要用户产生的 UnderstandingEvidence。Memory 可以记录“用户自评已理解”，但这只代表 self-reported，不等价于 verified mastery。

## 5. 与 Resume 的边界

学习恢复优先使用 `LearningResumePoint`（Goal / confirmed / unresolved / NextStep / source context）。Conversation summary 是辅助材料，不能取代语义恢复点。

## 6. 与多角色的边界

Nahida / March 7th / Keqing / Firefly 等 Persona 共享同一学习真值。角色可以有不同措辞、案例和短期互动观察，但不能形成各自版本的 Claim、mastery 或 Evidence validity。

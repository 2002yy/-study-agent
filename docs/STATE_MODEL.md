# Study Agent State Model

> 本文定义“什么状态由谁拥有、是否持久化、能否覆盖”。当前进度看 [`PROJECT_STATUS.md`](PROJECT_STATUS.md)。

## 1. 状态分类

| 类别 | 示例 | Owner | 持久化 |
|---|---|---|---|
| Durable runtime truth | ChatTurn、session、run、正式学习实体 | FastAPI application/repository + SQLite | 是 |
| Committed learning truth | Claim Revision、committed Evidence、UnderstandingEvidence | Learning domain owner | 是（按实施阶段推进） |
| Ephemeral process state | evidence candidates、搜索排序、streaming UI、临时 tool result | request/runtime/UI | 否 |
| Derived view state | 首页卡片、freshness 提示、统计 | selector/view model | 可重建 |
| Runtime cache | SourceSnapshot cache、CI observation cache | cache owner | 非长期真值 |
| Historical export | Markdown session/export/archive docs | export/history | 不作为并发 runtime truth |
| Persona context | 当前角色措辞/教学策略提示 | Persona/pedagogy | 不拥有 truth |

## 2. Learning state

```text
LearningTopic
  ↓
LearningGoal ── LearningResumePoint
  ↓
LearningClaim ── ClaimRevision
  ↓                 ├─ EvidenceSet
Understanding       └─ UnderstandingEvidence

LearningHypothesis ── resolved_by → LearningClaim
blocking unresolved ──→ NextStep
```

### 三个独立维度

- **Understanding**：用户是否通过验证；
- **Source freshness**：当前源码是否仍支持历史结论；
- **Retention**：当前是否值得复习。

任何一个维度变化都不能偷偷覆盖另两个维度的历史事实。

## 3. Claim state

Claim 使用稳定 identity + immutable revisions。

```text
rev1 @ source A
   ↓ source changed
stale_candidate
   ↓ explicit revalidation
rev2 @ source B
```

- 历史 `confirmed` 不因 repo 变化降级；
- source removed → `source_changed`，不是历史无效；
- supporting drift 默认非 blocking；prerequisite drift 可触发 stale；
- repo HEAD 前进不是 stale 的充分条件。

## 4. Goal state

```text
active ↔ blocked → completed
   └────────────→ abandoned (explicit user intent)
```

- 浏览器关闭/聊天结束不改变 Goal 为 completed；
- inactivity 不自动 abandoned；
- Goal 不使用“82%”之类伪精确进度；
- Agent 可 clarify/narrow，不可静默换目标。

## 5. Resume state

恢复锚点按语义，而不是 last_message_id：

```text
topic
active_goal
last_confirmed_claim
current_unresolved
next_action
source_context
```

多个 active Goal 时默认恢复最近明确 active 的一个，其余进入“继续学习”次级列表。

## 6. Evidence state

```text
candidate (ephemeral)
   ↓ converge
committed EvidenceSet (durable learning reference)
```

SourceEvidence 与 ValidationObservation 分开。CI cache 只表达最近观察，不反向修改 SourceEvidence identity。

## 7. Memory state

长期记忆可以帮助重建偏好、关系、背景和会话摘要，但不得成为 Claim/Evidence/Understanding 的第二 truth owner。详细见 [`MEMORY_SYSTEM.md`](MEMORY_SYSTEM.md)。

## 8. Multi-role state

所有 Persona 共享同一 durable learning state。角色可以保留短期教学观察，但这些 observation 不能升级成“用户已掌握”“源码已验证”等 durable truth。

## 9. Conflict state

`ClaimConflict` / `EvidenceConflict` 必须显式存在到被解释：版本演进、scope 差异、错误结论、或 unresolved。禁止 latest-write-wins 清除语义冲突。

## 10. UI state

首页主层级：NextStep → Goal → Topic。Evidence 使用渐进披露。Freshness 提醒只有在与当前 Goal/推理相关时主动出现，不制造全局 stale backlog 压力。

# Study Agent State Model

> 本文定义“什么状态由谁拥有、是否持久化、能否覆盖”。当前进度看 [`PROJECT_STATUS.md`](PROJECT_STATUS.md)。
>
> 2026-08-21：已纳入 P2-D GrillMe 决策 1–49、G12/G16 最终 Grill 决策 1–24 与 v1 implementation cut。

## 1. 状态分类

| 类别 | 示例 | Owner | 持久化 |
|---|---|---|---|
| Durable runtime truth | ChatTurn、session、run、正式学习实体 | FastAPI application/repository + SQLite | 是 |
| Committed learning truth | Claim Revision、committed SourceEvidence、UnderstandingEvidence | Learning domain owner | 是 |
| Ephemeral process state | evidence candidates、搜索排序、streaming UI、临时 tool result | request/runtime/UI | 否 |
| Derived view state | 首页卡片、freshness 提示、统计、resume projection | selector/view model | 可重建 |
| Runtime cache | SourceSnapshot cache、structure index、CI observation cache | cache owner | 非长期真值 |
| Historical export | Markdown session/export/archive docs | export/history | 不作为并发 runtime truth |
| Persona context | 当前角色措辞/教学策略提示 | Persona/pedagogy | 不拥有 truth |

## 2. Learning state

```text
LearningTopic
  ↓
LearningGoal ── prerequisite → LearningGoal
  │
  ├─ LearningClaim ── ClaimRevision
  │                      ├─ EvidenceSet
  │                      └─ UnderstandingEvidence
  │
  ├─ LearningHypothesis ── resolved_by → LearningClaim
  └─ blocking unresolved ──→ NextStep

Workspace focus / ResumePoint
= navigation state, not learning truth
```

### 三个独立维度

- **Understanding**：用户是否通过验证；
- **Source freshness**：当前源码是否仍支持历史结论；
- **Retention**：当前是否值得复习。

任何一个维度变化都不能偷偷覆盖另两个维度的历史事实。

## 3. P2-D v1 durable set

### NOW：正式 durable truth

- `LearningTopic`
- `LearningGoal`
- `LearningClaim`
- `ClaimRevision`
- `SourceEvidence`
- `UnderstandingEvidence`
- 轻量 `LearningHypothesis`
- 轻量 `NextStep`

### CONTRACT：语义已冻结，v1 不要求独立 durable table

- `LearningRoute`
- `ClaimConflict`
- `GeneralizationCandidate`
- durable `ValidationObservation` history
- Retention history
- `EvidenceRetrieval`
- `LearningArtifact`
- `LearningCheckpoint`

### LATER：明确不阻塞 P2-D v1

- 知识图谱；
- Route editor；
- Retention scheduler / Anki；
- 全局 stale center；
- CI monitoring center；
- Revision management UI；
- durable CI observation history。

## 4. Claim state

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
- repo HEAD 前进不是 stale 的充分条件；
- duplicate candidate 复用既有 lineage，不做 latest-write-wins。

## 5. Goal state

```text
active ↔ blocked → completed
   └────────────→ abandoned (explicit user intent)
```

- 浏览器关闭/聊天结束不改变 Goal 为 completed；
- inactivity 不自动 abandoned；
- Goal 不使用“82%”之类伪精确进度；
- Agent 可 clarify/narrow，不可静默换目标；
- skip Understanding Validation 可以 completed，但相关 Claim 保持 unverified；
- prerequisite 只记录真正影响理解/验证的稀疏无环关系。

## 6. Resume / focus state

恢复锚点按语义，而不是 last_message_id：

```text
topic
active_goal
last_confirmed_claim
current_unresolved
next_action
source_context
```

多个 active Goal 时：

```text
pinned focus Goal
↓
last explicitly engaged active Goal
```

主 Goal 暂时 blocked 时可以提供替代动作，但不得静默把 focus 切到另一个 Topic。

## 7. Evidence state

```text
candidate (ephemeral)
   ↓ deterministic convergence
committed EvidenceSet relation (durable)
```

SourceEvidence 与 ValidationObservation 分开。CI cache 只表达最近观察，不反向修改 SourceEvidence identity。

`EvidenceSet` 在 v1 是领域概念，不要求单独表；`claim_revision_evidence` 可表达 primary / supporting + supporting role。

## 8. Existing projection compatibility

现有运行时仍有三类兼容/投影状态：

1. `AnswerClaimV1 / AnswerClaimSnapshotV1`：单个最终回答的 answer projection；
2. `EvidenceRefV1 / EvidenceSnapshotV1`：单个 ChatTurn 的 evidence projection；
3. `ChatThread.learning_state`：旧教学状态 JSON，包含 objective / confirmed_points / unresolved_gap / next_action 等。

它们可以帮助展示、恢复旧 session、构造 candidate，但**都不是 P2-D 新 committed learning truth**：

- AnswerClaim 的 answer-hash identity 不能升级为 LearningClaim lineage；
- EvidenceRef 的 score/provider status/selection reason 不能进入 SourceEvidence durable identity；
- `confirmed_points` 不得无 Evidence/Understanding 闭环批量迁移为 confirmed Claim。

P2-D-3 应采用“新 durable truth 优先，legacy projection fallback”的兼容策略，而不是 destructive migration。

## 9. Understanding state

`PedagogyEvalRun` 仍然是教学评估运行记录；P2-D `UnderstandingEvidence` 是长期 mastery proof。

```text
PedagogyEvalRun / user turn
        ↓ semantic closure mapping
UnderstandingEvidence
        ↓ relation
ClaimRevision → pass | partial | fail
```

Agent 的解释、self-report “懂了”、grader confidence 均不能独立生成 confirmed。

## 10. Memory state

长期记忆可以帮助重建偏好、关系、背景和会话摘要，但不得成为 Claim/Evidence/Understanding 的第二 truth owner。详细见 [`MEMORY_SYSTEM.md`](MEMORY_SYSTEM.md)。

LearningClosure / MemoryRun 的现有 resumable workflow 是可复用的 commit orchestration 模式，但 P2-D 长期 Claim/Evidence 应写入自己的 normalized repository，而不是继续塞进 Markdown memory 作为 canonical truth。

## 11. Multi-role state

所有 Persona 共享同一 durable learning state。角色可以保留短期教学观察，但这些 observation 不能升级成“用户已掌握”“源码已验证”等 durable truth。

## 12. Conflict state

`ClaimConflict` / `EvidenceConflict` 必须显式存在到被解释：版本演进、scope 差异、错误结论、或 unresolved。禁止 latest-write-wins 清除语义冲突。P2-D v1 可以只冻结合同，不要求独立 conflict table/UI。

## 13. Tool / provider state

```text
read-only retrieval      → ephemeral request/tool state
provider cache           → runtime cache
committed SourceEvidence → durable learning truth
external write           → requires confirmation
```

- goal-serving read 可以自动；goal-expanding research 必须显式提出；
- 普通 tool chain 必须有界；
- 同一 transient failure 默认最多一次有意义 retry；
- fallback provider 不得冒充原 evidence type；
- provider failure 不产生 negative fact。

## 14. Context temperature model

长期运行时把“数据库是否保留”和“是否进入模型 prompt”分开。

### HOT

- 当前 Goal / Primary NextStep；
- 当前 unresolved；
- 当前 Evidence candidates / committed references；
- 当前局部最近对话。

默认进入当前 prompt。

### WARM

- 当前 Topic 的相关 Claims / Hypotheses；
- ResumePoint；
- 近期必要 Artifact；
- 与当前 Goal 有关的旧 Evidence。

按需加载。

### DURABLE

- ClaimRevision；
- SourceEvidence identity；
- UnderstandingEvidence raw user response；
- Goal history；
- user intent（pin / skip / abandon / explicit revalidate）；
- conflict/resolution history。

长期保留，但默认不全量进入 prompt。

### COLD

- 完整旧 ChatTurns；
- 历史 Artifact；
- 旧 retrieval / diagnostics /重复解释。

可检索、可审计，默认不进入 prompt。

**Context compression 只改变 prompt 输入，不等于 durable deletion。**

## 15. UI state

首页主层级：NextStep → Goal → Topic。Evidence 使用渐进披露。Freshness 提醒只有在与当前 Goal/推理相关时主动出现，不制造全局 stale backlog 压力。

P2-D v1 只需要：Goal、少量 Claims、Primary/Supporting、Hypothesis、短验证、Primary NextStep。现有 `LearningStrip / LearningPanel / EvidenceTrail` 应作为复用 surface，不新造管理后台。

## 16. Durable commit boundary

P2-D learning truth 不在每个 chat token/turn 后实时写入。

```text
chat / retrieval
→ ephemeral candidate
→ evidence convergence
→ claim-worthiness gate
→ semantic learning closure
→ atomic durable commit
```

如果中途证据变化、发现 owner 解释错误、provider unavailable，过程状态应停留在 candidate/Hypothesis，而不是留下多份错误 Claim。

## 17. SQLite ownership

P2-D v1 使用规范化关系表，目标 schema 见 [`../domain_models.md`](../domain_models.md)。禁止用通用 JSON blob 把新学习真值继续塞回 `chat_threads.learning_state`。

当前 `RuntimeDatabase` 的顺序迁移/ledger/rollback 机制继续作为 schema owner；新 P2-D 表必须通过同一受控迁移链或明确的单一 component migration owner 引入，不能另起第二套数据库初始化规则。

## 18. ChatTurn operation / cancellation state

ChatTurn 是 chat 取消与中断的唯一 durable owner；客户端 operation registry 和 HTTP 连接状态只是交互/传输状态。

```text
client preallocates turn_id + operation_id
→ server reserves ChatTurn before expensive preparation
→ cancel_requested(operation_id)
→ checkpoint settles cancelled | interrupted
→ same-operation completion is fenced forever
```

- cancel timestamps、stage、reason 必须与目标 operation 绑定；旧 operation 的 cancel 字段不能污染 continuation 的新 operation；
- 无可见输出为 cancelled；已有可见回答或来源为 interrupted；completed 先提交时只能观测 already_completed；
- Cancel POST 表达“请求已登记”，turn-status read 表达最终事实；
- 未采用 local RAG chunks 保持 ephemeral，不创建 LocalRagRun，不进入模型、证据、LearningTruth 或 retry reuse；
- continuation 复用同 Turn 已采用 snapshot，retry/regenerate 产生 child Turn/new retrieval；
- `archive_after_cancel` 是 server-owned durable intent，不是 React callback/ref。

## 19. External-call audit state

外发授权和外发事实分开保存：policy decision 表达“允许什么”，`external_calls` 表达“实际发生了什么”。

| 调用 owner | 调用用途 | 最小记录 |
|---|---|---|
| ChatTurn | answer generation、pedagogy evaluation、query embedding | purpose、provider、data categories/counts、result、audit version |
| RagWriteRun stage | document embedding | provider、document/chunk counts、result/`blocked_by_policy`、audit version |

调用审计不保存 prompt、query 或文档正文。旧 Turn 没有足够调用级证据时，派生 UI 必须显示 unknown；不得从策略布尔值推导 false。`question_only` / `recent_chat` 下，外部教学评估不得读取长期学习状态；外部 query embedding 最多使用当前原始问题，private query 只在本地使用。未建立文档级云处理授权前，document embedding 只能本地执行。

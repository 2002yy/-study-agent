# Study Agent 领域模型

> **稳定语义 owner。** 当前进度不在此维护，请看 [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)。
>
> 2026-08-09：P2-D GrillMe 决策 1–49 已冻结。本文描述稳定目标语义与 P2-D v1 最小实现边界；其中部分对象仍只保留合同，实施状态必须以 `PROJECT_STATUS.md` 为准。

## 1. 领域总览

```text
LearningTopic
├─ LearningGoal
│  ├─ prerequisite → LearningGoal
│  └─ LearningResumePoint
├─ LearningClaim
│  └─ ClaimRevision*
│     ├─ EvidenceSet
│     │  ├─ Primary SourceEvidence (exactly 1)
│     │  └─ Supporting SourceEvidence (0..4)
│     └─ UnderstandingEvidence*
├─ LearningHypothesis
├─ ClaimConflict / EvidenceConflict
└─ NextStep

SourceEvidence ── independent ── ValidationObservation
LearningClaim  ── separate ───── source freshness
LearningClaim  ── separate ───── retention

LearningRoute / LearningArtifact / GeneralizationCandidate
= supporting contracts, not competing truth owners
```

核心原则：**源码是否有依据、用户是否掌握、知识对当前源码是否仍新鲜，是三个不同问题。**

## 2. LearningTopic

稳定的学习机制域，不是层层嵌套的知识文件夹。

```typescript
type LearningTopic = {
  id: string;
  title: string;
  scope: "project" | "general";
  createdAt: string;
  updatedAt: string;
};
```

示例：`会话状态与恢复`、`RAG 证据链`、`GitHub 源码学习`。

## 3. LearningGoal

一次具体学习目标，与 Topic 分离。

```typescript
type LearningGoalStatus = "active" | "blocked" | "completed" | "abandoned";

type LearningGoal = {
  id: string;
  topicId: string;
  objective: string;
  status: LearningGoalStatus;
  createdAt: string;
  updatedAt: string;
};
```

规则：
- 聊天关闭不等于 Goal 完成；
- 无活动不自动变 `abandoned`；
- 不使用伪精确的完成百分比；
- Agent 可以澄清/收窄 Goal，但不能静默改变语义方向；真正的新方向创建候选新 Goal；
- Goal 完成基于原问题与核心 Claim 闭环，不要求把整个仓库探索完；
- 理解验证可由用户显式跳过，此时 Goal 可以 completed，但相关 Claim 不因此 confirmed。

Goal 完成条件：核心问题已回答、必要 Claim 已形成、blocking unresolved 已清零、理解验证已完成或用户明确跳过、NextStep 已收敛。

## 4. LearningResumePoint

恢复的是学习状态，而不是最后一条聊天消息。

```typescript
type LearningResumePoint = {
  topicId: string;
  activeGoalId: string;
  lastConfirmedClaimId?: string;
  currentUnresolvedIds: string[];
  nextStepId?: string;
  sourceContext?: Record<string, unknown>;
};
```

默认恢复用户 pinned 的 focus Goal；没有 pin 时恢复最近明确投入的 active Goal。UI 优先表达“上次学到 / 当前卡点 / 继续”。ResumeContext 必须从 durable entities 派生，而不是把一段 LLM 摘要当唯一状态。

## 5. LearningClaim

Claim 是短小、可验证、有长期复用价值的命题。不是 Agent 整段解释，也不是所有正确的局部事实。

```typescript
type ClaimKind = "mechanism" | "boundary" | "invariant" | "fact";
type ClaimScope = "project" | "general";

type LearningClaim = {
  id: string;
  topicId: string;
  subject: string;
  kind: ClaimKind;
  scope: ClaimScope;
  currentRevisionId: string;
  supersededBy?: string;
};
```

源码学习产生的 Claim 默认 `scope=project`。单仓库观察不得自动升级为 general truth。

长期保存优先：机制、边界、不变量、决策性事实。行号、临时调用、搜索排名等默认留在 Evidence / session context。每个语义学习小节通常只沉淀 1–3 个核心 Claim。

## 6. ClaimRevision

Claim 有稳定语义身份；文本、证据和验证结果进入不可变 Revision。

```typescript
type RevisionReason = "initial" | "revalidated" | "meaning_changed";

type ClaimRevision = {
  id: string;
  claimId: string;
  text: string;
  evidenceSet: EvidenceSet;
  understandingEvidenceIds: string[];
  sourceCommit?: string;
  reason: RevisionReason;
  createdAt: string;
};
```

- 历史 Revision 永不原地覆盖；
- repo 每个 commit 不自动制造 Revision；
- Primary Evidence 发生实质变化后，经过显式 revalidation 才产生新 Revision；
- 同一学习问题答案随架构演进而变化时保持 lineage；问题本身被淘汰时用 `supersededBy` 连接新 Claim；
- 同一学习问题的等价 Claim candidate 复用 lineage，不创建重复 Claim；
- LLM 可以提出疑似重复，但不能自行合并/删除历史 Claim。

## 7. EvidenceSet

```typescript
type SupportingRole = "corroborating" | "prerequisite";

type EvidenceSetEntry = {
  evidenceId: string;
  position: "primary" | "supporting";
  supportingRole?: SupportingRole;
};

type EvidenceSet = {
  primary: EvidenceSetEntry;       // exactly 1
  supporting: EvidenceSetEntry[];  // 0..4
};
```

规则：
- Exactly 1 Primary；Supporting 最多 4；
- 超过 5 个总证据通常说明 Claim 太大，应拆分；
- 不使用 importance/confidence 数值权重；
- `corroborating` 只是佐证；`prerequisite` 是 Claim 成立的必要逻辑前提；
- role 属于 Claim→Evidence 关系，不属于 SourceEvidence 本体；
- v1 不要求独立 `evidence_sets` 表，可由 `claim_revision_evidence` 关系表表达。

## 8. SourceEvidence

SourceEvidence 只回答“引用了什么”。

```typescript
type SourceEvidence = {
  id: string;
  repository: string;
  commitSha: string;
  treeSha: string;
  path: string;
  fileSha: string;
  symbol?: string;
  symbolKind?: string;
  startLine: number;
  endLine: number;
  evidenceKind: string;
};
```

最小不可缺定位：repository + exact commit + path + file SHA + line range。

不属于 SourceEvidence durable truth：query、rank、search score、chunk score/文本、parser 调试信息、LLM confidence、CI status、Supporting role、整段源码副本。

## 9. Evidence 候选与收敛

```text
Ephemeral candidates
→ deterministic convergence
→ committed EvidenceSet
```

收敛规则：
1. 选出 1 个最直接 Primary；通常优先实现 owner/contract，而不是外围搜索命中；
2. Supporting 去重；
3. 优先覆盖不同证明维度（实现、caller/callee、test、contract、prerequisite）；
4. 不为了凑数量加入弱证据；
5. 候选默认不进入 durable truth；
6. 不要求用户逐条审批，但 committed Evidence 必须可审计、可质疑、可重新验证；真正语义歧义才打断用户。

## 10. 源码自动探索边界

默认只自动扩展 Primary symbol 的**一层直接结构关系**：直接 caller/callee/import/implementation/test/config/contract。

超过一跳必须创建新的显式 evidence retrieval，并保留“为什么继续深入”。唯一例外是严格的 transparent forwarding：无业务分支、无状态变化、无领域语义变换的机械透传层可穿透。

底层 GitHub graph 工具可以支持更深查询，但 **Learning application service** 必须把普通自动探索固定在 one-hop；不能依赖底层工具默认 depth。

## 11. ValidationObservation

CI / provider 验证是时间变化的 observation，不属于 SourceEvidence identity。

```typescript
type ValidationObservation = {
  sourceEvidenceId?: string;
  commitSha: string;
  provider: string;
  runId?: string;
  status: "success" | "failure" | "pending" | "unavailable" | "unknown";
  observedAt: string;
};
```

- CI 必须 exact-SHA 关联；
- CI failure / unavailable ≠ source invalid；
- P2-D v1 只需要 runtime observation/cache 语义，不引入 durable CI history；
- SourceSnapshot/structure index 使用强 commit-pinned 复用；CI 使用独立短 TTL 与显式 refresh，不阻塞普通源码学习。

## 12. 源码 freshness

理解状态与源码 freshness 分离：

```text
current
stale_candidate
source_changed
```

- Primary 实质变化 → `stale_candidate`；
- Primary 被删除/无法重新映射 → `source_changed`，不是“历史 Claim 无效”；
- Supporting 变化默认只是 drift；只有 `prerequisite` 实质变化才可触发 stale；
- repo HEAD 前进本身不能让所有 Claim stale；
- revalidation 不覆盖历史 Revision；
- stale 检查只在相关 Goal/Claim 被恢复、引用或显式要求检查时触发，v1 不做后台全局扫描。

## 13. UnderstandingEvidence

`confirmed` 必须由用户产生的理解证据支撑；Agent 无权自证。

```typescript
type UnderstandingMethod = "explain" | "apply" | "practice";
type UnderstandingResult = "pass" | "partial" | "fail";

type UnderstandingEvidence = {
  id: string;
  method: UnderstandingMethod;
  prompt: string;
  userResponse: string;
  verifiedAt: string;
};

type UnderstandingEvidenceClaim = {
  understandingEvidenceId: string;
  claimRevisionId: string;
  result: UnderstandingResult;
};
```

- 用户说“懂了”只代表 self-reported/attempted，不直接 confirmed；
- 默认最小充分验证，一个关键问题即可；复杂小节通常一次覆盖 1–3 个强相关 Claim；
- 优先应用/预测/解释，不做题海；
- 用户可跳过验证继续学习，但 Claim 保持 unverified；
- 低价值 `fact` 可不要求理解验证；
- durable 数据保留 prompt、用户原始 response 和 per-Claim result，不保存 grader chain-of-thought 或虚假 mastery score。

## 14. Retention

历史 `confirmed` 表示“曾经通过验证”，不会因时间或一次回忆失败被改写。

Retention 独立表达：`fresh / review_candidate / needs_refresh / rechecked`。时间只能产生复习建议，不能推断用户已经忘记。复习优先情境触发；Study Agent 当前不扩张成完整间隔重复/Anki 系统。P2-D v1 暂不引入独立 retention history 表。

## 15. LearningHypothesis

没有可靠 Primary Evidence 时，不能创建正式 LearningClaim。

```typescript
type UnresolvedReason =
  | "missing_source"
  | "ambiguous_owner"
  | "insufficient_evidence"
  | "external_dependency"
  | "provider_unavailable";

type LearningHypothesis = {
  id: string;
  topicId: string;
  goalId?: string;
  text: string;
  candidateRefs: string[];
  unresolvedReason: UnresolvedReason;
  resolvedBy?: string;
  createdAt: string;
};
```

可证实子命题应拆成 Claim，不确定剩余继续作为 Hypothesis。解决后创建新 Claim，并通过 `resolvedBy` 保留历史，不原地变身。

## 16. NextStep

Hypothesis 不默认制造任务。只有直接阻塞当前 Claim、用户问题或理解验证的 unresolved item 才进入 NextStep。

- 默认 1 个 primary NextStep；必要时最多 2 个 optional；
- NextStep 必须是行动，不是 Hypothesis 文本复制；
- background unresolved 静默保留；
- 用户可主动提升 background item；
- Hypothesis resolved 后可自然完成关联 NextStep；
- 排序：用户 pinned > blocking dependency > 当前 Goal 连续性 > 情境 freshness/retention > optional；
- Agent 可以重排派生步骤，但不能静默覆盖用户 pinned 的学习意图。

## 17. Duplicate / Conflict / Generalization

- LLM 不得自动语义合并历史 Claim；只能标记疑似重复/`duplicateOf` 候选；
- 冲突使用显式 `ClaimConflict` / `EvidenceConflict`，最新记录不能静默覆盖旧记录；
- 架构演进可用 `supersededBy`，scope 差异可能不是真冲突；
- project → general 只能产生 `GeneralizationCandidate`；General Claim 需要独立概念学习与理解验证。

## 18. Evidence Provider 与 truth domain

Provider：GitHub / RAG / Web。它们不是 truth type，也没有全局优先级。

Truth domain 第一版只区分：

- `implementation`：当前/指定版本实现事实，通常由 GitHub/runtime evidence 支撑；
- `project_decision`：项目规范、正式决定，通常由项目文档/durable decision 支撑；
- `external_fact`：外部规范/事实，通常由权威 Web 来源支撑。

设计与实现冲突必须显式呈现 divergence；外部规范与项目实现不一致必须显式呈现 deviation；同一 truth domain 仍无法解释的来源冲突进入 EvidenceConflict。

## 19. Persona 与多角色

所有角色共享唯一 LearningTopic / Goal / Claim / Evidence / Understanding / NextStep durable truth。Persona 只能改变教学策略、例子、节奏、措辞和短期互动 context。

```text
Truth Layer
↓
Learning Layer
↓
Pedagogy Layer
↓
Persona Layer
```

下层不得反向改写上层 truth。

## 20. Agent 主动性与 Tool 边界

### 20.1 自动读取

`goal-serving retrieval` 可以自动执行：当前 Goal 必需的 GitHub source read、RAG read、权威 Web read 不需要每一步确认。

`goal-expanding research` 不得静默发生。Agent 想研究竞品、业界最佳实践或新的大方向时，应提出新的 Goal / GeneralizationCandidate / NextStep，而不是把当前 Goal 偷换掉。

### 20.2 有界工具链

一个普通 Agent turn 使用短、有界执行链。达到 budget 后只能：

```text
证据充分 → 综合 / 收敛
证据不足 → LearningHypothesis
确需继续深挖 → 新 retrieval + recorded reason
```

不得无限搜索，也不得在预算结束时用猜测补事实。

### 20.3 Retry / fallback

同一外部读取默认只进行一次有意义重试。明确的 404、权限拒绝、schema error 等不做无意义重复。Provider fallback 不得伪装成原 evidence 类型：例如 GitHub exact source unavailable 时，Web 搜索结果只能作为其他 provider evidence，不能冒充 commit-pinned SourceEvidence。

### 20.4 Confirmation

```text
Read-only learning action        → automatic
Derived internal state           → automatic
External write / send / deploy   → explicit confirmation
Irreversible / paid action       → explicit confirmation
User-intent mutation             → explicit confirmation
```

把 Goal 标成 abandoned、删除 pinned NextStep、合并用户明确 Topic 等属于 user-intent mutation；Hypothesis resolved 后完成关联 NextStep 属于 derived state。

### 20.5 Durable commit point

长期学习真值不边聊边写。过程中的 candidate、temporary interpretation、retrieval note 保持 ephemeral；只有在语义小节闭合、EvidenceSet 收敛、claim-worthiness 通过时才可自动提交少量 durable Claim。用户说“记住这个”可以提前触发候选，但不能绕过 evidence/truth 边界。

## 21. LearningRoute、prerequisite 与 focus

### 21.1 LearningRoute

`LearningRoute` 是可变导航建议，不是学习真值，也不是强制课程表。

```typescript
type LearningRoute = {
  topicId: string;
  suggestedGoalIds: string[];
};
```

它可以重排、跳过、删除或重新生成，不反向修改历史 Claim/Understanding。

### 21.2 Goal prerequisite

Goal 可以有稀疏、无环的 `requires` 关系。只有“不知道 X 会明显妨碍理解或验证 Y”时才建立 prerequisite；不构建完整知识图谱。

用户可以跳过 prerequisite：非关键 gap 仅记录；真正阻塞当前推理/验证的前置才进入 blocking unresolved。跳过没有惩罚性分数，也不等于已掌握。

### 21.3 Workspace focus

多个 Topic/Goal 同时 active 时：

```text
pinned focus Goal
↓
last explicitly engaged active Goal
```

Agent 不做跨 Topic 的“全局最优学习调度”。主 Goal 被外部条件阻塞时可以提供替代动作，但不静默切换主线。

## 22. Chat history、LearningArtifact 与上下文压缩

### 22.1 Chat history

Raw ChatTurn 可以长期保留作审计/历史，但不是 durable learning truth，也不承担长期恢复主职责。默认 prompt 只加载当前 Goal 所需的局部最近对话。

### 22.2 LearningArtifact

`LearningArtifact` 是面向人阅读的阶段性整理，不是第二套 Claim/Evidence owner。Artifact 可以引用多个 Goal/Claim/source refs；底层知识变化后历史 Artifact 可以显示 stale 提示，但不得静默重写旧内容。

自动生成只发生在重要 Goal 完成、Topic 阶段边界或用户主动要求时；零散问答不制造一篇篇总结文件。

### 22.3 Resume source priority

```text
1. LearningGoal / ResumePoint
2. Claim / Hypothesis / unresolved
3. NextStep
4. relevant Evidence
5. recent local ChatTurns
6. Artifact (only when useful)
```

### 22.4 Context compression ≠ history deletion

可以积极压缩/冷却：重复解释、检索中间过程、失败搜索、无关寒暄、已结束局部推演。

不能不可逆压缩掉：ClaimRevision、SourceEvidence identity、UnderstandingEvidence 原始用户回答、用户显式 pin/skip/abandon/revalidate 事件、冲突及解决历史。

“不进 prompt”不等于“从数据库删除”。

## 23. P2-D v1 最小实体集

P2-D v1 正式落地 **6 个核心 + 2 个轻量对象**：

### NOW / durable core

1. `LearningTopic`
2. `LearningGoal`
3. `LearningClaim`
4. `ClaimRevision`
5. `SourceEvidence`
6. `UnderstandingEvidence`

### NOW / lightweight durable

7. `LearningHypothesis`
8. `NextStep`

### CONTRACT / 暂不单独实体化

- `LearningRoute`
- `ClaimConflict`
- `GeneralizationCandidate`
- durable `ValidationObservation` history
- Retention history
- `EvidenceRetrieval`
- `LearningArtifact`
- `LearningCheckpoint`

EvidenceSet 仍是正式领域概念，但 v1 可通过 Revision↔Evidence 关系表表达，不要求单独 EvidenceSet 表。

## 24. P2-D v1 SQLite 关系模型

第一版采用规范化 SQLite，不做事件溯源、图数据库、大 JSON blob 或通用 `metadata/extra/context` 逃生字段。

```text
learning_topics
  id PK
  title
  scope
  created_at
  updated_at

learning_goals
  id PK
  topic_id FK
  objective
  status
  created_at
  updated_at

learning_goal_prerequisites
  goal_id FK
  prerequisite_goal_id FK

learning_claims
  id PK
  topic_id FK
  scope
  claim_kind
  created_at

claim_revisions
  id PK
  claim_id FK
  claim_text
  source_commit
  reason
  created_at

source_evidence
  id PK
  repository
  commit_sha
  tree_sha
  path
  file_sha
  symbol
  symbol_kind
  start_line
  end_line
  evidence_kind
  created_at

claim_revision_evidence
  claim_revision_id FK
  source_evidence_id FK
  role
  position

understanding_evidence
  id PK
  method
  prompt
  user_response
  verified_at

understanding_evidence_claims
  understanding_evidence_id FK
  claim_revision_id FK
  result

learning_hypotheses
  id PK
  topic_id FK
  goal_id FK
  text
  unresolved_reason
  resolved_by_claim_id FK nullable
  created_at

next_steps
  id PK
  goal_id FK
  text
  status
  is_primary
  created_at
  updated_at
```

明确不进入 durable schema：retrieval query/rank/score、LLM confidence/importance/mastery score、parser/debug metadata、UI cache、grader chain-of-thought。

## 25. 现有运行时 projection 与新长期真值的边界

现有 `AnswerClaimV1` / `AnswerClaimSnapshotV1` 属于**单个 ChatTurn 最终回答的结构化 projection**；其 identity 依赖 answer hash，并含 answer-level source/status 语义。它不是跨会话稳定的 LearningClaim lineage，不能通过改名直接升级为 `LearningClaim`。

现有 `EvidenceRefV1` / `EvidenceSnapshotV1` 属于**ChatTurn evidence projection**，包含 score、candidate/read/selected/rejected、provider status、selection/rejection reason 等过程/展示字段。它可以作为 retrieval/candidate 输入之一，但不能原样持久化成 `SourceEvidence`。

现有 `ChatThread.learning_state.confirmed_points`、旧 Markdown memory、session summary 都只能作为兼容展示/候选输入；**不得批量自动提升为 formal LearningClaim 或 confirmed mastery**。只有满足新 Evidence + Understanding 合同的新闭环才能产生正式长期学习真值。

## 26. P2-D v1 UI 边界

第一版只要求学习过程中真正需要看见的内容：

- 当前 LearningGoal；
- 1–3 个核心 Claim；
- Primary Evidence + 可展开 Supporting；
- 明确区分的 Hypothesis；
- 一次短 Understanding Validation；
- 1 个 Primary NextStep（必要时最多 2 个 optional）。

Evidence v1 只需要渐进披露前两层：

```text
Level 0: Claim + Primary symbol
Level 1: path/line + Supporting
```

以下明确后置：知识图谱、Claim 管理器、Revision timeline、Route editor、Retention/Stale dashboard、CI monitoring center、Topic hierarchy browser、复杂 provenance graph。

## 27. P2-D Golden Learning Journey

P2-D 不以“表建好了 / API 存在 / 页面出现卡片”作为完成标准。完整闭环必须至少验证：

```text
真实源码问题
→ Topic + Goal
→ 自动 commit-pinned source retrieval
→ deterministic line/symbol mapping
→ one-hop candidates
→ Evidence convergence
→ Claim rev1 或 Hypothesis
→ 短 UnderstandingEvidence
→ Goal closure
→ durable NextStep / Resume
→ 关闭并重新打开，不依赖完整 Chat history
→ Primary source 发生实质变化
→ historical confirmed 保留 + stale_candidate
→ explicit revalidation
→ same Claim lineage + new immutable Revision
```

必须覆盖 provider unavailable、无 Primary、CI failure、skip validation、supporting drift、duplicate reuse、snapshot/index cache reuse 等失败与性能边界。

## 28. 旧运行时实体

ChatThread / ChatTurn / GroupThread / NewsRun / ToolRun / MemoryTransaction / Operation / RetrievalIndex 等历史领域定义仍有参考价值，但当前 owner 与运行时状态统一以 [`docs/STATE_MODEL.md`](docs/STATE_MODEL.md)、[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) 和代码为准。旧 v0.8→v0.9 原文保存在 [`docs/archive/DOMAIN_MODELS_V08_V09.md`](docs/archive/DOMAIN_MODELS_V08_V09.md)。
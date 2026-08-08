# Study Agent 领域模型

> **稳定语义 owner。** 当前进度不在此维护，请看 [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)。
>
> 2026-08-08：P2-D 源码学习与验证领域合同已冻结。本文描述目标语义；其中部分对象尚未进入生产持久化，实施状态必须以 `PROJECT_STATUS.md` 为准。

## 1. 领域总览

```text
LearningTopic
├─ LearningGoal
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
  question: string;
  status: LearningGoalStatus;
  createdAt: string;
  updatedAt: string;
};
```

规则：
- 聊天关闭不等于 Goal 完成；
- 无活动不自动变 `abandoned`；
- 不使用伪精确的完成百分比；
- Agent 可以澄清/收窄 Goal，但不能静默改变语义方向；真正的新方向创建候选新 Goal。

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

默认恢复最近一个 active Goal；UI 优先表达“上次学到 / 当前卡点 / 继续”。

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

长期保存优先：机制、边界、不变量、决策性事实。行号、临时调用、搜索排名等默认留在 Evidence / session context。

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
  reason: RevisionReason;
  createdAt: string;
};
```

- 历史 Revision 永不原地覆盖；
- repo 每个 commit 不自动制造 Revision；
- Primary Evidence 发生实质变化后，经过显式 revalidation 才产生新 Revision；
- 同一学习问题答案随架构演进而变化时保持 lineage；问题本身被淘汰时用 `supersededBy` 连接新 Claim。

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
- role 属于 Claim→Evidence 关系，不属于 SourceEvidence 本体。

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
1. 选出 1 个最直接 Primary；
2. Supporting 去重；
3. 优先覆盖不同证明维度（实现、caller/callee、test、contract、prerequisite）；
4. 不为了凑数量加入弱证据；
5. 候选默认不进入 durable truth；
6. 不要求用户逐条审批，但 committed Evidence 必须可审计、可质疑、可重新验证；真正语义歧义才打断用户。

## 10. 源码自动探索边界

默认只自动扩展 Primary symbol 的**一层直接结构关系**：直接 caller/callee/import/implementation/test/config/contract。

超过一跳必须创建新的显式 evidence retrieval，并保留“为什么继续深入”。唯一例外是严格的 transparent forwarding：无业务分支、无状态变化、无领域语义变换的机械透传层可穿透。

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
- 当前 P2-D-1 只需要 runtime observation/cache 语义，不引入 durable CI history。

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
- revalidation 不覆盖历史 Revision。

## 13. UnderstandingEvidence

`confirmed` 必须由用户产生的理解证据支撑；Agent 无权自证。

```typescript
type UnderstandingMethod = "explain" | "apply" | "practice";
type UnderstandingResult = "pass" | "partial" | "fail";

type UnderstandingEvidence = {
  id: string;
  claimIds: string[];
  method: UnderstandingMethod;
  prompt: string;
  userResponse: string;
  result: UnderstandingResult;
  verifiedAt: string;
};
```

- 用户说“懂了”只代表 self-reported/attempted，不直接 confirmed；
- 默认最小充分验证，一个关键问题即可；复杂小节通常一次覆盖 1–3 个强相关 Claim；
- 优先应用/预测/解释，不做题海；
- 用户可跳过验证继续学习，但 Claim 保持 unverified；
- 低价值 `fact` 可不要求理解验证。

## 14. Retention

历史 `confirmed` 表示“曾经通过验证”，不会因时间或一次回忆失败被改写。

Retention 独立表达：`fresh / review_candidate / needs_refresh / rechecked`。时间只能产生复习建议，不能推断用户已经忘记。复习优先情境触发；Study Agent 当前不扩张成完整间隔重复/Anki 系统。

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
  text: string;
  reason: string;
  candidateRefs: string[];
  unresolvedReason: UnresolvedReason;
  resolvedBy?: string;
};
```

可证实子命题应拆成 Claim，不确定剩余继续作为 Hypothesis。解决后创建新 Claim，并通过 `resolvedBy` 保留历史，不原地变身。

## 16. NextStep

Hypothesis 不默认制造任务。只有直接阻塞当前 Claim、用户问题或理解验证的 unresolved item 才进入 NextStep。

- 默认 1 个 primary NextStep；必要时最多 2 个 optional；
- NextStep 必须是行动，不是 Hypothesis 文本复制；
- background unresolved 静默保留；
- 用户可主动提升 background item；
- Hypothesis resolved 后可自然完成关联 NextStep。

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

## 20. 旧运行时实体

ChatThread / ChatTurn / GroupThread / NewsRun / ToolRun / MemoryTransaction / Operation / RetrievalIndex 等历史领域定义仍有参考价值，但当前 owner 与运行时状态统一以 [`docs/STATE_MODEL.md`](docs/STATE_MODEL.md)、[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) 和代码为准。旧 v0.8→v0.9 原文保存在 [`docs/archive/DOMAIN_MODELS_V08_V09.md`](docs/archive/DOMAIN_MODELS_V08_V09.md)。

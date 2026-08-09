# Study Agent 系统不变量

> **硬约束 owner。** 本文件记录“无论如何重构都必须成立”的条件，不记录当前进度。实施状态看 [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)。
>
> 2026-08-09：已纳入 P2-D GrillMe 决策 1–49。

## 1. 文档与真值治理

### D1 — 单一进度 owner
`docs/PROJECT_STATUS.md` 是唯一当前进度入口。不得新增并列长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT。

### D2 — planned 不覆盖 committed truth
`planned / attempted / partial / failed / hypothesis` 不得覆盖已提交学习真值。

### D3 — 历史不可伪装成当前
旧 roadmap、迁移计划、架构快照必须带历史语义；当前架构/状态不得由 archive 文档声明。

## 2. 运行时 owner

### R1 — SQLite durable truth
React 是交互面，FastAPI 是应用入口，SQLite durable entities 是生产运行时事实。前端、Markdown、Persona 均不得维护第二套运行真值。

### R2 — Runtime 单 owner
EvidenceRuntime、LearningSessionRuntime、ExtensionRuntime 各自拥有自己的领域状态；WorkspaceCoordinator 只负责编排跨域取消/清理，不复制领域状态。

### R3 — 实验能力单入口
群聊、受控工具、workflow/开发诊断只从单一 Lab surface 进入，默认休眠。capability 存在不等于拥有独立普通模式产品面。

### R4 — 配置单 owner
平台安全配置只能由一个 owner 解析与校验；装配层、脚本、测试不得复制第二套规则。

## 3. Chat / Session

### C1 — 一个用户问题一个 ChatTurn
中断 + continuation 更新同一 Turn；retry 才创建带 parent lineage 的新 Turn。

### C2 — Turn ID 稳定
完成或可续写 Turn 的 identity 不因 UI 刷新、断线恢复或 continuation 改变。

### C3 — 响应 owner 校验
异步回调必须匹配 operation/generation/owner；stale response 不能覆盖新状态。

### C4 — Session 原子恢复
恢复 Session 时一次性恢复其消息、设置、route、RAG 与恢复状态，不把 Group/News 等独立 scope 一并清空。

## 4. SourceEvidence

### E1 — exact source identity
Committed SourceEvidence 至少固定 repository、exact commit、path、file SHA、line range；symbol/tree SHA 作为可复核定位增强。

### E2 — Evidence 不携带过程噪声
Query、rank、search score、chunk score、parser debug、LLM confidence、整段 source copy 不属于 SourceEvidence durable truth。

### E3 — CI 不属于 SourceEvidence identity
CI / provider 状态是独立 ValidationObservation。CI failure、pending、unavailable 都不能自动把合法 SourceEvidence 判为 invalid。

### E4 — exact-SHA CI
当 CI 与源码 evidence 建立关联时，payload commit SHA 必须与 snapshot SHA 精确一致；不允许“同 branch 差不多”的关联。

### E5 — EvidenceSet 有界
一个 LearningClaim Revision 必须有且只有 1 个 Primary Evidence；Supporting 0–4 个。超过上限默认要求删弱证据或拆 Claim。

### E6 — Supporting role 只有关系语义
`corroborating / prerequisite` 属于 EvidenceSetEntry，不固化到 SourceEvidence。

### E7 — 候选非 durable
普通 Evidence Candidates 只存在于一次检索/收敛过程。只有 committed EvidenceSet 进入长期真值。

### E8 — 自动探索最多一跳
从 Primary symbol 自动扩展只允许一层直接结构关系。更深探索必须形成新的显式 retrieval 与原因。严格机械透传层可作为窄例外穿透。

### E9 — one-hop 由学习应用层负责
底层 GitHub graph/impact 能力可以支持更深查询；P2-D learning application service 必须显式调用 one-hop，而不是假设 provider 默认 depth 永远符合学习合同。

## 5. Claim / Revision

### L1 — 无 Primary 不建 Claim
找不到可靠 Primary Evidence 时只能创建 LearningHypothesis，不允许用 `proposed Claim` 掩盖证据不足。

### L2 — Claim 只保存长期价值命题
机制、边界、不变量、决策性事实可成为 durable Claim；局部行号、临时调用、搜索细节默认不保存为 Claim。

### L3 — Revision 不可变
Claim 的具体文本、EvidenceSet 与 UnderstandingEvidence 写入不可变 Revision。重验证创建新 Revision，不覆盖旧 Revision。

### L4 — Git commit ≠ Claim revision
仓库每次提交不自动生成学习 Revision；只有用户实际重新验证形成的新学习真值才产生 Revision。

### L5 — confirmed 与 freshness 分离
仓库变化不能把历史 `confirmed` 改回 partial/unknown。

### L6 — Primary 变化触发 stale candidate
Primary 实质变化 → `stale_candidate`；Primary 被删除/无法映射 → `source_changed`。历史结论仍保留其当时版本语义。

### L7 — Supporting drift 默认不打断
Supporting 变化默认只记录 drift；只有 prerequisite 的实质变化可以触发 stale candidate。

### L8 — 历史不自动语义合并
LLM 不得因为“看起来相似”删除/合并历史 Claim。疑似重复只建立关联候选。

### L9 — 冲突显式存在
ClaimConflict / EvidenceConflict 不得通过“最新覆盖旧值”消失。能解释为版本演进、scope 差异时显式解析；否则 unresolved。

### L10 — AnswerClaim projection ≠ LearningClaim
`AnswerClaimV1 / AnswerClaimSnapshotV1` 只描述单个 ChatTurn 最终回答。其 answer-hash identity、answer-level status/source 不能直接升级成跨会话 LearningClaim lineage。

### L11 — 旧 confirmed_points 不自动升级
`ChatThread.learning_state.confirmed_points`、旧 Markdown memory、session summary 只能作为兼容展示或候选输入。没有新的 SourceEvidence + UnderstandingEvidence 闭环，不得批量转成 formal LearningClaim 或 confirmed mastery。

## 6. Understanding / Retention

### U1 — Agent 不能自证掌握
Agent 生成了正确解释不等于用户掌握。

### U2 — confirmed 必须有用户理解证据
对需要掌握的 mechanism/boundary/invariant，`confirmed` 必须由 explain/apply/practice 类型的 UnderstandingEvidence 支撑。

### U3 — “懂了”不是自动 confirmed
用户自评理解可以记录为 self-reported/attempted；系统应采用最小充分验证，而不是伪造 confirmed。

### U4 — 可跳过验证
用户可以继续学习而不做验证，但对应 Claim 保持 unverified。

### U5 — 验证短闭环
默认在语义小节结束时验证 1–3 个强相关 Claim；不每形成一个 Claim 就打断，也不积压成章节末考试。

### U6 — retention 不覆盖历史 mastery
时间或一次回忆失败不能抹掉“曾经 confirmed”。`review_candidate / needs_refresh / rechecked` 是独立维度。

### U7 — 不扩张成 Anki
复习优先情境触发；当前产品不以卡片队列、遗忘曲线、全局待复习压力为核心。

### U8 — Understanding durable 数据保留原始用户回答
可以保存 prompt、user response、method、per-Claim result 与时间；不得把 grader chain-of-thought、LLM confidence 或 mastery 百分比当成 durable mastery truth。

## 7. Hypothesis / NextStep

### H1 — 假设与 Claim 分离
Hypothesis 可以记录候选线索与 unresolved reason，但不能伪装为有证据的 Claim。

### H2 — 部分可证实必须拆分
能证明的子命题成为 Claim；剩余不确定部分继续 Hypothesis，不能把“源码事实只证实一半”误用用户理解 `partial` 表达。

### H3 — resolved_by 保留解决链
Hypothesis 解决后创建新 Claim，并通过 `resolved_by` 连接，不原地改对象类型。

### H4 — 不自动制造 backlog
只有 blocking unresolved 才生成 NextStep；background unresolved 静默保留。

### H5 — NextStep 收敛
默认 1 个 Primary NextStep，必要时最多 2 个 optional；NextStep 必须描述行动。

### H6 — 用户 pinned 意图优先
Agent 可重排派生 NextStep，但不得静默替换、删除或自动完成用户明确 pinned 的方向，除非该动作已完成或用户确认调整。

## 8. Topic / Goal / Resume

### G1 — Topic 与 Goal 分离
Topic 是稳定机制域；Goal 是一次具体学习目标。

### G2 — 聊天结束不等于 Goal 完成
Goal 只有在核心问题闭合、blocking unresolved 清零、必要 Claim 形成并完成/跳过理解验证后才 completed。

### G3 — Agent 不静默换 Goal
可澄清/收窄，但新语义方向必须成为 proposed new Goal/NextStep。

### G4 — 跑题不丢学习位置
本地分支吸收进 Goal；相关 detour 回答后恢复；真正新主题另开 Goal，旧 ResumePoint 保留。

### G5 — 恢复语义状态
ResumePoint 锚定 Topic / active Goal / last confirmed / unresolved / next action / source context，而不是 last_message_id。

### G6 — 首页 action-first
主层级是 `NextStep → Goal → Topic`；不得退化成 Topic 文件夹或统计仪表盘。

### G7 — prerequisite 稀疏且无环
只有“不知道 X 会明显妨碍理解或验证 Y”时才建立 Goal prerequisite；不得把所有相关知识连成知识图谱。

### G8 — 用户可跳过 prerequisite
非关键前置只记录 gap；真正阻塞当前推理/验证的前置才进入 blocking unresolved。跳过不得制造惩罚性评分，也不得伪装为已掌握。

### G9 — focus 不由 Agent 全局优化
多个 active Goal 时优先用户 pinned focus；无 pin 时恢复最近明确投入的 active Goal。Agent 不以“效率/遗忘概率”等理由跨 Topic 偷换主线。

## 9. Freshness 与 UI

### F1 — stale 提示情境化
无关 stale 静默记录；当旧 Claim 即将参与当前解释、推理或 prerequisite 时才主动提醒/阻塞。

### F2 — Evidence 渐进披露
默认 Claim + Primary symbol；第二层 path/lines + Supporting；第三层 exact commit/CI/Revision history。普通 UI 不得退化成 IDE。

### F3 — v1 UI 不做管理后台
P2-D v1 只要求 Goal、少量 Claim、Primary/Supporting、Hypothesis、短验证和 Primary NextStep。知识图谱、Claim manager、Revision timeline、Route editor、Retention/Stale dashboard、CI monitoring center 均后置。

## 10. Persona / Provider

### P1 — 多角色单 truth
所有 Persona 共享同一 Topic / Goal / Claim / Evidence / Understanding / NextStep durable truth。

### P2 — Persona 不裁决 truth
Persona 只能改变解释策略、案例、节奏、措辞与短期互动 context，不能改变 Claim truth、Evidence validity、mastery、freshness。

### P3 — 层级不可反向污染
`Truth → Learning → Pedagogy → Persona`；下层不得覆盖上层。

### P4 — Provider 无全局王者
GitHub / RAG / Web 都只是 Evidence Provider。先判断 truth domain：implementation / project_decision / external_fact，再选适配来源。

### P5 — 设计与实现差异不可隐藏
项目 decision 与实际源码冲突必须显示 divergence；外部规范与项目实现不一致必须显示 deviation；同域冲突无法解析则进入 EvidenceConflict。

### P6 — Provider failure ≠ negative fact
provider unavailable、permission denied、rate limit、not found 等必须保留各自语义；“当前无法验证”不能被推导为“事实不存在/Claim 为假”。

## 11. Cache / Validation

### K1 — SourceSnapshot 强 commit 缓存
同一 repository + exact commit 的 source snapshot / structure index 不应因普通搜索重复重建。

### K2 — CI cache 独立
CI Observation 使用独立短 TTL / 显式刷新策略；普通源码学习不能因 CI refresh 阻塞或失败。

### K3 — runtime cache ≠ durable history
P2-D v1 不因 cache 需求引入 durable CI history。

## 12. Agent 主动性 / Tool

### A1 — goal-serving read 可以自动
完成当前 LearningGoal 所必需的只读 GitHub/RAG/Web retrieval 可以自动执行；不要求逐步确认。

### A2 — goal-expanding research 必须显式
竞品、业界最佳实践、新技术路线等会扩大当前 Goal 的研究必须先提出新 Goal/GeneralizationCandidate/NextStep，不得静默扩张。

### A3 — Tool chain 必须有界
普通 Agent turn 使用短、有界执行链；达到预算后必须综合、形成 Hypothesis，或以新的 recorded reason 启动深挖，禁止无限循环。

### A4 — 失败默认一次有意义重试
短暂网络/5xx 可重试一次；404、权限拒绝、schema error 等明确失败不做无意义重复。

### A5 — fallback 不得伪装 evidence 类型
GitHub exact evidence unavailable 时，Web/RAG fallback 只能以自己的 provider/type 存在，不能冒充 commit-pinned SourceEvidence。

### A6 — read-only 自动，副作用确认
外部写入、发送、部署、付费、不可逆动作必须显式确认。Derived internal state 可以自动更新；改变用户明确长期意图的内部动作也必须确认。

### A7 — durable truth 只在语义闭环点提交
Agent 不能边解释边持续写长期 Claim。Candidate / temporary interpretation / retrieval note 保持 ephemeral；只有 Evidence 收敛、claim-worthiness 通过并到达 semantic closure 后才可自动提交少量 durable truth。

## 13. Context / Artifact / History

### X1 — Chat history ≠ resume truth
Raw ChatTurn 可以长期保留用于审计，但长期恢复不得依赖重放完整聊天。

### X2 — Artifact ≠ second truth owner
LearningArtifact 只组合/引用 Goal、Claim、Evidence 形成可读笔记；它可以过时，但不得静默重写历史，也不得拥有第二套 Claim/Evidence truth。

### X3 — ResumeContext 必须可重建
ResumeContext 必须从 durable Goal/Claim/Hypothesis/NextStep/Evidence 派生；LLM summary 只能辅助展示。

### X4 — Context compression 不删除 durable history
可以不再把旧过程文本送进 prompt，但 ClaimRevision、SourceEvidence identity、UnderstandingEvidence raw response、用户显式意图、冲突解决历史必须可审计保留。

## 14. P2-D v1 存储边界

### V1 — 6 core + 2 light
P2-D v1 正式持久化：LearningTopic、LearningGoal、LearningClaim、ClaimRevision、SourceEvidence、UnderstandingEvidence；轻量持久化 LearningHypothesis、NextStep。

### V2 — 合同对象不强行建表
LearningRoute、ClaimConflict、GeneralizationCandidate、durable ValidationObservation history、Retention history、EvidenceRetrieval、LearningArtifact、LearningCheckpoint 当前只保留合同，除非后续切片明确提升。

### V3 — 关系模型优先
P2-D v1 使用规范化 SQLite 关系表。不得以事件溯源、图数据库、大 JSON blob 或通用 `metadata/extra/context` 字段绕开当前 schema 责任。

### V4 — durable schema 不存过程评分
retrieval query/rank/score、LLM confidence/importance/mastery score、parser/debug metadata、UI cache 不进入核心长期表。

### V5 — EvidenceSet 可关系表达
EvidenceSet 是领域合同，但 v1 可通过 claim_revision_evidence 的 primary/supporting role 表达，不需要独立 EvidenceSet 表。

## 15. 验收原则

### T1 — Golden Learning Journey 是 P2-D 完成门槛
P2-D 必须完成真实源码问题的 `Goal → pinned Evidence → Claim/Hypothesis → Understanding → Goal closure → durable resume → source change → revalidation/new Revision` 全链，而不是只验证表/API/UI 分别存在。

### T2 — 失败边界必须锁定
至少覆盖：GitHub unavailable、无 Primary、CI failure、skip validation、supporting drift、Primary changed、无完整 chat 的 resume、duplicate lineage reuse。

### T3 — 性能边界必须锁定
同 repo+commit snapshot/index 复用；普通 retrieval 有界；CI unavailable 不阻塞 source-learning 主结果。

每新增/修改相关能力，测试必须优先锁定上述 invariant，而不是只锁某个 UI 文本或某次 bug 的偶然表现。旧 pre-P2-D 不变量原文保存在 [`docs/archive/STATE_INVARIANTS_PRE_P2D.md`](docs/archive/STATE_INVARIANTS_PRE_P2D.md)。
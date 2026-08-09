# Testing Strategy

> 测试优先锁 invariant 与 owner，而不是锁某次实现偶然形状。
>
> 2026-08-09：P2-D v1 的完成标准已经从“组件分别存在”收敛为真实 Golden Learning Journey。

## 1. 核心门禁

- Python unit/integration；
- React/Vitest；
- TypeScript build；
- FastAPI + SQLite integration；
- Golden Journey / browser tests；
- migration/recovery/failure injection。

实际命令与 CI workflow 以仓库 `.github/workflows/` 为准。

## 2. P2-D-1 Source Evidence 必测

- lexical query 能稳定落到 match line；
- nested symbol 选择 innermost containing symbol；
- 无 symbol 时 graceful path+line fallback；
- exact commit/file/line provenance 可复核；
- 自动结构扩展不越过 one-hop；
- CI payload SHA mismatch → unavailable/拒绝关联；
- CI failure/unavailable 不使 source evidence invalid；
- SourceSnapshot cache 与 CI short-TTL cache 分离；
- custom/offline snapshotter 不因为 source search 隐式发 live CI；
- P2-D learning service 调用 graph 时显式 `depth=1`，不依赖通用 graph 默认值。

## 3. P2-D-2 Durable Learning Truth 必测

### 3.1 Migration / repository

- 从当前 schema version 正常升级到 P2-D v1 schema；
- migration 中途 failure injection 必须 rollback，不留下半张表/半个 ledger 状态；
- FK/unique/check 等关键约束生效；
- ClaimRevision + SourceEvidence associations 原子提交，任一失败全部 rollback；
- 重启后 Topic/Goal/Claim/Revision/Evidence/Hypothesis/NextStep 可完整读取；
- 新 schema 不引入通用 `metadata/extra/context` JSON 逃生字段。

### 3.2 SourceEvidence / convergence

- SourceEvidence durable identity 包含 repository/exact commit/path/file SHA/line range；
- query/rank/search score/chunk score/provider status/CI status/LLM confidence 不进入 SourceEvidence；
- exactly 1 Primary；
- Supporting ≤ 4；
- supporting role 只允许 corroborating/prerequisite；
- candidate 去重且优先不同证明维度；
- 不为凑 5 个证据加入弱项；
- 无合法 Primary → 只创建 LearningHypothesis，不创建 Claim；
- 部分可证实陈述拆成 Claim + Hypothesis；
- one-hop 自动扩展有界，超过一跳需要新的 retrieval reason。

### 3.3 Existing projection boundary

- `AnswerClaimV1` 不被直接写成 LearningClaim；
- `EvidenceRefV1/EvidenceSnapshotV1` 的 score/provider status/selection reason 不进入 SourceEvidence；
- legacy `learning_state.confirmed_points` 不自动生成 formal Claim/confirmed mastery；
- Answer/evidence snapshots 可以作为 candidate input，但 committed truth 必须重新通过 P2-D contract。

### 3.4 Duplicate lineage

- 同一显式 semantic identity 的 candidate 复用已有 Claim lineage；
- 新 Evidence / revalidation 不能创建第二个同义 Claim；
- v1 不用 embedding similarity 阈值自动合并历史 Claim。

## 4. P2-D-3 Understanding / Closure / Resume 必测

### 4.1 Commit point

- 普通 chat turn / retrieval 中间阶段不得写 durable Claim；
- 只有 semantic closure + evidence convergence + claim-worthiness 通过后才提交；
- closure source 变化时必须拒绝 stale commit；
- retry/recovery 不重复创建 ClaimRevision。

### 4.2 Understanding

- Agent 自己生成解释不能产生 confirmed；
- self-reported “懂了”不能绕过 UnderstandingEvidence；
- explain/apply/practice 才是 allowed method；
- 一次 UnderstandingEvidence 可关联 1–3 个 ClaimRevision，并分别 pass/partial/fail；
- raw user response 必须 durable；
- grader confidence / chain-of-thought 不成为 mastery truth；
- skip validation 后 Goal 仍可 completed，但对应 Claim 保持 unverified。

### 4.3 Goal / Hypothesis / NextStep

- 浏览器关闭/会话结束不自动 completed；
- blocking unresolved 阻塞 Goal closure；background unresolved 不阻塞；
- 无 Primary 时 Hypothesis 可 durable，但不能走 confirmed path；
- Hypothesis `resolved_by` 新 Claim，不原地改对象类型；
- 默认 1 Primary NextStep，optional ≤2；
- 用户 pinned NextStep 不被 Agent 静默重排/删除。

### 4.4 Resume

- semantic ResumePoint 可跨刷新/进程重启恢复 Goal/Claims/unresolved/NextStep；
- resume 不依赖完整 Chat history；
- 删除/不加载旧聊天正文后，当前学习位置仍可重建；
- durable P2-D state 优先于 legacy `learning_state`；旧 session 在没有新 state 时仍能 fallback；
- legacy `confirmed_points` fallback 只展示旧状态，不升级 formal Claim；
- detour/new topic 不丢原 active Goal；
- pinned focus 优先于最近临时 detour；
- Persona 切换后读取同一 durable learning truth。

## 5. P2-D-4 Freshness / Revalidation 必测

- repo HEAD 前进但 Primary 实质不变 → current；
- Primary 实质变化 → stale_candidate；
- Primary removed/unmappable → source_changed；
- supporting corroborating drift → 不触发 stale；
- supporting prerequisite material drift → 可触发 stale_candidate；
- stale 只在相关 Goal/Claim 被恢复/引用/显式检查时评估；
- 无后台全仓 stale 通知；
- revalidation 创建同一 Claim lineage 的新 immutable Revision；
- rev1 Evidence/Understanding 历史仍可读；
- CI failure/unavailable 不阻止 SourceEvidence freshness 判断；
- provider unavailable 只能得到 unavailable / Hypothesis / blocked 语义，不能推导“Claim false”。

## 6. Provider / Tool boundary 必测

- goal-serving read-only retrieval 可以自动；
- goal-expanding research 不得静默发生；
- 普通 Agent turn 的 tool chain 有界；
- 达预算后只能 synthesize / Hypothesis / explicit deeper retrieval；
- transient provider failure 最多一次有意义 retry；
- 404/permission/schema failure 不做循环重试；
- fallback provider 不冒充原 evidence type；
- read-only 无需确认；external write/send/deploy/paid/irreversible 需要确认；
- derived internal update 可自动；user-intent mutation 需要确认。

## 7. P2-D Golden Learning Journey

Golden Journey 使用真实源码问题，不使用“建一条假 Claim”作为验收。

### 场景：理解 session recovery 为什么必须保留 ChatTurn identity

1. 用户提出真实源码问题；
2. 系统建立 Topic=`会话状态与恢复` 与具体 LearningGoal；
3. Agent 自动执行 commit-pinned source retrieval；
4. wide chunk 收窄到 deterministic match line，并映射 innermost source symbol；
5. 以 Primary 为根自动扩展 one-hop caller/test/contract 候选；
6. convergence 得到 exactly 1 Primary + 少量 Supporting；
7. 核心命题创建 LearningClaim rev1；
8. 对“是否所有异常恢复路径都满足”这类证据不足子问题只能创建 Hypothesis；
9. Agent 在语义小节结束提出 1 个短 explain/apply/predict 验证；
10. 用户回答形成 UnderstandingEvidence pass/partial/fail；
11. 核心问题闭合后 Goal completed，并保留 Primary NextStep（若有）；
12. 关闭应用/清空默认 prompt 中的完整历史聊天；
13. 新会话从 durable Goal/Claim/Hypothesis/NextStep 恢复“已确认/未解决/下一步”；
14. 模拟 Primary symbol 在新 commit 中发生实质修改；
15. 历史 rev1/confirmed 保留，freshness 变 stale_candidate；
16. 显式 revalidation 新 commit；
17. 结论仍成立时复用同一 Claim lineage，创建 rev2，而不是第二个重复 Claim。

## 8. Golden Journey 强制失败/边界案例

至少固定以下案例：

1. GitHub provider unavailable → 不生成假 Claim；
2. 无 Primary Evidence → Hypothesis only；
3. CI failed → SourceEvidence 仍有效；
4. 用户 skip validation → Goal 可结束、Claim 不 confirmed；
5. Supporting corroborating changed → drift only；
6. Primary changed → stale_candidate；
7. 完整 Chat history 不参与恢复 → durable resume 仍成立；
8. 同语义 Claim 再次出现 → 复用 lineage；
9. closure commit 前 source changed → 不提交 stale truth；
10. migration/repository transaction failure → 不留下部分 Claim/Evidence。

## 9. 性能 / boundedness 验收

P2-D v1 不先设伪精确毫秒 SLA，而锁复杂度边界：

- same repository + exact commit 的 snapshot/structure/code/graph index 可复用；
- 普通源码查询不得重复 fetch/rebuild 整仓；
- source exploration 默认 one-hop；
- provider request / page / work-item budget 生效；
- CI cache 与 SourceSnapshot cache 分离；
- CI unavailable / refresh failure 不阻塞 source-learning response；
- 一个普通学习 turn 不因为 Agent 自主探索产生无界 GitHub API 调用。

建议在 integration test 中对 mock provider call count 建上界断言，而不是只测最终文本。

## 10. UI / 浏览器验收

P2-D v1 只验证当前学习 surface，不新建管理后台：

- 当前 Goal；
- 1–3 个 Claim；
- Primary + expandable Supporting；
- Hypothesis 与 Claim 有明显视觉区别；
- 短 Understanding Validation；
- Primary NextStep；
- Evidence Level 0–1：symbol → path/line/supporting；
- stale_candidate 只在相关上下文出现轻提示。

浏览器/设备：

- Chromium Golden Journey；
- Firefox 核心流程抽样；
- WebKit 核心流程抽样；
- 至少一台实体手机：IME/input、scroll、drawer、Lab、recovery、长 SourceEvidence path/symbol/line 不横向撑破页面。

## 11. 文档验收

- `PROJECT_STATUS.md` 唯一声明当前阶段；
- 当前 architecture/domain/invariant/state/testing 文档互相链接，不维护重复 roadmap；
- archive 文档不得被当作 current owner；
- 实现状态与设计合同必须区分，禁止把“frozen design”写成“already shipped”；
- P2-D-2 / D-3 / D-4 的 scope、non-goal、验收只在 `PROJECT_STATUS.md` 维护当前执行状态，稳定合同回写 canonical docs。
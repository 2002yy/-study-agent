# Testing Strategy

> 测试优先锁 invariant 与 owner，而不是锁某次实现偶然形状。

## 1. 核心门禁

- Python unit/integration；
- React/Vitest；
- TypeScript build；
- FastAPI + SQLite integration；
- Golden Journey / browser tests；
- migration/recovery/failure injection。

实际命令与 CI workflow 以仓库 `.github/workflows/` 为准。

## 2. P2-D Source Evidence 必测

- lexical query 能稳定落到 match line；
- nested symbol 选择 innermost containing symbol；
- 无 symbol 时 graceful path+line fallback；
- exact commit/file/line provenance 可复核；
- 自动结构扩展不越过 one-hop；
- EvidenceSet exactly 1 Primary，Supporting ≤4；
- candidate 不进入 durable truth；
- CI payload SHA mismatch → unavailable/拒绝关联；
- CI failure/unavailable 不使 source evidence invalid；
- SourceSnapshot cache 与 CI short-TTL cache 分离。

## 3. Claim / Revision 必测

- 无 Primary Evidence 不可创建正式 Claim；
- Primary 变化只标 stale_candidate，不改历史 confirmed；
- source removed → source_changed；
- supporting corroborating drift 不触发强制 stale；
- prerequisite drift 可触发 revalidation；
- revalidation 创建新 Revision，不覆盖旧 Revision；
- repo 普通 commit 不自动制造 Revision；
- duplicate/conflict 不使用 latest-write-wins 静默合并。

## 4. Understanding 必测

- Agent 自己生成解释不能产生 confirmed；
- self-reported “懂了”不能绕过 UnderstandingEvidence；
- explain/apply/practice pass 才可升级需要验证的 Claim；
- skip validation 后仍可继续 Goal，但状态保持 unverified；
- retention/freshness 不覆盖历史 mastery。

## 5. Goal / Resume 必测

- 浏览器关闭/会话结束不自动 completed；
- blocking unresolved 阻塞 Goal closure；background unresolved 不阻塞；
- semantic ResumePoint 可跨刷新恢复 Goal/NextStep；
- detour/new topic 不丢原 active Goal；
- Persona 切换后读取同一 durable learning truth。

## 6. Provider conflict 必测

- implementation / project_decision / external_fact 使用不同 evidence domain；
- design-vs-code 显示 divergence；
- same-domain unresolved evidence conflict 保留为 EvidenceConflict；
- provider unavailable 不推导“事实为假”。

## 7. UI / 浏览器验收

当前 P2-D 后续必须包含：

- Chromium Golden Journey；
- Firefox 核心流程抽样；
- WebKit 核心流程抽样；
- 至少一台实体手机：IME/input、scroll、drawer、Lab、recovery。

Evidence UI 还应验证三级渐进披露以及窄屏不横向溢出。

## 8. 文档验收

- `PROJECT_STATUS.md` 唯一声明当前阶段；
- 当前 architecture/domain/invariant 文档互相链接，不维护重复 roadmap；
- archive 文档不得被当作 current owner；
- 实现状态与设计合同必须区分，禁止把“frozen design”写成“already shipped”。

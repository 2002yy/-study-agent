# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-07-27  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**证据身份、来源生命周期、实时/恢复一致性和普通/诊断展示已经完成；当前建立服务端 AnswerClaim 真值合同。**  
> 当前分支：`agent/answer-claim-owner-v1`。

本文件只维护当前事实、真实指标、缺口、执行顺序和门禁。历史细节以 Git 提交和 PR 为准。

## 1. 产品边界

学习主路径：

```text
当前目标
-> 教学或练习
-> 资料与外部证据
-> 理解验证
-> 已确认内容 / 未解决缺口
-> 明确下一步
-> 整理与恢复
```

- RAG 服务于“围绕自己的资料学习”。
- Web Research 服务于“需要外部事实时获得可信证据”。
- GitHub 是源码学习高级研究工具，不是第二个执行产品。
- Memory 是学习连续性基础设施。
- Workflow 只属于高级诊断。
- 群聊、新闻、工具保持实验功能。
- 当前不推进新向量数据库、GraphRAG、原生移动端、可执行仓库代理、掌握百分比或并列长期状态文档。

## 2. 当前架构与主链

当前架构：**React 19 + FastAPI + application services + SQLite**。

真值边界：

- React 只负责交互和可重建缓存；
- SQLite durable entities、committed learning state、评估和运行状态是运行真值；
- 用户确认后的长期学习记忆写入 Markdown memory；
- planned / attempted / failed 不得覆盖 committed truth；
- 多步流程由 application service + durable run 拥有。

已完成：

- TaskContract 单一真值；
- LearningClosureRun 与总结闭环；
- ThreadSummaryState；
- 学习状态去伪精化；
- 结构化恢复卡；
- 会话语义导航；
- UI 收敛和窄屏适配；
- 五条 Golden Journey 回归合同。

## 3. 已完成的证据主线

### PR #61：G13 live / restore parity

Merge SHA：`597006e99919ea7e5f5b02f01b1536b446da9a55`。

- 正确读取嵌套 `RagResult.chunk`；
- local evidence 使用稳定 `chunk_id`；
- 同来源不同 chunk 不错误折叠；
- 恢复 `pedagogy_snapshot.evidence_ids`；
- live -> persisted -> restored 等价回归。

CI #1317 全绿。

### PR #62：server-owned EvidenceSnapshot v1

Merge SHA：`fcfb9bc66750d10c822306fae735424e658b19ef`。

- `EvidenceRefV1`、`EvidenceSnapshotV1`、`ClaimEvidenceLinkV1`；
- 服务端拥有证据身份和生命周期；
- 新 Turn 在现有 JSON 快照内持久化；
- 旧 Turn 确定性兼容恢复；
- React 优先读取服务端快照；
- 教学引用与事实 claim link 分离。

CI #1340 全绿。

### PR #63：durable ResearchRun source truth

Merge SHA：`f1b2a4f9d481a16e5c93e6ac8fb4c0f9ee2f45c2`。

- selected/rejected ResearchRun 来源进入 ChatTurn 真值；
- 保存 Provider 状态、stop reason、URL/domain、相关度和排除原因；
- continuation/retry 不能切换来源 owner；
- 同一 Run 恢复使用原 Turn 冻结真值；
- 实时与数据库恢复读取同一 `rag_snapshot`。

CI #1357 全绿。

### PR #64：adopted evidence / diagnostics 分层

Merge SHA：`451bc4a78fc3eda6219083371591aa46c8e62900`。

- 普通层只显示 selected 或教学明确引用的证据；
- candidate/read/rejected、分数、Provider 状态和工具调用进入显式诊断详情；
- 没有 selected 时不把候选来源包装成回答来源；
- 普通复制和诊断复制分离；
- 链接换行、触控尺寸和窄屏溢出已处理；
- `web_tools.calls` 使用结构化类型收窄。

CI #1368 全绿：后端测试、RAG K1、Ruff、package、detect-secrets、mypy、195 项前端测试、TypeScript 与 Vite build。

## 4. RAG K1 当前基线

K1a–K1e 已进入 `main`：

- 12 份学习文档；
- 30 个 retrieval case，其中 26 个 answerable；
- 10 个 answer-quality gold case；
- stale / forbidden leakage：0；
- source recall@K：0.923077；
- nDCG：0.903600；
- adaptive recall@K：0.942308；
- multi-source recall@K：0.9；
- deterministic answerable supported：26/26；
- deterministic unanswerable block：4/4；
- real-provider replay harness 已完成。

尚未完成：还没有实际成功的正式真实 Provider benchmark 可作为模型质量结论。

## 5. 当前缺口：AnswerClaim owner

目前已有 EvidenceRef 和 ClaimEvidenceLink schema，但尚无服务端 owner 能稳定回答：

- 最终回答包含哪些可核对 assertion；
- 哪些内容只是教学指令、问题、建议或不确定表达；
- assertion 的稳定 ID；
- assertion 与 EvidenceRef 的支持关系；
- 中断、失败、重试和 continuation 后哪个版本才是最终真值。

禁止：

- 按标点切分回答并把每句当 claim；
- 用关键词或标题匹配自动建立支持关系；
- 把 `PedagogyTurnPlan.evidence_ids` 当作 answer claim links；
- partial/interrupted 文本覆盖 completed claim truth。

## 6. 精确执行顺序

### P0-2c2a：AnswerClaimSnapshot v1（当前）

目标：建立版本化服务端合同和 ChatTurn 生命周期边界，本 PR 不自动生成 claim。

拟新增：

```text
AnswerClaimV1
- id
- text
- kind: factual | instructional | question | recommendation | uncertainty
- status: asserted | qualified | withdrawn
- source: provider_structured | application_supplied

AnswerClaimSnapshotV1
- schema_version
- answer_hash
- claims
- claim_links
- producer
- status: unavailable | supplied | validated | rejected
- reason
```

规则：

1. claim ID 由规范化 claim text + final answer hash 确定性产生，或接受上游已验证 ID；不得按数组位置生成。
2. ChatTurn 只在 final answer 与 snapshot 的 answer hash 一致时接受 claim truth。
3. claim links 只接受已知 EvidenceRef ID。
4. 空 claim ID、未知 evidence、非法枚举或越界 confidence 被拒绝。
5. interrupted / failed / abandoned Turn 不产生 validated snapshot。
6. retry 创建新 Turn 和新 answer hash，不继承父 Turn claims。
7. continuation 在新 final answer 完成前使旧 claim snapshot 失效。
8. 当前生成链没有结构化 claims 时保存 `unavailable`，不从自然语言回答推断。
9. 旧 Turn 安全回退 unavailable。
10. 不增加 SQLite schema，继续使用现有 JSON 快照边界。

本 PR不修改主模型 prompt，不增加额外模型调用，不改 UI。

门禁：

- deterministic ID / answer hash；
- answer hash mismatch 拒绝；
- evidence ID 和 confidence 校验；
- interrupted / retry / continuation 生命周期测试；
- old Turn compatibility；
- full CI。

### P0-2c2b：结构化生成接线与质量基线

合同稳定后再选择同次生成 sidecar 或独立 evaluator，先以 record-only 评估 schema parse rate、claim coverage、unsupported claim rate、link precision/recall 和额外成本。质量未达标时不进入普通 UI。

### P0-3：架构真值与 Streamlit 清理

- 同步 `ARCHITECTURE_STATUS.md`、`STATE_MODEL.md`；
- 删除或迁移 `src/ui`；
- requirements 移除 Streamlit 并重新锁定；
- README / USER_GUIDE 同步；
- package diff 和全量回归。

### P1

1. 执行 RAG-K1f 真实 Provider 回答基线；
2. RAG-K2 结构化 parser 和 structure-aware chunking；
3. 学习成效基线。

### P2

1. 自适应 `LearningPlanRun / LearningUnit / AssessmentAttempt`；
2. GitHub 源码学习 24–30 case 质量收口；
3. G10-D 可执行代理继续冻结。

## 7. 统一验证要求

每个切片必须完成：

- 目标测试；
- 后端全量 pytest；
- RAG K1 baseline；
- Ruff；
- expanded mypy baseline 不扩大；
- package helper；
- detect-secrets；
- 前端全量 Vitest；
- TypeScript 与 Vite production build；
- 存储兼容与失败恢复；
- 实时与刷新真值比较；
- 更新本文件；
- 任一门禁未完成不得合并。

## 8. 当前执行状态

- 当前分支：`agent/answer-claim-owner-v1`；
- 已完成：PR #61、#62、#63、#64；
- 当前任务：P0-2c2a AnswerClaimSnapshot v1 合同与 ChatTurn 生命周期；
- 下一动作：审查 complete / interrupt / retry / continuation 写入点，新增纯领域合同与兼容测试；
- 合并策略：Draft PR -> 完整 CI -> claim 真值与失败安全审查 -> 全绿合并。

## 9. 文档规则

- 当前状态只更新本文件；
- `ARCHITECTURE_STATUS.md` 只维护稳定 owner/边界；
- `STATE_MODEL.md` 只维护稳定数据模型；
- 不新增并列长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT。

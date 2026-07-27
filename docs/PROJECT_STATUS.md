# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-07-27  
> 当前产品定义：**Study Agent 是一个能够长期保持“我正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前产品边界：GitHub = 学习源码时使用的高级研究工具；RAG = 围绕自己的资料学习；Web Research = 需要外部事实时获得可信证据；Memory = 学习连续性基础设施；Workflow = 高级诊断 / 开发者模式。  
> 当前主线：**证据身份、生命周期、ResearchRun 来源真值和实时/恢复一致性已经服务端化；当前收敛普通用户证据展示，把候选、排除、分数和工具调用下沉到显式诊断区。**  
> 当前工作分支：`agent/evidence-display-layering`。

本文件只回答：**做到哪里、真实指标是什么、已知缺陷是什么、下一步做什么。** 历史过程留在 Git 提交和 PR，不维护并列长期状态文档。

## 0. 产品方向与冻结边界

所有新增能力必须先回答：

> **它是否帮助用户更好地继续学习？**

学习主路径固定为：

```text
当前目标 / 当前任务
-> 教学或练习
-> 资料与外部证据
-> 理解验证
-> 已确认内容 / 未解决缺口
-> 明确下一步
-> 结构化整理
-> 下次准确恢复
```

能力层级：

- **RAG**：围绕自己的资料学习，不是向量库管理产品。
- **Web Research**：在需要外部事实时提供可信证据，不是平级搜索引擎。
- **GitHub**：学习源码时使用的高级研究工具，不是第二个代码审查/执行产品。
- **Memory**：用户确认后的学习连续性基础设施，不是独立工作区。
- **Workflow**：高级诊断 / 开发者模式，不进入普通主路径。
- 群聊、新闻、工具保持实验功能。

当前冻结：

- 新向量数据库、GraphRAG、以新 reranker 替代质量评测；
- 原生移动端；
- 群聊/新闻/工具升级为一级产品；
- 新 Workflow 主界面；
- 自动 checkout/test/build、任意 shell、可写 worktree、私有仓库自动执行；
- mastery 百分比和按轮数推断掌握；
- 并列长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT 文档。

## 1. 当前架构与学习主链

当前主架构：**React 19 + FastAPI + application services + SQLite**。

真值边界：

- React 状态只负责交互和可重建缓存；
- SQLite durable entities、committed learning state、评估、索引和运行状态是运行真值；
- Markdown memory 只保存用户确认后的长期学习记忆；
- planned / attempted / failed 不得覆盖 committed truth；
- 多步流程由 application service + durable run 拥有，API route 只做 adapter。

已完成的学习主链：

1. **TaskContract 单一真值**：新 Turn 只判定一次；显式 override 只作用于下一新 Turn；retry / continuation 恢复原合同。
2. **LearningClosureRun**：durable owner、状态机、source hash 幂等、retry/cancel/resume、MemoryRun 关联和刷新恢复。
3. **结构化总结输入**：只使用 committed LearningState、最终 PedagogyEvalRun、证据和有预算的最近对话。
4. **ThreadSummaryState**：`summarized / needs_update / not_summarized`；只有新 completed turn 才重新开放整理。
5. **会话语义导航**：标题、目标/研究摘要、阶段/缺口、状态、搜索和分组。
6. **学习状态去伪精化**：`已验证 / 待验证 / 需重讲 / 待语义复核`；不显示启发式百分比。
7. **结构化恢复卡**：返回用户显示 committed 目标、确认点/采用来源、缺口和下一步；中断 Turn 可继续、重试或 durable abandon。
8. **UI 收敛与窄屏可用**：一级操作只保留当前任务收束、上传、会话和 More；低频功能按需出现。
9. **Golden Journey 门禁**：首次问答、系统学习、资料学习、联网研究、GitHub 源码学习已有决策数、surface、恢复点击、下一步可见性和内部术语合同。

## 2. 已完成的证据与 RAG 质量工作

### 2.1 P0-1：G13 live / restore parity

PR #61 已合并，merge SHA：`597006e99919ea7e5f5b02f01b1536b446da9a55`。

完成：

- 正确读取嵌套 `RagResult.chunk`；
- local evidence identity 优先使用 `chunk_id`；
- 同一来源不同 chunk 不错误折叠；
- 恢复 `pedagogy_snapshot.evidence_ids`；
- live response -> persisted snapshot -> restored session 等价回归；
- 刷新后教学“引”标记保持；
- package helper 更新到当前 React/FastAPI 入口。

CI #1317 全绿。

### 2.2 P0-2a：server-owned EvidenceSnapshot v1

PR #62 已合并，merge SHA：`fcfb9bc66750d10c822306fae735424e658b19ef`。

完成：

- `EvidenceRefV1`、`EvidenceSnapshotV1`、`ClaimEvidenceLinkV1` 合同；
- 稳定证据 ID、生命周期、Provider 状态和采用/排除原因；
- `ChatTurn` 从既有 `rag_snapshot + pedagogy_snapshot` 确定性生成服务端投影；
- 新 Turn 在现有 JSON 边界内持久化，不增加 SQLite schema；
- 旧非空 Turn 读取时补齐 v1 投影，数据库原行不被静默改写；
- local chunk 只有 disclosure 选中同一 `chunk_id` 时才成为 selected；
- WebTool search/read 只成为 candidate/read；模糊 `web-1` 不得冒充 selected URL；
- React 优先消费服务端 snapshot，旧 Turn 才走兼容 normalizer；
- pedagogy evidence IDs 与事实 claim links 分离，不伪造 claim。

CI #1340 全绿。

### 2.3 P0-2b：durable ResearchRun source truth

PR #63 已合并，merge SHA：`f1b2a4f9d481a16e5c93e6ac8fb4c0f9ee2f45c2`。

完成：

- completed/partial ResearchRun 的 selected/rejected source assessments 接入 `ChatTurn.rag_snapshot.research_sources`；
- 保存 run ID、Provider 状态、stop reason、URL/domain、相关度和排除原因；
- snippet、文章正文、query attempts、token、密钥及任意 Provider payload 不进入 Turn 来源快照；
- unusable Run 或不匹配的 source block 被拒绝；
- web policy 阻断时不持久化 ResearchRun 来源明细；
- EvidenceSnapshot v1 自动投影 selected/rejected 生命周期；
- continuation/retry 不能切换到另一个 ResearchRun；
- 同一 Run 恢复时忽略客户端篡改，使用原 Turn 冻结的来源真值；
- `PreparedChatTurn.rag` 返回 repository-owned `rag_snapshot`，实时与数据库恢复一致。

CI #1357 全绿：pytest、RAG K1、Ruff、package、detect-secrets、expanded mypy baseline、前端测试与生产构建。

### 2.4 RAG-K1 当前完成度

K1a–K1e 已进入 `main`：

- 12 份学习文档；
- 30 个 retrieval case，其中 26 个 answerable；
- 10 个 answer-quality gold case；
- clean、paraphrase、multi-source、ambiguous overlap、stale revision、unanswerable；
- corpus/prompt fingerprint、checked-in snapshot、answer evaluator；
- active/superseded/excluded 资格；
- evidence sufficiency/refusal；
- non-regressive adaptive multi-source coverage；
- real-provider replay harness、provenance、latency/usage report 与手动 workflow。

尚未完成：**没有实际成功的 `status=completed` 真实 Provider benchmark 可作为模型质量结论。**

## 3. 当前真实指标

### 3.1 RAG K1 确定性基线

- raw Hybrid source hit：0.961538；
- source precision@K：0.477564；
- source recall@K：0.923077；
- MRR：0.942308；
- nDCG：0.903600；
- stale / forbidden leakage：0；
- adaptive overall recall@K：0.942308；
- adaptive nDCG：0.921567；
- multi-source recall@K：0.9；
- multi-source precision@K：0.733333；
- deterministic answerable supported：26/26；
- deterministic unanswerable block：4/4。

这些指标证明固定 corpus 的回归合同，不代表真实模型在更大真实资料上的最终质量。

### 3.2 GitHub replay 基线

- 15 个仓库；
- 17 个 case；
- 15 个 Provider replay；
- partial rate：0.7647；
- cache hit rate：0.0588；
- 平均 Provider 请求：9.647；
- 平均录制时间：151.4 秒；
- symbol mapping precision / recall / F1：0.625 / 0.4545 / 0.5263；
- CI association precision / recall / F1：0.3529 / 1.0 / 0.5217。

结论：symbol recall 仍低，CI association 过度关联明显，17 case 未达到 24–30 case 目标；G10-D 可执行代理继续冻结。

## 4. 当前缺口

### 4.1 普通证据与开发者诊断尚未分层

当前 `EvidenceTrail` 同时展示：

- 服务端统一证据；
- selected/read/candidate/rejected 全生命周期；
- 搜索调用和读取调用；
- 旧 RAG citations；
- score 和工具错误。

这造成普通用户重复看到同一来源，并暴露内部候选、分数和工具过程。

正确边界：

- 普通层只显示回答实际采用且可核对的 selected 证据，以及明确的教学引用；
- 普通层不显示 candidate/read/rejected、score、搜索次数、读取正文预览和旧 citation 列表；
- 显式“诊断详情”才显示完整生命周期、Provider 状态、采用/排除原因、工具调用和兼容数据；
- 普通复制只复制已采用证据，诊断复制才包含全部状态和分数；
- 无 selected 证据时不得把 candidate/read 包装成“回答来源”。

### 4.2 事实 answer-claim owner 尚未建立

`PedagogyTurnPlan.evidence_ids` 是教学计划引用，不是回答 claim。

因此当前：

- `ClaimEvidenceLinkV1` schema 已有；
- `EvidenceSnapshotV1.claim_links` 保持空；
- 不从自然语言回答反向猜 claim；
- 后续必须先定义服务端结构化 answer assertion/claim owner，再允许写 claim links。

### 4.3 Streamlit 移除未收尾

- 根级 `app.py` 已移除；
- React 19 和 testing-library 已完成；
- `src/ui` 仍存在；
- `requirements.in` 仍保留 Streamlit；
- README 仍有入口状态冲突。

### 4.4 长期学习缺计划级 authoritative entity

现有 TaskContract、LearningState、PedagogyEvalRun、LearningClosureRun、ThreadSummaryState 和 MemoryRun 可保证单次会话可信，但尚无正式实体维护长期目标拆分、前置关系、单元验证、失败后重规划和阶段复测。

## 5. 精确执行顺序

所有切片遵循：**小 PR -> 目标测试 -> 全量门禁 -> 更新本文件 -> 全绿合并 -> 从最新 main 开下一刀。**

### P0-2c1：`agent/evidence-display-layering`（当前）

目标：收敛普通用户证据展示，不改变服务端真值。

范围：

1. 默认摘要只报告实际采用证据数量，不展示搜索次数、读取次数、候选总数或分数；
2. 普通详情只展示 selected 证据，以及被 `pedagogy.evidence_ids` 明确引用的证据；
3. 普通证据行显示类型、标题/链接和“教学引用”标记，不显示 lifecycle 标签与 score；
4. candidate/read/rejected、Provider 状态、采用/排除原因、WebTool 搜索/读取、错误和旧 citations 全部进入显式“诊断详情”；
5. 普通复制只复制普通可见证据；诊断复制包含完整生命周期和技术字段；
6. 删除“统一证据 + 搜索卡 + 阅读卡 + citation list”在普通层的重复展示；
7. 窄屏下标题和链接可换行，按钮可触控，诊断区不产生横向溢出；
8. 旧快照仍可诊断恢复，但不得在普通层把 candidate/read 伪装成 adopted。

门禁：

- selected 与教学引用的普通展示测试；
- candidate/read/rejected 默认隐藏测试；
- 显式诊断展开测试；
- 普通/诊断复制内容边界测试；
- 空 selected 状态不伪造来源；
- live/restore 使用同一 EvidenceSnapshot；
- 全量前后端 CI。

### P0-2c2：answer-claim owner

- 服务端生成结构化 assertion ID；
- 只有最终采用 claim 与已知 EvidenceRef 建立 `ClaimEvidenceLinkV1`；
- 无法解析或无法确认支持关系时保持空，不补造；
- claim links 实时与刷新一致；
- 不从前端或自然语言字符串匹配推断关系。

### P0-3：架构真值与 Streamlit 清理

- 同步 `ARCHITECTURE_STATUS.md`、`STATE_MODEL.md`；
- 删除/迁移 `src/ui`；
- requirements 移除 Streamlit并重新锁定；
- README / USER_GUIDE 同步；
- package diff 和全量回归。

### P1-1：RAG-K1f 真实 Provider 回答基线

实际执行 K1e，固定 corpus/prompt/case fingerprint、Provider/model/temperature/repeat，报告 answerability、unsupported-answer、citation、claim support、groundedness、stale leakage、parse failure、latency、token 和成本。

首轮 record-only，但立即硬门禁：

- stale/forbidden leakage = 0；
- 明确不可回答问题不得生成无依据事实；
- Provider/parse 失败不得补造完成分数。

### P1-2：RAG-K2 结构化摄取

1. `ParserResult -> DocumentBlock`：heading/page/paragraph/table/list identity、parser version、warnings、preview；
2. structure-aware chunking：父子块、最小块合并、章节感知、表格保留、chunker version、manifest。

要求 Markdown / PDF / DOCX 困难 fixture，且 K1 不回退。

### P1-3：学习成效基线

覆盖：初始诊断、误解修正、explain-back、迁移题、直接答案泄漏、证据一致性、刷新/跨会话恢复，以及仅凭“我懂了”不得变成已验证。

### P2-1：自适应 LearningPlan MVP

仅在前述门禁完成后新增：

- `LearningPlanRun`；
- `LearningUnit`；
- `AssessmentAttempt`；
- diagnosing / plan_ready / active / reassessing / replanning / completed；
- LearningState 只投影当前活跃单元；
- 不新增平级课程后台，不显示伪精确百分比。

### P2-2：GitHub 源码学习质量收口

- 扩展到 24–30 immutable case；
- 增加真实 CI 正例和 cold/hot replay；
- 降低 generic matrix false positives；
- 增加阅读顺序、核心文件、explain-back、证据行号与下次恢复旅程。

## 6. 统一验证要求

每个实现切片必须同时完成：

- 目标测试；
- 后端全量 pytest；
- RAG K1 baseline；
- Ruff；
- expanded mypy baseline，不得新增或扩大错误；
- package helper；
- detect-secrets；
- 前端全量 Vitest；
- TypeScript 与 Vite production build；
- 存储变化必须有 migration / compatibility / failure recovery；
- 桌面与窄屏人工或 Playwright Golden Journey；
- 实时与刷新状态/证据比较；
- 更新本文件；
- 任一门禁未完成不得合并。

## 7. 当前执行状态

- 当前分支：`agent/evidence-display-layering`；
- 已完成：PR #61 evidence parity；PR #62 EvidenceSnapshot v1；PR #63 ResearchRun source truth；
- 当前任务：P0-2c1 普通证据与开发者诊断分层；
- 下一动作：重构 `EvidenceTrail` 默认/诊断视图和复制边界，补桌面与窄屏回归；
- 合并策略：Draft PR -> 完整 CI -> 普通/诊断信息边界审查 -> 全绿合并。

## 8. 文档规则

- 当前状态只更新本文件；
- `ARCHITECTURE_STATUS.md` 只维护稳定 owner/边界；
- `STATE_MODEL.md` 只维护稳定数据模型；
- consolidated roadmap 只保存目标/验收，不覆盖当前事实；
- 不新增并列长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT。

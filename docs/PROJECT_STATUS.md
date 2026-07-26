# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-07-26  
> 当前产品定义：**Study Agent 是一个能够长期保持“我正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前产品边界：GitHub = 学习源码时使用的高级研究工具；RAG = 围绕自己的资料学习；Web Research = 需要外部事实时获得可信证据；Memory = 学习连续性基础设施；Workflow = 高级诊断 / 开发者模式。  
> 当前主线：**先修复证据合同与状态真值，再执行真实回答基线和结构化资料摄取；之后才进入学习成效评测与自适应学习计划。**  
> 当前工作分支：`agent/g13-evidence-parity`。

本文件只回答：**做到哪里、当前真实指标是什么、已知缺陷是什么、下一步按什么顺序做。** 详细历史留在 Git 提交和 PR，不在这里重复维护第二套历史流水账。

## 0. 产品方向与硬边界

所有新增能力必须先回答：

> **它是否帮助用户更好地继续学习？**

- **学习主链**：当前目标 / 当前任务 -> 已确认内容 -> 未解决缺口 -> 明确下一步 -> 教学或练习 -> 证据 -> 理解验证 -> 整理 -> 下次恢复。
- **GitHub** 不是第二个产品。仓库快照、代码结构、Git 历史、PR / CI、change impact 与 review context 必须回到源码理解、解释验证和当前学习目标。
- **RAG** 不是知识库管理产品。普通用户首先看到上传资料、围绕资料学习、不可回答时拒答和可核对引用，而不是索引、向量数据库、topK 或 Provider 参数。
- **Web Research** 不是搜索引擎。搜索、来源筛选、阅读、采用/排除和 EvidenceTrail 是学习回答的证据基础设施。
- **Memory** 不是独立工作区。用户关心的是本次确认了什么、还缺什么、下次从哪里继续。
- **Workflow** 只属于高级诊断 / 开发者模式。普通用户只需要知道任务是否进行中、是否失败、能否继续或重试。
- 群聊、新闻、工具保持实验功能，不升级为一级产品。
- 当前阶段禁止以“增加 Provider、向量库、GraphRAG、原生移动端、可执行仓库代理”代替学习质量工作。

## 1. 当前架构与已完成主链

当前主架构是 **React 19 + FastAPI + application services + SQLite**。前端状态只负责展示和恢复缓存；服务端 durable entity、committed learning state、评估、索引和运行状态是 authoritative truth。

### 1.1 核心学习产品

1. **TaskContract 单一真值**：新 Turn 只判定一次任务合同；显式 override 只作用于下一新 Turn；retry / continuation 恢复原持久化合同；前端不二次推断。
2. **G1 LearningClosureRun**：正式 durable owner、状态机、source hash 幂等、retry / cancel / resume、MemoryRun 关联和刷新恢复。
3. **G2 结构化总结输入**：只使用 committed LearningState、最终 PedagogyEvalRun、证据引用和受预算限制的最近对话；失败/中断回合不能成为已掌握事实。
4. **G3 ThreadSummaryState**：`summarized / needs_update / not_summarized`；只有新增 completed turn 才重新开放整理；不自动归档。
5. **G4 会话语义导航**：标题、目标/研究摘要、阶段/缺口、summary status、搜索、分组和手动标题。
6. **G5 学习状态去伪精化**：`已验证 / 待验证 / 需重讲 / 待语义复核`；committed 与 attempted 分离；不显示启发式掌握百分比。
7. **G6 结构化恢复卡**：新用户五类入口；返回用户显示 committed 目标、确认点/采用来源、缺口和下一步；中断 Turn 可继续、重试或 durable abandon。
8. **G7–G8 UI 收敛与窄屏可用**：一级操作只保留当前任务收束、上传、会话和 More；资料、来源、设置与低频功能按需出现；窄屏、触控、焦点恢复和非 hover 环境已覆盖。
9. **PR #52–#54 产品收敛**：设置与工作区解耦；上传资料完成后直接进入系统学习或直接提问；五条 Golden Journey 已对决策数、surface 数、恢复点击、下一步可见性和内部术语建立回归合同。

当前单次学习会话闭环已能走通：

```text
明确目标
-> 教学推进
-> 证据追溯
-> 理解验证
-> 结构化整理
-> 用户确认记忆
-> 标记本次已整理
-> 新内容出现后重新开放整理
-> 下次按语义会话恢复
```

### 1.2 ResearchRun / 联网证据

- 聊天联网工具循环由带 thread / turn owner 的 durable ResearchRun 管理。
- 保存查询尝试、采用/拒绝来源、读取结果、预算、错误和 stop reason。
- 支持 retry / resume / cancel / get / list。
- `status` 表示流程状态；`provider_status` 表示证据完整度。
- 取消为协作式取消；取消后不得提交 completed 或推进 committed learning state。
- 恢复后的联网来源与回答 EvidenceTrail 绑定同一个 Run。

### 1.3 GitHub 源码学习基础设施

已具备：

- commit-pinned repository snapshot；
- Python / JavaScript / TypeScript / Java Tree-sitter 结构图；
- path / symbol / exact phrase / BM25 风格本地搜索；
- callers / callees / hierarchy / implementations / related files；
- ref / commit / compare / diff / blame；
- PR / issue / checks / jobs / 有界脱敏日志；
- cross-fork repository 归属；
- shared Provider request/page budget；
- 双仓库 change-impact；
- source-backed PR review context；
- SQLite persistent cache 和 immutable replay harness。

定位保持为**源码学习高级研究工具**，不进入普通用户平级工作区。

### 1.4 RAG-K1 已完成到哪里

K1a–K1e 已按小 PR 进入 `main`：

- **K1a**：从 6 条干净 fixture 扩展为 12 份学习文档、30 个 retrieval case、10 个 answer-quality gold case；覆盖 clean、paraphrase、multi-source、ambiguous overlap、stale revision 和 unanswerable；建立 corpus fingerprint、answer evaluator 和 checked-in snapshot。
- **K1b**：`active / superseded / excluded` 证据资格在排序前生效；stale / forbidden source leakage 降为 0。
- **K1c**：增加 evidence sufficiency / refusal；当前确定性 30-case corpus 上 answerable supported rate 26/26、unanswerable block rate 4/4、answerability accuracy 1.0。
- **K1d**：复合问题使用非回退 adaptive multi-source coverage；multi-source recall@K 从 0.8 提升到 0.9，precision@K 从 0.7 提升到 0.733333，nDCG 从 0.788590 提升到 0.882017；不得丢失 raw top-K 已召回的唯一来源。
- **K1e**：真实 Provider answer replay harness、provenance、corpus/prompt fingerprint、Provider/model/latency/usage 报告和手动工作流已完成。

**尚未完成的事实**：仓库尚不能把 harness readiness 描述成已经完成一次正式真实 Provider benchmark。只有实际 Provider 调用成功并产生 `status=completed` 的报告后，才能讨论真实模型回答质量。

## 2. 当前高优先级缺陷

### 2.1 G13 证据与消息完整性仍是 partial

最新前端已加入统一 EvidenceRef 展示、状态分组、复制纯文本和教学引用标记，但尚不能标记为 sealed。

已确认缺陷：

1. **本地 RagResult 数据形状不一致**：正式类型把 `title / source_path / chunk_id` 放在 `result.chunk`，但 `normalizeEvidence()` 当前主要读取顶层 `item.title / item.source_path / item.source`；真实本地证据可能在统一证据区丢失并被过滤。
2. **测试隐藏了生产缺陷**：相关前端测试构造了错误的顶层 RagResult，并用 `as never` 绕过类型检查，没有覆盖真实嵌套结构。
3. **刷新恢复丢失 evidence IDs**：实时 `PedagogySummary` 已包含 `evidence_ids`，但 `pedagogySummaryFromSnapshot()` 尚未恢复该字段；同一回答刷新后可能丢失“教学引用”标记。
4. **selected / rejected 缺正式生产者**：当前统一器主要产生 local/web-search=`candidate` 和 web-read=`read`；“已采用 / 已排除”尚未由服务端 authoritative contract 产生。
5. **证据身份未封板**：前端临时生成的 `source || title || url` 未证明与后端 `plan.evidence_ids` 稳定一致；claim-source mapping 仍缺服务端持久化实体。
6. **普通与高级展示边界待收敛**：统一证据区与旧 web call / debug 卡片可能重复；候选、排除、score 和内部状态应下沉高级诊断。

因此当前状态定义为：

> **G13 前端聚合初版完成；live/restore parity、服务端身份、状态 owner 和 claim-source 持久化未完成。**

### 2.2 状态文档曾发生代码/文档漂移

此前本文件同时保留了：

- K1 之前“只有 6 条干净 fixture”的旧结论；
- K1a–K1e 已完成的代码；
- 最新 G10 replay 指标。

本次已按代码状态纠正。以后任何 PR 只有同时更新本文件的“当前事实、指标、缺陷、下一顺序”才算交付完整；不再把历史批次细节长期堆积在本文件。

### 2.3 Streamlit 移除尚未收尾

- `app.py` 已移除；
- React 19 和 testing-library 迁移已完成；
- `src/ui` 仍待清理；
- `requirements.in` 仍保留 Streamlit；
- README 仍同时存在“入口已移除”和“旧入口用于兼容验证”的冲突描述。

该工作必须作为独立清理 PR，不混入 G13 或新学习功能。

### 2.4 长期学习仍缺计划级 authoritative entity

现有 TaskContract、LearningState、PedagogyEvalRun、LearningClosureRun、ThreadSummaryState 和 MemoryRun 可以保证单次会话可信，但还没有一个正式实体回答：

- 一个长期目标应拆成哪些学习单元；
- 前置知识和顺序是什么；
- 每个单元如何验证；
- 测验失败后如何改变计划；
- 阶段复测如何影响下一步。

该能力后置到证据、真实回答和结构化摄取稳定之后，不能提前塞进 `LearningState.payload` 或新建平级课程后台。

## 3. 当前真实指标

### 3.1 RAG K1 确定性基线

- corpus：12 份学习文档；
- retrieval：30 case / 26 answerable；
- answer gold：10 case；
- raw Hybrid source hit：0.961538；
- raw Hybrid source precision@K：0.477564；
- raw Hybrid source recall@K：0.923077；
- raw Hybrid MRR：0.942308；
- raw Hybrid nDCG：0.903600；
- stale / forbidden leakage：0；
- adaptive overall recall@K：0.942308；
- adaptive nDCG：0.921567；
- multi-source recall@K：0.9；
- multi-source precision@K：0.733333；
- deterministic answerable supported：26/26；
- deterministic unanswerable block：4/4。

这些指标证明当前固定 corpus 的合同和回归，不代表真实模型在更大真实资料上的最终质量。

### 3.2 GitHub replay 基线

当前：

- 15 个仓库；
- 17 个 case；
- 15 个 Provider replay；
- partial rate：0.7647；
- cache hit rate：0.0588；
- 平均 Provider 请求：9.647；
- 平均录制时间：151.4 秒；
- symbol mapping precision：0.625；
- symbol mapping recall：0.4545；
- symbol mapping F1：0.5263；
- CI association precision：0.3529；
- CI association recall：1.0；
- CI association F1：0.5217。

结论：symbol mapping 已改善，但 recall 仍低；CI association 存在明显过度关联；17 case 尚未达到 24–30 case 目标；不得进入 G10-D 可执行仓库代理。

## 4. 精确下一代码顺序

所有切片均使用**小 PR、完整回归、更新本文件、全绿后再合并并从最新 main 开下一刀**。

### P0-1：`fix/g13-evidence-parity`（当前切片）

目标：只修证据实时/刷新一致性，不引入新学习功能。

范围：

1. `normalizeEvidence()` 正确读取正式嵌套 `RagResult.chunk`，仅为旧快照保留受控 fallback；
2. local evidence ID 优先使用 `chunk_id`，再使用稳定 source/title fallback；
3. `pedagogySummaryFromSnapshot()` 恢复 `evidence_ids`；
4. 删除相关错误 `as never` fixture，使用真实 `RagResult[]`；
5. 新增 live response -> persisted snapshot -> restored session 的 parity 回归；
6. 记录 G13 仍为 partial，不在本 PR 伪造 selected/rejected 或服务端 claim link。

合并门禁：

- 目标前端测试；
- 全量 Vitest；
- TypeScript build；
- Vite production build；
- 后端全量 pytest、Ruff、mypy baseline、package helper、detect-secrets；
- CI 全绿；
- 合并前检查实时与刷新后的 EvidenceRef 数量、ID、引用标记一致。

### P0-2：`feat/server-owned-evidence-ref-v1`

目标：让证据身份、生命周期和 claim-source 关系成为服务端 authoritative contract。

范围：

- `EvidenceRefV1`：id/type/title/source/url/domain/published_at/score/lifecycle_status/provider_status；
- selection / rejection reason；
- `ClaimEvidenceLink`；
- selected/rejected 正式 owner；
- turn snapshot 持久化和旧快照安全默认；
- 前端只展示服务端合同，不再自行推断状态；
- 普通模式只显示采用证据，候选/排除/score 下沉开发者诊断。

### P0-3：`chore/truth-and-streamlit-cleanup`

目标：完成架构真值和双前端残留清理。

范围：

- 同步 `ARCHITECTURE_STATUS.md` 和 `STATE_MODEL.md` 的 authoritative owners；
- 删除或迁移 `src/ui`；
- `requirements.in` 移除 Streamlit并重新锁定依赖；
- README / USER_GUIDE 删除冲突兼容描述；
- package diff、旧 import 搜索和完整回归。

### P1-1：`eval/rag-k1f-real-provider-baseline`

目标：实际执行 K1e，形成首个真实回答基线，而不是只证明 harness 可用。

至少固定：

- corpus / prompt / case fingerprint；
- Provider profile、model、temperature 和重复运行次数；
- answerability、unsupported-answer rate、citation precision/recall、claim coverage/support、groundedness、stale leakage；
- schema parse failure、latency、token usage 和成本；
- `provider_unavailable / partial_failure / completed` 分离。

第一轮仍以 record-only 为主，但三个安全合同立即硬门禁：

- stale / forbidden evidence leakage = 0；
- 明确不可回答问题不得生成无依据事实；
- 失败或无法解析不得补造完成分数。

### P1-2：RAG-K2 结构化资料摄取

分两个 PR：

1. `feat/rag-k2a-structured-parser`：`ParserResult -> DocumentBlock`，保留 heading/page/paragraph/table/list identity、parser version、warnings 和 preview；
2. `feat/rag-k2b-structure-aware-chunking`：父子块、最小块合并、章节感知、表格保留、chunker version 和 manifest。

K2 必须用 Markdown / PDF / DOCX 困难 fixture 验证，并证明 K1 指标不回退。

### P1-3：`eval/learning-outcome-baseline`

目标：从“回答质量和 UI 流畅度”升级为“学习成效”。

首批固定 case 覆盖：

- 初始诊断；
- 误解修正；
- explain-back；
- 迁移题；
- 直接答案泄漏；
- 证据一致性；
- 刷新/跨会话恢复；
- 仅凭“我懂了”不得变成已验证。

### P2-1：`feat/adaptive-learning-plan-mvp`

仅在前述门禁完成后进入。

拟新增：

- `LearningPlanRun`；
- `LearningUnit`；
- `AssessmentAttempt`；
- `created -> diagnosing -> plan_ready -> active -> reassessing -> replanning -> completed/abandoned`；
- LearningState 只投影当前活跃单元；
- 恢复卡显示当前单元、缺口和下一步；
- 不新增平级课程后台，不显示伪精确百分比。

### P2-2：GitHub 源码学习质量收口

- 扩展到 24–30 immutable case；
- 增加真实 CI 正例与 cold/hot replay；
- 降低 generic matrix job false positives；
- 分语言和场景报告；
- 增加源码学习旅程：阅读顺序、核心文件、explain-back、证据行号、下次恢复。

G10-D0/D1/D2 继续冻结，直到质量基线和执行安全边界同时成立。

## 5. 明确冻结项

当前不得作为主线推进：

- 新向量数据库；
- 以新 reranker 代替质量评测；
- GraphRAG；
- 原生移动端；
- 群聊/新闻/工具升级为一级产品；
- 新 Workflow 主界面；
- 自动 checkout/test/build；
- 任意 shell；
- 可写 worktree；
- 私有仓库自动执行；
- mastery 百分比；
- 根据聊天轮数推断掌握；
- 新建并列长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT 文档。

## 6. 统一验证要求

每个实现切片必须同时完成：

- 目标测试先行；
- 后端全量 pytest；
- Ruff；
- expanded mypy baseline，禁止新增或扩大错误；
- package helper；
- detect-secrets；
- 前端全量 Vitest；
- TypeScript 与 Vite production build；
- 存储变化必须有 migration / compatibility / failure recovery；
- 桌面与窄屏人工或 Playwright Golden Journey；
- 刷新前后状态和证据比较；
- 更新本文件；
- 相关检查未全部完成时不得合并。

## 7. 当前执行状态

- 分支：`agent/g13-evidence-parity`；
- 已完成：按 2026-07-26 代码状态重写本文件，修正 K1、G13、Streamlit 和 G10 的漂移；
- 正在推进：P0-1 G13 evidence parity；
- 下一步：修复嵌套 RagResult、恢复 `evidence_ids`、补生产形状与 live/restore parity 回归；
- 合并策略：Draft PR -> 完整 CI -> 人工 diff/证据一致性检查 -> 全绿后合并；未全绿不合并。

## 8. 文档规则

- 当前状态只更新本文件。
- 稳定架构边界维护在 `ARCHITECTURE_STATUS.md`，但不得维护进度顺序。
- 稳定数据模型维护在 `STATE_MODEL.md`，但不得维护当前状态。
- 详细需求可留在 consolidated roadmap，但不得覆盖本文件的当前事实。
- 不再新增并列的长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT。

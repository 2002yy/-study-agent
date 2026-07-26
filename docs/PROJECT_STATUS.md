# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-07-26  
> 当前产品定义：**Study Agent 是一个能够长期保持“我正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前产品边界：GitHub = 学习源码时使用的高级研究工具；RAG = 围绕自己的资料学习；Web Research = 需要外部事实时获得可信证据；Memory = 学习连续性基础设施；Workflow = 高级诊断 / 开发者模式。  
> 当前主线：**证据实时/刷新一致性已修复；当前封板服务端 EvidenceRef、证据生命周期和 claim-source 关系。之后才执行真实回答基线、结构化摄取、学习成效评测与自适应学习计划。**  
> 当前工作分支：`agent/server-owned-evidence-ref-v1`。

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
- 当前阶段禁止以增加 Provider、向量库、GraphRAG、原生移动端或可执行仓库代理代替学习质量工作。

## 1. 当前架构与已完成主链

当前主架构是 **React 19 + FastAPI + application services + SQLite**。前端状态只负责展示和可重建缓存；服务端 durable entity、committed learning state、评估、索引和运行状态是 authoritative truth。

### 1.1 核心学习产品

1. **TaskContract 单一真值**：新 Turn 只判定一次；显式 override 只作用于下一新 Turn；retry / continuation 恢复原持久化合同；前端不二次推断。
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

已具备 commit-pinned snapshot、四语言 Tree-sitter 结构图、本地代码搜索、调用/继承关系、ref/commit/compare/diff/blame、PR/issue/checks/jobs/脱敏日志、cross-fork 归属、Provider 共享预算、双仓库 change-impact、source-backed review context、SQLite cache 和 immutable replay harness。

定位保持为**源码学习高级研究工具**，不进入普通用户平级工作区。

### 1.4 RAG-K1 已完成到哪里

K1a–K1e 已进入 `main`：

- **K1a**：12 份学习文档、30 个 retrieval case、10 个 answer-quality gold case；覆盖 clean、paraphrase、multi-source、ambiguous overlap、stale revision 和 unanswerable；建立 corpus fingerprint、answer evaluator 和 checked-in snapshot。
- **K1b**：`active / superseded / excluded` 在排序前生效；stale / forbidden source leakage 降为 0。
- **K1c**：evidence sufficiency / refusal；固定 corpus 上 answerable supported 26/26、unanswerable block 4/4、answerability accuracy 1.0。
- **K1d**：非回退 adaptive multi-source coverage；multi-source recall@K 0.8 -> 0.9，precision@K 0.7 -> 0.733333，nDCG 0.788590 -> 0.882017。
- **K1e**：真实 Provider answer replay harness、provenance、corpus/prompt fingerprint、Provider/model/latency/usage 报告和手动工作流完成。

**尚未完成**：还没有一份实际成功、`status=completed` 的正式真实 Provider benchmark 可以作为产品质量结论。

### 1.5 P0-1 G13 evidence parity 已完成

PR #61 已在完整 CI 全绿后 squash 合并，merge SHA `597006e99919ea7e5f5b02f01b1536b446da9a55`。

已完成：

- `normalizeEvidence()` 消费正式嵌套 `RagResult.chunk`；
- local evidence identity 优先使用 `chunk_id`，旧快照才回退 source/title；
- 同一来源的不同 chunk 不再错误折叠；
- 历史 `pedagogy_snapshot.evidence_ids` 恢复；
- 删除错误顶层 fixture 和相关 `as never`；
- 增加 live response -> persisted snapshot -> restored session parity 回归；
- 增加刷新后“引”标记回归；
- 修正 package helper 对已删除根级 `app.py` 的过时要求，并加入当前 React/FastAPI 入口；残余 `src/ui` 门禁保留到独立清理 PR。

CI #1317 已通过：pytest、RAG K1 baseline、Ruff、package helper、detect-secrets、expanded mypy、前端全量测试和生产构建。

## 2. 当前高优先级缺陷

### 2.1 G13 仍是 partial：服务端 EvidenceRef 未封板

P0-1 已解决数据形状和 live/restore parity，但以下问题仍存在：

1. **selected / rejected 缺正式 owner**：当前前端主要推断 local/web-search=`candidate`、web-read=`read`；采用/排除不应由 UI 猜测。
2. **证据身份仍未统一由服务端产生**：local chunk ID、web URL、ResearchRun source identity 尚未投影为一个版本化服务端合同。
3. **claim-source mapping 未持久化**：当前只有教学计划 `evidence_ids`，尚无 claim ID、证据 ID、支持类型和置信度的正式关系。
4. **turn snapshot 未保存统一合同**：历史恢复仍依赖 rag/web/pedagogy 多份原始快照在前端重新组合。
5. **普通与高级展示重复**：采用证据、候选、已阅读、已排除、score、搜索调用和读取详情尚未按用户层级分离。
6. **旧快照兼容尚未定义版本**：需要 schema/version、安全默认和不伪造 selected 的迁移策略。

当前定义：

> **G13 live/restore parity 已完成；服务端身份、生命周期 owner、claim-source 持久化和展示分层未完成。**

### 2.2 Streamlit 移除尚未收尾

- 根级 `app.py` 已移除；
- React 19 和 testing-library 迁移已完成；
- `src/ui` 仍存在；
- `requirements.in` 仍保留 Streamlit；
- README 仍有“入口已移除”和“旧入口兼容验证”的冲突描述。

该工作必须作为 P0-3 独立清理 PR，不混入 EvidenceRef。

### 2.3 长期学习缺计划级 authoritative entity

现有 TaskContract、LearningState、PedagogyEvalRun、LearningClosureRun、ThreadSummaryState 和 MemoryRun 可以保证单次会话可信，但尚无正式实体维护长期目标拆分、前置关系、单元验证、失败后重规划和阶段复测。该能力必须后置到证据、真实回答和结构化摄取稳定之后。

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

这些指标证明固定 corpus 的合同和回归，不代表真实模型在更大真实资料上的最终质量。

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

结论：symbol recall 仍低，CI association 过度关联明显，17 case 未达到 24–30 case 目标；不得进入 G10-D 可执行仓库代理。

## 4. 精确下一代码顺序

所有切片均使用**小 PR、完整回归、更新本文件、全绿后合并，并从最新 main 开下一刀**。

### P0-1：G13 evidence parity

状态：**已完成并合并 PR #61。**

### P0-2：`feat/server-owned-evidence-ref-v1`（当前切片）

目标：让证据身份、生命周期和 claim-source 关系成为服务端 authoritative contract。

实施边界分两层，避免一次 PR 过大：

#### P0-2a：服务端投影与快照合同

- `EvidenceRefV1`：`id / schema_version / type / title / source / url / domain / published_at / score / lifecycle_status / provider_status / selection_reason / rejection_reason`；
- `ClaimEvidenceLink`：`claim_id / evidence_id / support_type / confidence`；
- 从现有 RAG 结果、Web tool trace、ResearchRun 已采用/排除来源投影；
- 只有现有 authoritative 数据能证明时才标记 selected/rejected，不能靠前端启发式回填；
- 写入 turn snapshot，旧行无该字段时安全回退；
- API/前端类型先兼容双读，不立即删除旧 rag/web snapshot。

#### P0-2b：前端切换与展示分层

- 前端优先使用服务端 EvidenceRefV1，不再重建 selected/rejected；
- 普通模式只显示回答采用且可核对的证据；
- 候选、已阅读、排除原因、score、Provider 调用下沉开发者诊断；
- claim-source 对应可按回答 claim 展开；
- 实时与刷新使用同一服务端合同；
- 旧快照继续通过兼容 normalizer 恢复，但不得伪造生命周期状态。

当前 PR 先执行 P0-2a；若 migration、API 和前端兼容使 diff 过大，则在稳定合同后拆出 P0-2b。

### P0-3：`chore/truth-and-streamlit-cleanup`

- 同步 `ARCHITECTURE_STATUS.md` 和 `STATE_MODEL.md` authoritative owners；
- 删除或迁移 `src/ui`；
- `requirements.in` 移除 Streamlit并重新锁定依赖；
- README / USER_GUIDE 删除冲突兼容描述；
- package diff、旧 import 搜索和完整回归。

### P1-1：`eval/rag-k1f-real-provider-baseline`

实际执行 K1e，固定 corpus/prompt/case fingerprint、Provider/model/temperature/repeat，报告 answerability、unsupported-answer、citation、claim support、groundedness、stale leakage、parse failure、latency、token 和成本。

第一轮 record-only，但三个安全合同立即硬门禁：stale/forbidden leakage=0；明确不可回答问题不得生成无依据事实；失败或无法解析不得补造完成分数。

### P1-2：RAG-K2 结构化资料摄取

1. `feat/rag-k2a-structured-parser`：`ParserResult -> DocumentBlock`，保留 heading/page/paragraph/table/list identity、parser version、warnings 和 preview；
2. `feat/rag-k2b-structure-aware-chunking`：父子块、最小块合并、章节感知、表格保留、chunker version 和 manifest。

K2 必须用 Markdown / PDF / DOCX 困难 fixture 验证，并证明 K1 指标不回退。

### P1-3：`eval/learning-outcome-baseline`

覆盖初始诊断、误解修正、explain-back、迁移题、直接答案泄漏、证据一致性、刷新/跨会话恢复，以及仅凭“我懂了”不得变成已验证。

### P2-1：`feat/adaptive-learning-plan-mvp`

仅在前述门禁完成后新增 `LearningPlanRun / LearningUnit / AssessmentAttempt`，并保持 LearningState 只投影当前活跃单元；不新增平级课程后台，不显示伪精确百分比。

### P2-2：GitHub 源码学习质量收口

扩展至 24–30 immutable case，增加真实 CI 正例和 cold/hot replay，降低 generic matrix false positives，并增加阅读顺序、核心文件、explain-back、证据行号和下次恢复旅程。

G10-D0/D1/D2 继续冻结。

## 5. 明确冻结项

当前不得作为主线推进：新向量数据库、以新 reranker 替代质量评测、GraphRAG、原生移动端、群聊/新闻/工具升级一级产品、新 Workflow 主界面、自动 checkout/test/build、任意 shell、可写 worktree、私有仓库自动执行、mastery 百分比、根据聊天轮数推断掌握，以及并列长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT 文档。

## 6. 统一验证要求

每个实现切片必须同时完成：

- 目标测试先行；
- 后端全量 pytest；
- RAG K1 baseline；
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

- 分支：`agent/server-owned-evidence-ref-v1`；
- 已完成：PR #61 G13 evidence parity，完整 CI #1317 全绿后合并；
- 正在推进：P0-2a 服务端 EvidenceRefV1 投影与 turn snapshot 合同；
- 当前动作：定位现有 RAG/Web/ResearchRun 证据 owner、ChatTurn 快照 schema、API 返回和旧行兼容边界；
- 合并策略：Draft PR -> 完整 CI -> migration/兼容/恢复审查 -> 全绿后合并；未全绿不合并。

## 8. 文档规则

- 当前状态只更新本文件。
- 稳定架构边界维护在 `ARCHITECTURE_STATUS.md`，但不得维护进度顺序。
- 稳定数据模型维护在 `STATE_MODEL.md`，但不得维护当前状态。
- 详细需求可留在 consolidated roadmap，但不得覆盖本文件的当前事实。
- 不再新增并列的长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT。

# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-07-27  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**进入功能与使用体验审计，当前先证明真实生产学习验证链不会伪造掌握，并且刷新、继续和重试后真值一致。**  
> 当前分支：`audit/learning-verification-e2e`，P0-A1。

本文件只维护当前事实、真实指标、缺口、执行顺序和门禁。历史细节以 Git 提交和 PR 为准；不得新增并列的长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT 文档。

## 1. 产品与架构边界

```text
当前目标
-> 教学或练习
-> 资料与外部证据
-> 理解验证
-> 已确认内容 / 未解决缺口
-> 明确下一步
-> 整理与恢复
```

- RAG 服务于围绕自己的资料学习。
- Web Research 服务于需要外部事实时获得可信证据。
- GitHub 是源码学习高级研究工具，不是第二个执行产品。
- Memory 是学习连续性基础设施。
- Workflow 只属于高级诊断。
- React 只负责交互和可重建缓存；SQLite durable entities 是运行真值。
- planned / attempted / failed 不得覆盖 committed truth。
- 当前不推进新向量数据库、GraphRAG、原生移动端、可执行仓库代理、掌握百分比或新的并列工作台。
- 下一阶段以“核心学习闭环是否真实可用”为判断标准，而不是以新增功能数量为判断标准。

## 2. 已完成主链

- TaskContract 单一真值；
- LearningClosureRun 与总结闭环；
- ThreadSummaryState；
- 学习状态去伪精化；
- 结构化恢复卡与语义会话导航；
- UI 学习优先层级、窄屏适配和五条 Golden Journey 组件回归；
- RAG K1a–K1e 确定性基线和真实 Provider replay harness；
- EvidenceSnapshot、ResearchRun source truth、EvidenceTrail 普通/诊断分层；
- AnswerClaimSnapshot v1 服务端合同和完整 Turn 生命周期；
- AnswerClaim record-only 离线评测基线。

## 3. 已完成的证据与 claim 真值

### PR #61：G13 live / restore parity

Merge SHA：`597006e99919ea7e5f5b02f01b1536b446da9a55`，CI #1317 全绿。

- local evidence 使用稳定 `chunk_id`；
- live -> persisted -> restored 等价；
- 教学引用刷新后保持。

### PR #62：EvidenceSnapshot v1

Merge SHA：`fcfb9bc66750d10c822306fae735424e658b19ef`，CI #1340 全绿。

- `EvidenceRefV1 / EvidenceSnapshotV1 / ClaimEvidenceLinkV1`；
- 服务端拥有证据身份和生命周期；
- 新旧 Turn 使用现有 JSON 快照兼容持久化；
- pedagogy 引用与事实 claim link 分离。

### PR #63：ResearchRun source truth

Merge SHA：`f1b2a4f9d481a16e5c93e6ac8fb4c0f9ee2f45c2`，CI #1357 全绿。

- selected/rejected ResearchRun 来源进入 ChatTurn；
- 保存 Provider 状态、stop reason、URL/domain、相关度和排除原因；
- continuation/retry 不能切换来源 owner；
- 实时与恢复读取同一 `rag_snapshot`。

### PR #64：adopted evidence / diagnostics 分层

Merge SHA：`451bc4a78fc3eda6219083371591aa46c8e62900`，CI #1368 全绿。

- 普通层只显示 selected 或教学明确引用证据；
- candidate/read/rejected、分数和工具调用进入诊断详情；
- 无 selected 时不把候选包装成回答来源；
- 普通复制和诊断复制分离。

### PR #65：AnswerClaimSnapshot v1

Merge SHA：`b700da1a2751769959ae1b41966f5da0a854162a`，CI #1389 全绿。

- `AnswerClaimV1 / AnswerClaimSnapshotV1`；
- final answer hash、稳定 claim ID、claim kind/status/source、support type、confidence 和 evidence ID 校验；
- validated claim links 回投 EvidenceSnapshot；
- streaming/interrupted/failed/abandoned 使用稳定 `turn_not_completed`；
- completed 且无 producer 时保存 final answer hash + `producer_unavailable`；
- continuation 使旧 claim truth 失效；retry 不继承父 Turn claims；
- partial commit 不能覆盖服务端 route/rag/pedagogy 或注入伪造 claim；
- 未修改 prompt、未增加模型调用、未用自然语言字符串推断 claim、未增加 UI。

### PR #66：AnswerClaim 离线评测基线

Merge SHA：`b1ac5a841aab5948b4fee623aeaea1d87e1b8af9`；合并前 CI #1407 全绿。

- 复用 RAG K1 的 10 个 answer-quality gold case；
- 版本化 `AnswerClaimEvalCase` 和结构化 producer adapter；
- deterministic gold producer 只验证 evaluator 正确性；
- 指标覆盖 schema parse、answerability、claim precision/recall/F1、kind accuracy、claim coverage、unsupported claim、link precision/recall/F1、refusal/forbidden leakage；
- 覆盖 malformed、hallucinated、missing-claim、wrong-link、unknown-evidence、producer failure 等负例；
- case/evaluator/producer/output fingerprints 和 checked-in snapshot；
- 失败、无法解析或 unavailable 不补造完成分数；
- 不调用生产聊天、不修改 prompt、不写 ChatTurn、不调用真实 Provider、不增加 UI；
- 满分结果只能表述为 `evaluator_self_test_only`，不得冒充模型质量。

## 4. 当前真实指标

### RAG K1

- corpus：12 份学习文档；
- retrieval：30 case / 26 answerable；
- answer-quality gold：10 case；
- source recall@K：0.923077；
- nDCG：0.903600；
- adaptive recall@K：0.942308；
- multi-source recall@K：0.9；
- stale / forbidden leakage：0；
- deterministic answerable supported：26/26；
- deterministic unanswerable block：4/4。

这些是固定 corpus 的回归合同，不代表真实模型最终质量。尚未有正式真实 Provider benchmark 可作为模型质量结论。

### GitHub replay

- 15 个仓库；
- 17 个 case；
- 15 个 Provider replay；
- partial rate：0.7647；
- symbol mapping precision / recall / F1：0.625 / 0.4545 / 0.5263；
- CI association precision / recall / F1：0.3529 / 1.0 / 0.5217。

G10-D 可执行代理继续冻结。

## 5. 当前任务：P0-A1 学习验证 E2E

核心问题：

> 用户是否能够从第一次提问开始，经过教学、真实理解验证、失败恢复、成果整理和下次恢复，完成可信且低摩擦的学习闭环，而不需要理解 Run、RAG、Provider、Memory 文件和 Workflow 等内部结构？

已确认生产事实：

- FastAPI `get_chat_service()` 注入 `ExternalDataPolicyChatService`；
- 该服务注入 `TaskAwarePedagogyEngine()`；
- 该服务注入 `TaskAwarePedagogyEvaluationService(LLMSemanticEvaluator())`；
- P0-A1 不预设“缺少 semantic evaluator 接线”，而是验证真实成功、误解、无推理、不可用和恢复链路；
- 只有需要 mastery evidence 的 transfer/complete/deliver 阶段允许 `accept` 推进；
- 其他决策必须阻止 committed learning state 前进。

验证链：

```text
建立目标
-> 教学或练习
-> 学习者解释
-> PedagogyEvalRun
-> committed LearningState
-> 刷新
-> 恢复卡与学习条保持一致
```

本切片范围：

1. 通过真实 FastAPI route、`ExternalDataPolicyChatService`、TaskContract、SQLite repository 和 SessionService 验证；
2. 使用可控 semantic evaluator 和可控模型回复，不调用真实 Provider；
3. 正确且有推理的解释能够进入 `accept` 并提交 confirmed point；
4. “懂了”等无推理表达不能推进；
5. 明显误解不能推进并留下可恢复缺口；
6. semantic evaluator 超时或不可用不能伪造掌握；
7. 非法 evidence ref 不能推进；
8. interrupted continuation 和 failed retry 不得重复或越权提交状态；
9. GET session 模拟刷新后，thread learning state、navigation、latest pedagogy 和 PedagogyEvalRun 保持一致；
10. 不改普通 UI、不引入第二个学习评估 owner、不增加真实 Provider 调用。

门禁：目标 E2E、后端全量 pytest、RAG K1、Ruff、package helper、detect-secrets、expanded mypy、前端 Vitest、TypeScript 与 Vite production build。

## 6. 后续审计与整改顺序

### P0-A2：真实浏览器 Golden Journeys

分支：`test/browser-golden-journeys`。使用 Playwright 或等价 E2E，运行真实 React + 可控 FastAPI，覆盖首次问答、系统学习闭环、上传资料学习、联网研究恢复和 GitHub 源码学习。真实测量必需点击、必需决策、跨 surface 数、恢复点击、失败下一动作，并覆盖 1440px、约 390px、键盘、焦点、刷新和网络失败。

### P0-A3：核心首屏按需加载

分支：`perf/core-bootstrap-lazy-features`。首屏只加载 health、sessions、runtime settings 和当前学习恢复所需数据；Sources、Memory、群聊、新闻、工具、Workflow 按打开时加载；隐藏模块失败不进入全局普通用户告警；保留 last-good cache 和并发刷新防回退。

### P0-A4：资料与来源三层收口

分支：`ux/sources-three-layer-separation`。在现有抽屉内分为“本次回答依据 / 我的资料 / 检索诊断”；普通层不得把 candidate/read/rejected 或检索分数包装成回答依据。

### P0-A5：学习结束 review-first

分支：`ux/closure-review-first`。默认只展示本次确认、剩余缺口、下次入口和确认保存；Memory 文件目标、追加/替换、候选编辑和 provenance 进入高级编辑。

### P0-A6：会话导航单一 owner

分支：`refactor/session-navigation-single-owner`。提取唯一 `SessionNavigator`，宽屏为侧栏、窄屏装入 SlideOver，共用搜索、分组、重命名、归档、错误和切换保护。

### P0-A7：新手与设置渐进披露

分支：`ux/onboarding-settings-progressive-disclosure`。首次打开以输入框为主，只保留“系统学习 / 上传资料”轻量入口；普通设置只保留学习方式、是否使用资料、外部数据与隐私、互动氛围，其余进入高级设置。

### P0-A8：可访问性、反馈与移动端收口

分支：`a11y/focus-feedback-responsive`。覆盖 SlideOver 焦点循环、Escape、焦点恢复、focus-visible、复制失败反馈、上传格式/大小/accept、关键内容换行、触控目标、软键盘和横向溢出。

## 7. 审计阶段完成标准

只有同时满足以下条件，才允许恢复后续扩展：

- 正确解释能通过真实生产链进入 committed learning truth；
- 无推理表达、明显误解和不可用 evaluator 不会伪造掌握；
- 五条 Golden Journey 在桌面与窄屏浏览器 E2E 全部通过；
- first-answer 没有强制配置决策；
- 系统学习恢复、资料学习、联网研究恢复均不超过两层产品 surface；
- 刷新、网络失败、stream interruption 后都有一键或明确恢复路径；
- 首屏不依赖隐藏实验模块；
- 普通证据层只显示 adopted evidence；
- 默认学习结束流程不要求理解 Memory 文件结构；
- 桌面与移动端使用同一个会话导航 owner；
- 键盘、焦点、复制、上传和窄屏关键问题有自动回归；
- 全量 CI 通过。

## 8. 审计期间冻结

1. 真实 Provider claim replay；
2. claim producer 接入生产 ChatService；
3. UI 展示“已支持 claim”；
4. Streamlit / 架构清理；
5. RAG-K1f 正式真实 Provider 回答基线；
6. RAG-K2 结构化 parser / chunking；
7. 自适应 `LearningPlanRun / LearningUnit / AssessmentAttempt`；
8. G10-D 可执行代理。

审计完成后根据真实结果重新排序，不自动沿用旧计划。

## 9. 统一验证要求

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
- 兼容和失败恢复；
- P0-A2 之后相关 UI 切片必须运行浏览器 E2E；
- 更新本文件；
- 任一门禁未完成不得合并。

## 10. 当前执行状态

- 当前分支：`audit/learning-verification-e2e`；
- 基线：PR #66 merge SHA `b1ac5a841aab5948b4fee623aeaea1d87e1b8af9`；
- 当前任务：建立真实生产路径的 P0-A1 学习验证 E2E；
- 当前阶段：测试设计与最小必要真值修复；
- 下一动作：增加成功、无推理、误解、semantic failure、evidence failure、continuation/retry 和刷新恢复测试；
- 合并策略：独立小分支 -> Draft PR -> 完整门禁 -> 全绿后合并。

## 11. 文档规则

- 当前状态只更新本文件；
- status-only 更新留在当前 active branch，不直接推 `main`；
- `ARCHITECTURE_STATUS.md` 只维护稳定 owner/边界；
- `STATE_MODEL.md` 只维护稳定数据模型；
- 不新增并列长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT；
- 代码状态、CI 状态、分支和 PR 顺序变化时必须同步更新本文件。

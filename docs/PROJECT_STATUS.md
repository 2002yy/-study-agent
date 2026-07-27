# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-07-27  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**完成 AnswerClaim 离线评测基线后，立即进入功能与使用体验审计；审计完成前不增加横向功能，也不接入生产 claim producer。**  
> 当前分支：`agent/answer-claim-eval-baseline`，Draft PR #66。

本文件只维护当前事实、真实指标、缺口、执行顺序和门禁。历史细节以 Git 提交和 PR 为准；不得新增并列的长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT 文档。

## 1. 产品与架构边界

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

已完成：

- TaskContract 单一真值；
- LearningClosureRun 与总结闭环；
- ThreadSummaryState；
- 学习状态去伪精化；
- 结构化恢复卡与语义会话导航；
- UI 学习优先层级、窄屏适配和五条 Golden Journey 组件回归；
- RAG K1a–K1e 确定性基线和真实 Provider replay harness；
- EvidenceSnapshot、ResearchRun source truth、EvidenceTrail 普通/诊断分层；
- AnswerClaimSnapshot v1 服务端合同和完整 Turn 生命周期。

## 3. 已完成的证据与 claim 真值

### PR #61：G13 live / restore parity

Merge SHA：`597006e99919ea7e5f5b02f01b1536b446da9a55`，CI #1317 全绿。

- 正确读取 `RagResult.chunk`；
- local evidence 使用 `chunk_id`；
- live -> persisted -> restored 等价；
- 教学引用刷新后保持。

### PR #62：EvidenceSnapshot v1

Merge SHA：`fcfb9bc66750d10c822306fae735424e658b19ef`，CI #1340 全绿。

- `EvidenceRefV1 / EvidenceSnapshotV1 / ClaimEvidenceLinkV1`；
- 服务端拥有证据身份和生命周期；
- 新旧 Turn 使用现有 JSON 快照兼容持久化；
- React 优先读取服务端真值；
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
- 普通复制和诊断复制分离；
- 窄屏、链接换行和触控边界已处理。

### PR #65：AnswerClaimSnapshot v1

Merge SHA：`b700da1a2751769959ae1b41966f5da0a854162a`，CI #1389 全绿。

- `AnswerClaimV1 / AnswerClaimSnapshotV1`；
- final answer hash 和稳定 claim ID；
- claim kind/status/source、support type、confidence 和 evidence ID 校验；
- supplied/validated snapshot 只有 answer hash 匹配时才接受；
- validated claim links 回投 EvidenceSnapshot；
- streaming/interrupted/failed/abandoned 使用稳定 `turn_not_completed`；
- completed 且无 producer 时保存 final answer hash + `producer_unavailable`；
- continuation 在新 final answer 前使旧 claim truth 失效；
- retry 不继承父 Turn claims；
- partial commit 只能更新文本，不能覆盖服务端 route/rag/pedagogy 或注入伪造 claim；
- 旧 Turn 在内存中兼容投影，不静默改写数据库；
- 未修改 prompt、未增加模型调用、未用自然语言字符串推断 claim、未增加 UI。

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

这些是固定 corpus 的回归合同，不代表真实模型最终质量。尚未有实际成功的正式真实 Provider benchmark。

### GitHub replay

- 15 个仓库；
- 17 个 case；
- 15 个 Provider replay；
- partial rate：0.7647；
- symbol mapping precision / recall / F1：0.625 / 0.4545 / 0.5263；
- CI association precision / recall / F1：0.3529 / 1.0 / 0.5217。

G10-D 可执行代理继续冻结。

## 5. 当前任务：PR #66 AnswerClaim 离线评测基线

目标：复用现有 RAG K1 的 10 个 answer-quality gold case，建立**不调用生产聊天、不修改 prompt、不写 ChatTurn**的 record-only harness。

已实现：

- 版本化 `AnswerClaimEvalCase`；
- 结构化 producer adapter；
- deterministic gold producer，仅验证 evaluator 正确性；
- schema parse、answerability、claim precision/recall/F1、kind accuracy、claim coverage、unsupported claim、link precision/recall/F1、refusal/forbidden leakage 指标；
- malformed、hallucinated、missing-claim、wrong-link、unknown-evidence、producer failure 等负例；
- case/evaluator/producer/output fingerprints；
- checked-in record-only snapshot；
- CLI runner；
- 失败、无法解析或 unavailable 不补造完成分数。

当前验证状态：

- Draft PR #66；
- CI #1399：pytest、RAG K1、Ruff、package helper 已通过；
- detect-secrets 因 snapshot 中的 SHA-256 字段名被误判而失败，报告确认没有真实凭证；
- 已将 runner 字段名改为明确的 `*_fingerprint_sha256`；
- 仍需同步 checked-in snapshot 并重跑完整 CI；
- mypy 与前端门禁在 CI #1399 中因 secrets gate 顺序被跳过；
- 任一门禁未完成前不得合并。

本 PR 的满分 deterministic 结果只能表述为 `evaluator_self_test_only`，不得冒充模型质量。

## 6. 下一阶段：功能与使用体验审计

### 阶段目标

在 PR #66 全绿并合并后，暂停真实 Provider claim replay、Streamlit 清理、自适应学习计划和其他横向扩展，先回答一个核心问题：

> 用户是否能够从第一次提问开始，经过教学、真实理解验证、失败恢复、成果整理和下次恢复，完成可信且低摩擦的学习闭环，而不需要理解 Run、RAG、Provider、Memory 文件和 Workflow 等内部结构？

审计结果、进度和整改顺序只写入本文件，不创建新的长期审计文档。

### 已识别的高风险点

1. **理解验证生产接线风险**
   - 需要证明正确解释能进入 committed truth；
   - “懂了”等无推理表达不能推进；
   - 明显误解能生成 misconception / unresolved gap；
   - semantic evaluator 不可用时不能伪造掌握；
   - 刷新和恢复后评估状态保持一致。
2. **Golden Journey 仍以组件存在性为主**
   - 当前部分 decision/surface 指标是测试常量，不是真实浏览器点击测量；
   - 尚未系统覆盖真实网络失败、刷新、键盘、390px 窄屏和焦点行为。
3. **首屏仍加载隐藏实验模块**
   - tools、workflows、wechat 等不应成为普通首屏依赖；
   - 隐藏模块失败不应产生全局普通用户告警。
4. **资料与来源混合三种任务**
   - adopted answer evidence；
   - 检索候选与评分诊断；
   - 长期资料管理。
5. **学习结束流程过度工程化**
   - 默认“整理成果”不应直接进入多目标记忆文件编辑工作台。
6. **会话导航存在双实现**
   - 桌面 SessionSidebar 与抽屉 SessionsPanel 重复搜索、分组、重命名、切换和归档逻辑。
7. **首次打开与设置仍有认知负担**
   - 新手卡五个等权入口；
   - 普通设置仍暴露角色固定、模型档位、上下文深度、完整提示词和检索算法。
8. **可访问性、反馈和移动端仍需真实验证**
   - SlideOver 缺焦点循环；
   - 复制失败被静默吞掉；
   - 上传缺少格式/大小提示和 accept 限制；
   - 关键缺口/下一步在窄屏可能被单行省略。

## 7. 审计与整改精确顺序

### P0-A1：学习验证 E2E

建议分支：`audit/learning-verification-e2e`。

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

必须覆盖：

- 正确且有推理的解释；
- 明显误解；
- 只说“懂了”；
- semantic evaluator 不可用或超时；
- evidence ref 不合法；
- continuation / retry / interrupted；
- 刷新恢复一致性。

若生产默认配置不能产生可信 `accept`，先修接线，不推进后续体验重构。

### P0-A2：真实浏览器 Golden Journeys

建议分支：`test/browser-golden-journeys`。

使用 Playwright 或等价浏览器 E2E，运行真实 React + 可控 FastAPI：

1. 首次打开 -> 提问 -> 获得回答；
2. 系统学习 -> 理解验证 -> 整理 -> 下次恢复；
3. 上传资料 -> 完成处理 -> 围绕资料提问 -> 核对采用证据；
4. 联网研究 -> 查看进度 -> 停止 -> 恢复 -> 继续对话；
5. GitHub 源码学习 -> 阅读源码 -> 回到学习目标。

必须真实测量：

- 必需点击数；
- 必需决策数；
- 跨越产品 surface 数；
- 恢复点击数；
- 失败后是否有明确下一动作；
- 1440px 桌面、约 390px 窄屏；
- 键盘与焦点；
- 刷新和网络失败。

现有组件 Golden Journey 测试保留为快速回归，但不得继续把常量当作真实体验指标。

### P0-A3：核心首屏按需加载

建议分支：`perf/core-bootstrap-lazy-features`。

- 首屏只加载 health、sessions、runtime settings 和当前学习恢复所需数据；
- Sources、Memory、群聊、新闻、工具、Workflow 按抽屉打开时加载；
- 隐藏实验模块失败不进入全局普通用户告警；
- 当前用户动作失败必须在局部给出原因和可执行恢复动作；
- 保留 last-good cache 和并发刷新防回退。

### P0-A4：资料与来源三层收口

建议分支：`ux/sources-three-layer-separation`。

不增加顶级页面，在现有抽屉内分为：

1. **本次回答依据**：只显示 adopted evidence；
2. **我的资料**：资料状态、旧版本、排除、恢复、删除；
3. **检索诊断**：候选、排名、分数、命中词、原始上下文。

普通层不得把 candidate/read/rejected 或检索分数包装成回答依据。

### P0-A5：学习结束 review-first

建议分支：`ux/closure-review-first`。

默认结束流程只展示：

1. 本次确认了什么；
2. 还有什么不会；
3. 下次从哪里继续；
4. 确认保存，并选择“继续当前”或“归档并新建”。

Memory 文件目标、追加/替换、候选编辑和 provenance 进入二次“高级编辑”。

### P0-A6：会话导航单一 owner

建议分支：`refactor/session-navigation-single-owner`。

- 提取唯一 `SessionNavigator`；
- 宽屏作为固定侧栏；
- 窄屏装入 SlideOver；
- 共用搜索、分组、重命名、归档、错误和生成中切换保护；
- 删除 SessionSidebar / SessionsPanel 的重复业务逻辑。

### P0-A7：新手与设置渐进披露

建议分支：`ux/onboarding-settings-progressive-disclosure`。

- 首次打开以输入框为主；
- 只保留“系统学习”“上传资料”两个轻量快捷入口；
- 联网研究和项目推进优先由输入自动识别，必要时放入更多选项；
- 普通设置只保留学习方式、是否使用我的资料、外部数据与隐私、互动氛围；
- 角色固定、完整提示词、模型档位、上下文深度和检索算法进入高级设置；
- 不增加新的永久模式栏或平行工作台。

### P0-A8：可访问性、反馈与移动端收口

建议分支：`a11y/focus-feedback-responsive`。

- SlideOver 焦点循环；
- Escape、关闭后焦点恢复、Tab 顺序；
- 清晰 focus-visible；
- 复制失败可见反馈；
- 上传格式、大小和支持类型说明；
- input `accept` 与服务端校验一致；
- 关键目标、缺口和下一步允许换行，不以单行省略隐藏；
- 触控目标、软键盘、无横向溢出和小屏抽屉验证。

## 8. 审计阶段完成标准

只有同时满足以下条件，才允许恢复真实 Provider claim replay、P0-3 清理或 P2 自适应计划：

- 正确解释能通过真实生产接线进入 committed learning truth；
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

## 9. 审计之后的冻结顺序

审计阶段完成前，以下任务保持冻结：

1. P0-2c2b2 真实 Provider claim replay；
2. claim producer 接入生产 ChatService；
3. UI 展示“已支持 claim”；
4. P0-3 Streamlit / 架构清理；
5. RAG-K1f 正式真实 Provider 回答基线；
6. RAG-K2 结构化 parser / chunking；
7. 自适应 `LearningPlanRun / LearningUnit / AssessmentAttempt`；
8. G10-D 可执行代理。

审计完成后重新根据真实结果排序，而不是自动沿用旧计划。

## 10. 统一验证要求

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
- 浏览器 E2E（进入 P0-A2 后对相关 UI 切片强制执行）；
- 更新本文件；
- 任一门禁未完成不得合并。

## 11. 当前执行状态

- 当前分支：`agent/answer-claim-eval-baseline`；
- 当前 Draft PR：#66；
- 已完成并合并：PR #61–#65；
- 当前任务：同步 fingerprint snapshot，修复 detect-secrets 命名误判并重跑完整 CI；
- PR #66 全绿后：合并到 `main`，从最新 `main` 建立 `audit/learning-verification-e2e`；
- 下一主阶段：P0-A1 -> P0-A2 -> 根据审计结果执行 P0-A3–P0-A8；
- 合并策略：独立小分支 -> Draft PR -> 完整门禁 -> 全绿后合并；
- 任一检查未完成或失败，不得合并。

## 12. 文档规则

- 当前状态只更新本文件；
- status-only 更新留在当前 active branch，不直接推 `main`；
- `ARCHITECTURE_STATUS.md` 只维护稳定 owner/边界；
- `STATE_MODEL.md` 只维护稳定数据模型；
- 不新增并列长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT；
- 代码状态、CI 状态、分支和 PR 顺序变化时必须同步更新本文件。
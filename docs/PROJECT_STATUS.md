# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-07-27  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**P0-A1 学习真值闭环已通过；P0-A2 首批真实浏览器基线已全绿，当前准备合并后继续补齐资料学习、联网研究恢复和 GitHub 源码学习。**  
> 当前分支：`test/browser-golden-journeys`，Draft PR #68。

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
- 当前以“核心学习闭环是否真实可用”为判断标准，不以新增功能数量为判断标准。

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
- AnswerClaim record-only 离线评测基线；
- 生产路径学习验证 E2E。

## 3. 已完成 PR 与真值合同

- PR #61：G13 live / restore parity，merge `597006e99919ea7e5f5b02f01b1536b446da9a55`，CI #1317 全绿；
- PR #62：EvidenceSnapshot v1，merge `fcfb9bc66750d10c822306fae735424e658b19ef`，CI #1340 全绿；
- PR #63：ResearchRun source truth，merge `f1b2a4f9d481a16e5c93e6ac8fb4c0f9ee2f45c2`，CI #1357 全绿；
- PR #64：adopted evidence / diagnostics 分层，merge `451bc4a78fc3eda6219083371591aa46c8e62900`，CI #1368 全绿；
- PR #65：AnswerClaimSnapshot v1，merge `b700da1a2751769959ae1b41966f5da0a854162a`，CI #1389 全绿；
- PR #66：AnswerClaim 离线评测基线，merge `b1ac5a841aab5948b4fee623aeaea1d87e1b8af9`，CI #1407 全绿；
- PR #67：生产学习验证生命周期审计，merge `c19d5070b9bcf73ed46a81731bbeae842b757208`，CI #1416 全绿。

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

## 5. P0-A1 已完成：学习验证 E2E

生产 owner 链：

```text
FastAPI
-> ExternalDataPolicyChatService
-> TaskContract
-> TaskAwarePedagogyEvaluationService(LLMSemanticEvaluator)
-> TaskAwarePedagogyEngine
-> SQLite ChatThread / ChatTurn / PedagogyEvalRun
-> SessionService 恢复投影
```

已验证：

- 正确且有推理的解释进入 `accept`、transfer 和 confirmed point；
- GET session 后 learning state、navigation 和 latest pedagogy 一致；
- “懂了”被 `understanding_asserted_without_reasoning` 拒绝；
- 二分查找 `O(n)` 误解被 deterministic gate 拒绝并留下 gap；
- semantic timeout 返回 `needs_semantic_review`，transfer 被阻止；
- invented evidence ref 被拒绝；
- interrupted Turn 不提交，continuation 复用同一 Turn 后只提交一次；
- failed retry 创建 child，parent 转为 `superseded`，只提交一次；
- 审计只增加测试，没有修改生产代码或放宽学习门禁。

## 6. P0-A2：真实浏览器 Golden Journeys

### P0-A2a 已实现：核心浏览器基线

PR #68 建立：

- Playwright Chromium browser harness；
- 真实 React 页面；
- 可控网络级 API/SSE fixture，不调用真实模型、联网搜索或用户文件；
- desktop `1440×900` 与 mobile `390×844`；
- JSON 动作指标；
- 失败时 trace、screenshot、video 与 HTML report；
- CI 中固定 `@playwright/test@1.55.0`，浏览器套件与 Vitest 分离；
- 保留原有 Vitest 组件 Golden Journeys 作为快速回归。

真实浏览器覆盖：

1. 首次打开 -> 键盘到达输入框 -> 提问 -> 获得回答 -> 刷新恢复；
2. 已有学习会话 -> 恢复卡 -> 继续这里 -> 回答 -> 刷新恢复；
3. chat SSE 返回 503 -> 显示可执行错误 -> 一键重新生成 -> 刷新恢复。

### 实测指标

桌面与 390px 结果一致：

| journey | required clicks | required decisions | product surfaces | recovery clicks | keyboard-only | refresh restore | horizontal overflow |
|---|---:|---:|---:|---:|---|---|---|
| first answer | 0 | 0 | 1 | 0 | pass | pass | none |
| returning learning | 1 | 1 | 1 | 1 | not required | pass | none |
| chat failure recovery | 1 | 0 | 1 | 1 | not required | pass | none |

这些数字来自浏览器动作和可验证 DOM，不是手写 Golden Journey 常量。

### CI 与修正记录

- CI #1425：Vitest 扫描 `e2e`，因普通前端步骤尚未安装 Playwright 而失败；修复为 `vitest run src`，明确分离 suite；
- CI #1427：浏览器首次真正执行，6/6 在最终断言处失败；真实主路径均已完成，失败原因是 fixture 未覆盖 `/knowledge-base/documents`、返回卡定位未限定区域；
- 同步补齐知识库与头像 fixture，拆分 API fixture、指标和 spec；
- 实现 head `624b4e3a65e84823199d7422ad7d9478136a5404`，CI #1435：6 个浏览器用例和全部原有门禁全绿；
- 本状态提交后必须对最新 head 再跑完整 CI，未通过前 PR #68 保持 Draft。

### P0-A2 尚未完成

仍缺三条真实浏览器旅程：

1. 上传资料 -> 处理完成 -> 围绕资料提问 -> 核对 adopted evidence；
2. 联网研究 -> 查看进度 -> 停止/失败 -> 恢复 -> 继续对话；
3. GitHub 源码学习 -> 查看源码依据 -> 回到学习目标。

PR #68 只负责可复用基础设施和核心三条旅程。合并后从最新 `main` 建立独立分支 `test/browser-golden-journeys-evidence` 补齐剩余三条，不在本 PR 顺手重构 Sources、SessionNavigator、首屏加载或设置。

## 7. 后续审计顺序

### P0-A3：核心首屏按需加载

分支：`perf/core-bootstrap-lazy-features`。首屏只加载 health、sessions、runtime settings 和当前恢复所需数据；其余模块按打开时加载；隐藏模块失败不进入普通全局告警。

### P0-A4：资料与来源三层收口

分支：`ux/sources-three-layer-separation`。现有抽屉分为“本次回答依据 / 我的资料 / 检索诊断”；普通层只显示 adopted evidence。

### P0-A5：学习结束 review-first

分支：`ux/closure-review-first`。默认只展示本次确认、剩余缺口、下次入口和确认保存；Memory 工程细节进入高级编辑。

### P0-A6：会话导航单一 owner

分支：`refactor/session-navigation-single-owner`。提取唯一 `SessionNavigator`，宽屏为侧栏，窄屏装入 SlideOver。

### P0-A7：新手与设置渐进披露

分支：`ux/onboarding-settings-progressive-disclosure`。首次打开以输入框为主；普通设置只保留学习方式、资料、外部数据与隐私、互动氛围。

### P0-A8：可访问性、反馈与移动端收口

分支：`a11y/focus-feedback-responsive`。覆盖焦点循环、Escape、焦点恢复、复制失败反馈、上传约束、关键内容换行、触控目标、软键盘和横向溢出。

## 8. 审计阶段完成标准

- 正确解释能进入 committed learning truth；
- 无推理、误解和不可用 evaluator 不会伪造掌握；
- 五类 Golden Journey 在桌面与窄屏浏览器 E2E 全部通过；
- first-answer 没有强制配置决策；
- 系统学习恢复、资料学习、联网研究恢复均不超过两层 product surface；
- 刷新、网络失败、stream interruption 后有明确恢复路径；
- 首屏不依赖隐藏实验模块；
- 普通证据层只显示 adopted evidence；
- 默认结束流程不要求理解 Memory 文件结构；
- 桌面与移动端使用同一个会话导航 owner；
- 键盘、焦点、复制、上传和窄屏问题有自动回归；
- 全量 CI 通过。

## 9. 审计期间冻结

1. 真实 Provider claim replay；
2. claim producer 接入生产 ChatService；
3. UI 展示“已支持 claim”；
4. Streamlit / 架构清理；
5. RAG-K1f 正式真实 Provider 回答基线；
6. RAG-K2 结构化 parser / chunking；
7. 自适应 `LearningPlanRun / LearningUnit / AssessmentAttempt`；
8. G10-D 可执行代理。

审计完成后根据真实结果重新排序，不自动沿用旧计划。

## 10. 当前执行状态

- 当前分支：`test/browser-golden-journeys`；
- 当前 Draft PR：#68；
- 基线：PR #67 merge SHA `c19d5070b9bcf73ed46a81731bbeae842b757208`；
- P0-A2a 实现 head：`624b4e3a65e84823199d7422ad7d9478136a5404`；
- CI #1435：完整门禁全绿；
- 当前动作：状态同步后对最终 head 重跑完整 CI；
- 通过后：PR #68 ready -> squash merge -> 建立 `test/browser-golden-journeys-evidence`；
- 合并策略：独立小分支 -> Draft PR -> 完整门禁 -> 全绿后合并。

## 11. 文档规则

- 当前状态只更新本文件；
- status-only 更新留在当前 active branch，不直接推 `main`；
- `ARCHITECTURE_STATUS.md` 只维护稳定 owner/边界；
- `STATE_MODEL.md` 只维护稳定数据模型；
- 不新增并列长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT；
- 代码状态、CI 状态、分支和 PR 顺序变化时必须同步更新本文件。

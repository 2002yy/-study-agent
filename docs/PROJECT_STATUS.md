# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-07-27  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**学习真值、真实浏览器旅程和核心首屏按需加载已通过；当前进入 P0-A4，将资料抽屉收口为回答依据、资料管理和检索诊断三层。**  
> 当前分支：`ux/sources-three-layer-separation`，P0-A4。

本文件只维护当前事实、指标、缺口、顺序和门禁。不得新增并列长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT 文档。

## 1. 产品边界

```text
当前目标 -> 教学/练习 -> 资料与证据 -> 理解验证
-> 已确认/未解决 -> 下一步 -> 整理与恢复
```

- RAG 服务于围绕自己的资料学习；Web Research 服务于需要外部事实的任务。
- GitHub 是源码学习的证据来源，不是第二个执行产品或顶级工作台。
- Memory 是连续性基础设施；Workflow 只属于高级诊断。
- React 是交互和可重建缓存；SQLite durable entities 是运行真值。
- planned / attempted / failed 不得覆盖 committed truth。
- 当前冻结横向扩展，以核心学习闭环是否真实可用为判断标准。

## 2. 已完成

- TaskContract、LearningClosureRun、ThreadSummaryState、结构化恢复卡；
- RAG K1a-K1e、EvidenceSnapshot、ResearchRun source truth；
- EvidenceTrail 普通/诊断分层；
- AnswerClaimSnapshot v1 与 record-only 离线评测；
- 生产路径学习验证 E2E；
- Chromium desktop / 390px 五类 Golden Journey 浏览器基线；
- 核心首屏按需加载与隐藏功能错误隔离。

已合并：

- PR #61 `597006e99919ea7e5f5b02f01b1536b446da9a55`，CI #1317；
- PR #62 `fcfb9bc66750d10c822306fae735424e658b19ef`，CI #1340；
- PR #63 `f1b2a4f9d481a16e5c93e6ac8fb4c0f9ee2f45c2`，CI #1357；
- PR #64 `451bc4a78fc3eda6219083371591aa46c8e62900`，CI #1368；
- PR #65 `b700da1a2751769959ae1b41966f5da0a854162a`，CI #1389；
- PR #66 `b1ac5a841aab5948b4fee623aeaea1d87e1b8af9`，CI #1407；
- PR #67 `c19d5070b9bcf73ed46a81731bbeae842b757208`，CI #1416；
- PR #68 `4da85690043e9144b18dabaf0b4d2359c16eaeb8`，CI #1437；
- PR #69 `04ac7d59c2f7ed76eee7192c3500ebbb6bc6d286`，CI #1449；
- PR #70 `ccdea493d8d0119e9ba0b9c203a06b5f14de1229`，CI #1462。

## 3. 当前真实指标

### RAG K1

- 12 documents；30 retrieval cases / 26 answerable；10 answer-quality gold；
- source recall@K 0.923077；nDCG 0.903600；adaptive recall@K 0.942308；
- multi-source recall@K 0.9；stale / forbidden leakage 0；
- deterministic answerable 26/26；unanswerable block 4/4。

这些是固定 corpus 回归合同，不代表真实模型最终质量。

### GitHub replay

- 15 repos；17 cases；15 Provider replay；partial rate 0.7647；
- symbol mapping P/R/F1 0.625 / 0.4545 / 0.5263；
- CI association P/R/F1 0.3529 / 1.0 / 0.5217。

G10-D 可执行代理继续冻结。

## 4. P0-A1 已完成：学习验证

真实 FastAPI -> policy ChatService -> TaskContract -> semantic/deterministic pedagogy -> SQLite -> SessionService 链已经验证：

- 正确且有推理的解释进入 committed truth；
- “懂了”、已知误解、semantic timeout、非法 evidence ref 不推进；
- interrupted continuation 与 failed retry 只提交一次；
- 刷新恢复与 SQLite 真值一致。

## 5. P0-A2 已完成：真实浏览器 Golden Journeys

PR #68 和 PR #69 使用真实 React + Chromium + 网络级 API/SSE fixture，运行 `1440×900` 与 `390×844`。

| journey | clicks | decisions | surfaces | recovery | keyboard | refresh | overflow |
|---|---:|---:|---:|---:|---|---|---|
| first answer | 0 | 0 | 1 | 0 | pass | pass | none |
| returning learning | 1 | 1 | 1 | 1 | n/a | pass | none |
| chat 503 recovery | 1 | 0 | 1 | 1 | n/a | pass | none |
| material learning + adopted evidence | 3 | 1 | 1 | 0 | n/a | pass | none |
| web research recovery + adopted evidence | 2 | 0 | 1 | 1 | n/a | pass | none |
| source-code learning + adopted evidence | 2 | 0 | 1 | 0 | n/a | pass | none |

普通 EvidenceTrail 只显示 server-owned selected/adopted evidence；所有旅程刷新恢复，390px 无横向溢出。

## 6. P0-A3 已完成：核心首屏按需加载

- 干净首屏从 9 个业务请求收窄为 `/health`、`/sessions`、`/runtime/settings`；
- `/rag/status`、`/knowledge-base/documents`、`/tools`、`/workflows/runs`、`/memory`、`/wechat` 未打开时均为零请求；
- Sources、群聊、工具、开发者诊断、学习成果打开后只加载对应功能数据；
- 隐藏接口全部模拟 503 时，desktop 和 390px 普通首屏不显示全局错误；
- core refresh 不清空已加载 feature data，持久化 active run/session 恢复语义保留；
- PR #70 最终 head CI #1462 全绿。

## 7. 当前任务：P0-A4 资料与来源三层收口

### 已确认问题

现有 SourcesPanel 在同一纵向页面混合：

1. 回答实际采用的证据；
2. 检索候选、排序、分数、命中词和模型上下文；
3. 长期资料状态、删除和全量重建操作。

普通用户会把“检索到”误解为“回答采用”，文档管理与检索调试也互相干扰。

### 本切片范围

单一抽屉保留，不新增 evidence owner；内部拆为三个 tab：

1. **本次回答依据**：默认层，只读取当前 Turn 的 server-owned EvidenceSnapshot；只显示 selected 或 pedagogy 明确引用的证据，不显示候选、分数、上下文或文档管理；
2. **我的资料**：只显示长期知识库文档、active/superseded/excluded 状态、恢复、删除和重建；
3. **检索诊断**：显示 candidate/read/rejected/selected 生命周期、排序、相关度、命中词、评分明细、来源片段和模型上下文。

边界：

- `normalizeEvidence()` 继续只解释服务端 EvidenceSnapshot；
- 前端不得根据检索排序自行把 candidate 标为 selected；
- `ragSearch` 手动查询结果只属于诊断层；
- 普通层没有 selected evidence 时明确显示“暂无可核对依据”，不得回退展示 candidate；
- 不在本切片改 EvidenceTrail、RAG 后端、SessionNavigator、设置或 closure UX。

### 门禁

- Vitest 验证默认层不含 candidate、score、context 和 document management；
- Vitest 验证诊断层包含完整生命周期，资料层只包含文档管理；
- Chromium desktop / 390px 验证真实 Sources 抽屉默认 tab、tab 切换、server-owned selected evidence 和无横向溢出；
- 原有 16 个浏览器用例继续通过；
- pytest、RAG K1、Ruff、package、detect-secrets、mypy、Vitest、TypeScript 和 Vite 全绿。

## 8. 后续顺序

1. P0-A5 `ux/closure-review-first`：默认结束流程只展示确认、缺口、下次入口和保存；
2. P0-A6 `refactor/session-navigation-single-owner`：唯一 SessionNavigator；
3. P0-A7 `ux/onboarding-settings-progressive-disclosure`：新手与设置渐进披露；
4. P0-A8 `a11y/focus-feedback-responsive`：焦点、复制、上传、触控、软键盘和溢出。

## 9. 审计完成标准

- 学习真值门禁成立；五类 Golden Journey 在 desktop 和 390px 全部通过；
- first answer 无强制配置；学习恢复、资料学习、联网研究不超过两层 surface；
- 刷新、网络失败和 stream interruption 有明确恢复路径；
- 首屏不依赖隐藏实验模块；普通证据层只显示 adopted evidence；
- 默认结束流程不要求理解 Memory 文件；桌面/移动使用同一会话 owner；
- 键盘、焦点、复制、上传和窄屏问题有自动回归；全量 CI 通过。

## 10. 审计期间冻结

真实 Provider claim replay、生产 claim producer、claim UI、Streamlit 清理、RAG-K1f、RAG-K2、自适应 LearningPlan、G10-D 可执行代理继续冻结。

## 11. 当前执行状态

- 当前分支：`ux/sources-three-layer-separation`；
- 基线：PR #70 merge SHA `ccdea493d8d0119e9ba0b9c203a06b5f14de1229`；
- 当前阶段：三层 SourcesPanel、组件所有权测试和真实浏览器抽屉测试已写入；
- 下一动作：建立 Draft PR，运行完整门禁，根据证据修复实现或测试；
- 合并策略：独立小分支 -> Draft PR -> 完整门禁 -> 全绿合并。

## 12. 文档规则

- 当前状态只更新本文件；status-only 更新留在 active branch；
- `ARCHITECTURE_STATUS.md` 只维护稳定 owner/边界；`STATE_MODEL.md` 只维护稳定数据模型；
- 不新增并列长期状态文档；代码、CI、分支和 PR 变化必须同步本文件。

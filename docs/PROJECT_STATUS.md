# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-07-27  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**学习真值、五类浏览器旅程和核心首屏按需加载均已通过实现门禁；PR #70 状态同步后重跑最终 CI。**  
> 当前分支：`perf/core-bootstrap-lazy-features`，Draft PR #70。

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
- Chromium desktop / 390px 五类 Golden Journey 浏览器基线。

已合并：

- PR #61 `597006e99919ea7e5f5b02f01b1536b446da9a55`，CI #1317；
- PR #62 `fcfb9bc66750d10c822306fae735424e658b19ef`，CI #1340；
- PR #63 `f1b2a4f9d481a16e5c93e6ac8fb4c0f9ee2f45c2`，CI #1357；
- PR #64 `451bc4a78fc3eda6219083371591aa46c8e62900`，CI #1368；
- PR #65 `b700da1a2751769959ae1b41966f5da0a854162a`，CI #1389；
- PR #66 `b1ac5a841aab5948b4fee623aeaea1d87e1b8af9`，CI #1407；
- PR #67 `c19d5070b9bcf73ed46a81731bbeae842b757208`，CI #1416；
- PR #68 `4da85690043e9144b18dabaf0b4d2359c16eaeb8`，CI #1437；
- PR #69 `04ac7d59c2f7ed76eee7192c3500ebbb6bc6d286`，CI #1449。

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

## 6. P0-A3 已完成实现：核心首屏按需加载

### 结构变化

- 新增 core loader，普通 bootstrap 只拥有 health、sessions、runtime settings；
- core refresh 只覆盖核心字段，已经按需加载的 feature data 不会被聊天后的 refresh 清空；
- feature loader 单独拥有 RAG status、tools、workflow summaries、memory status 和 WeChat；
- `useUploadController` 不再在挂载时读取知识库文档；
- 当前抽屉由 controller owner 触发对应 feature loader；
- 持久化 active session / RagRun / MemoryRun / ResearchRun 等恢复 effect 保留，不因首屏收窄而丢失 durable truth；
- feature loader 错误不写入 `snapshot.errors`，未打开模块的故障不再进入普通全局告警。

### 真实浏览器请求结果

干净首屏从 9 个业务请求收窄为 3 个：

```text
GET /health
GET /sessions
GET /runtime/settings
```

未打开功能时以下请求均为 0：

```text
/rag/status
/knowledge-base/documents
/tools
/workflows/runs
/memory
/wechat
```

显式打开后：

- Sources -> `/rag/status` + `/knowledge-base/documents`；
- 群聊 -> `/wechat`；
- 工具 -> `/tools`；
- 开发者诊断 -> `/workflows/runs`；
- 学习成果 -> `/memory`。

隐藏六类接口全部模拟 503 时，desktop 和 390px 普通首屏仍不显示“部分功能暂不可用”或“API 未连接”。打开各抽屉时只请求本功能数据。

### 门禁

- 实现 head `6b9d8e7e108f0f9da0282027d544b3199c93e55d`；
- CI #1460：全部后端、RAG、类型、Vitest、Vite 和 16 个 desktop/mobile Chromium 用例全绿；
- 本状态提交后必须对最新 head 重跑完整 CI，未通过前 PR #70 保持 Draft。

## 7. 后续顺序

1. P0-A4 `ux/sources-three-layer-separation`：本次回答依据 / 我的资料 / 检索诊断；
2. P0-A5 `ux/closure-review-first`：默认结束流程只展示确认、缺口、下次入口和保存；
3. P0-A6 `refactor/session-navigation-single-owner`：唯一 SessionNavigator；
4. P0-A7 `ux/onboarding-settings-progressive-disclosure`：新手与设置渐进披露；
5. P0-A8 `a11y/focus-feedback-responsive`：焦点、复制、上传、触控、软键盘和溢出。

## 8. 审计完成标准

- 学习真值门禁成立；五类 Golden Journey 在 desktop 和 390px 全部通过；
- first answer 无强制配置；学习恢复、资料学习、联网研究不超过两层 surface；
- 刷新、网络失败和 stream interruption 有明确恢复路径；
- 首屏不依赖隐藏实验模块；普通证据层只显示 adopted evidence；
- 默认结束流程不要求理解 Memory 文件；桌面/移动使用同一会话 owner；
- 键盘、焦点、复制、上传和窄屏问题有自动回归；全量 CI 通过。

## 9. 审计期间冻结

真实 Provider claim replay、生产 claim producer、claim UI、Streamlit 清理、RAG-K1f、RAG-K2、自适应 LearningPlan、G10-D 可执行代理继续冻结。

## 10. 当前执行状态

- 当前分支：`perf/core-bootstrap-lazy-features`，Draft PR #70；
- 基线：PR #69 merge SHA `04ac7d59c2f7ed76eee7192c3500ebbb6bc6d286`；
- 实现 head：`6b9d8e7e108f0f9da0282027d544b3199c93e55d`，CI #1460 全绿；
- 当前阶段：状态同步后验证最终 head；
- 下一动作：最终 CI 全绿后 Ready + squash merge，再进入 P0-A4；
- 合并策略：独立小分支 -> Draft PR -> 完整门禁 -> 全绿合并。

## 11. 文档规则

- 当前状态只更新本文件；status-only 更新留在 active branch；
- `ARCHITECTURE_STATUS.md` 只维护稳定 owner/边界；`STATE_MODEL.md` 只维护稳定数据模型；
- 不新增并列长期状态文档；代码、CI、分支和 PR 变化必须同步本文件。

# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-07-27  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**学习真值与五类真实浏览器 Golden Journey 已通过；PR #69 最终状态同步后重跑完整门禁，合并后进入 P0-A3 首屏按需加载。**  
> 当前分支：`test/browser-golden-journeys-evidence`，Draft PR #69。

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
- PR #68 `4da85690043e9144b18dabaf0b4d2359c16eaeb8`，CI #1437。

PR #69 当前实现 head `41589111f5d0583a6513d595a447039b730293f1` 的 CI #1447 已全绿；最终状态提交仍需重新通过完整门禁后才能合并。

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

## 5. P0-A2 已完成实现：真实浏览器 Golden Journeys

PR #68 和 PR #69 使用真实 React + Chromium + 网络级 API/SSE fixture，运行 `1440×900` 与 `390×844`。失败时保存 trace、screenshot、video、HTML report 和 JSON 指标。

桌面与 390px 结果一致：

| journey | clicks | decisions | surfaces | recovery | keyboard | refresh | overflow |
|---|---:|---:|---:|---:|---|---|---|
| first answer | 0 | 0 | 1 | 0 | pass | pass | none |
| returning learning | 1 | 1 | 1 | 1 | n/a | pass | none |
| chat 503 recovery | 1 | 0 | 1 | 1 | n/a | pass | none |
| material learning + adopted evidence | 3 | 1 | 1 | 0 | n/a | pass | none |
| web research recovery + adopted evidence | 2 | 0 | 1 | 1 | n/a | pass | none |
| source-code learning + adopted evidence | 2 | 0 | 1 | 0 | n/a | pass | none |

实际验证：

- 上传走隐藏文件输入、RagRun、知识库刷新和明确学习方式选择；
- 普通 EvidenceTrail 只显示 selected/adopted local evidence，candidate 不出现；
- failed ResearchRun 从持久化 `webLookupRunId` 恢复，一次点击重试后进入下一轮聊天；
- 下一轮请求携带同一 ResearchRun ID，回答使用 server-owned selected research evidence；
- 源码学习继续显示目标、缺口和下一步，GitHub 只作为 supporting evidence；
- 所有新增回答和 adopted evidence 在刷新后恢复；
- 所有旅程保持一个 product surface，390px 无横向溢出。

指标来自真实浏览器动作与 DOM 状态，不是组件测试常量。

### 修正记录

- CI #1443：7/12 通过；上传缺 RagRun GET fixture，研究 seed 在刷新时覆盖新会话，源码移动端定位到隐藏重复元素；
- CI #1445：10/12 通过；上传和研究桌面/移动全部通过，只剩恢复卡目标严格定位歧义；
- CI #1447：12/12 浏览器用例及全部仓库门禁全绿；修正均位于测试 fixture/定位，没有修改生产代码或放宽 evidence truth。

## 6. 下一阶段：P0-A3 核心首屏按需加载

分支：`perf/core-bootstrap-lazy-features`。

目标：

1. 首屏只请求 health、sessions、runtime settings 和当前恢复所需数据；
2. Memory、Sources、group、news、tools、workflow 按抽屉打开或实际使用时加载；
3. 隐藏模块失败不进入普通全局告警；
4. 保留 last-good、部分服务可用和恢复语义；
5. 浏览器门禁记录首屏请求集合、隐藏模块零请求和按需加载行为；
6. 不在本切片重构 Sources、SessionNavigator、设置或 closure UX。

## 7. 后续顺序

1. P0-A3 `perf/core-bootstrap-lazy-features`：首屏按需加载，隐藏模块失败不污染普通告警；
2. P0-A4 `ux/sources-three-layer-separation`：本次回答依据 / 我的资料 / 检索诊断；
3. P0-A5 `ux/closure-review-first`：默认结束流程只展示确认、缺口、下次入口和保存；
4. P0-A6 `refactor/session-navigation-single-owner`：唯一 SessionNavigator；
5. P0-A7 `ux/onboarding-settings-progressive-disclosure`：新手与设置渐进披露；
6. P0-A8 `a11y/focus-feedback-responsive`：焦点、复制、上传、触控、软键盘和溢出。

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

- 当前分支：`test/browser-golden-journeys-evidence`，Draft PR #69；
- 基线：PR #68 merge SHA `4da85690043e9144b18dabaf0b4d2359c16eaeb8`；
- 实现 head：`41589111f5d0583a6513d595a447039b730293f1`，CI #1447 全绿；
- 当前阶段：状态文档同步后，对最新 head 重跑完整 CI；
- 下一动作：最终 head 全绿后 Ready + squash merge，随后从最新 `main` 建立 P0-A3 分支；
- 合并策略：独立小分支 -> Draft PR -> 完整门禁 -> 全绿合并。

## 11. 文档规则

- 当前状态只更新本文件；status-only 更新留在 active branch；
- `ARCHITECTURE_STATUS.md` 只维护稳定 owner/边界；`STATE_MODEL.md` 只维护稳定数据模型；
- 不新增并列长期状态文档；代码、CI、分支和 PR 变化必须同步本文件。

# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-07-28  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**P0-E1 已完成；P0-E2 第一切片“成功截图与真实动作指标”已进入 `main`，当前推进 360px / 窄高度与复杂内容门禁。**  
> 解冻条件：**P0-E2 完成前，真实 Provider AnswerClaim replay 与生产 claim/agent 扩张继续冻结。**

本文件只维护当前事实、指标、缺口、顺序和门禁。不得新增并列长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT 文档。

## 1. 产品边界

```text
当前目标 -> 教学/练习 -> 资料与证据 -> 理解验证
-> 已确认/未解决 -> 下一步 -> 整理与恢复
```

- RAG 服务于围绕自己的资料学习；Web Research 服务于需要外部事实的任务。
- GitHub 是源码学习证据来源，不是第二个执行产品或顶级工作台。
- Memory 是连续性基础设施；Workflow 只属于高级诊断。
- React 是交互和可重建缓存；SQLite durable entities 是运行真值。
- planned / attempted / partial / failed 不得覆盖 committed truth。
- 当前冻结横向扩展，以核心学习闭环是否真实可用为判断标准。

## 2. 已完成主链

- TaskContract、LearningClosureRun、ThreadSummaryState、结构化恢复卡；
- RAG K1a-K1e、EvidenceSnapshot、ResearchRun source truth；
- AnswerClaimSnapshot v1 与 record-only 离线评测；
- 生产路径学习验证 E2E；
- desktop / 390px Golden Journeys；
- 核心首屏按需加载与隐藏功能错误隔离；
- 资料与来源三层收口；
- 学习结束 review-first；
- desktop / mobile SessionNavigator 单一交互 owner；
- 新手入口与设置渐进披露；
- SlideOver 键盘焦点闭环、复制反馈、上传前置合同和窄屏/软键盘体验门禁；
- React -> FastAPI -> SQLite 的确定性真实全栈浏览器运行时；
- 首次学习、理解验证、真实上传/索引/证据、learning closure、中断续写和失败重试的真实组合门禁；
- 选定绿色旅程的命名成功截图、manifest、真实动作 recorder 与证据完整性 teardown。

近期已进入 `main`：

- PR #72 `3796bfe3bbc7c83feac9eeb9f195803a5ed57228`，最终 CI #1496；
- PR #73 `676fe23a0f26d500712b71c6e175d99d953f1e80`，最终 CI #1520；
- PR #74 `911e83769c1b53849fe21772099bec0323357180`，最终 head CI #1546；
- PR #76 `267969d92f0eaed4d6b2dc6b631a5380dd86f591`，最终 CI #1554；
- PR #77 `836a50c306b1af17f1c01e07dc96291cb5da9b30`，最终 head CI #1579；
- PR #78 `b5bf2239cc93f1d30e3914010ee88d548ab2b8ca`，第一切片状态同步；
- PR #79 `6934b77e88e49244614af4e74eae980911229c80`，最终 head CI #1595；
- PR #80 `56b584c1a9ab28eeb997e5636015270be501d32a`，第二切片状态同步，CI #1599；
- PR #81 `2ed83b57d49b8057a128b9e3df62da62a7be133e`，最终 head CI #1609；
- PR #82 `b2d178777e43a2c165e9b4229b0531db855bfe8e`，P0-E1 完成状态同步，CI #1613；
- PR #83 `c90bc39ad3bbe9137e035d0892122b3b86755749`，最终 head CI #1626。

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

### P0-E2 首批 observed journey metrics

以下数字来自浏览器事件 recorder，而不是用例手写常量；desktop 与 390px 结果一致：

| 旅程 | 点击 | 配置/推进决策 | 恢复动作 | 发送 | 用户滚动 | 表面并集 |
|---|---:|---:|---:|---:|---:|---|
| 首次回答 | 0 | 0 | 0 | 1 | 0 | main、returning restore |
| 返回学习 | 1 | 1 | 1 | 1 | 0 | main、returning restore |
| 失败重试 | 1 | 0 | 1 | 1 | 0 | main、interrupted recovery、returning restore |

三条旅程均无横向溢出。首次回答为 keyboard-only 路径。

## 4. 已验证的产品闭环

| 闭环 | 当前结论 | 真实证据边界 |
|---|---|---|
| 首次开始 | 真实全栈通过、成功证据可审查 | React/FastAPI/SQLite 与 desktop/390px 成功步骤截图；0 点击、0 配置决策 |
| 返回学习 | 可用、成功证据可审查 | 恢复上下文、一次明确选择、继续后刷新；1 点击、1 决策、1 恢复动作 |
| 上传资料学习 | 真实全栈通过 | Markdown 校验、解析、document/revision identity、staging/activation、检索、selected evidence 与刷新恢复 |
| 联网研究 | 基础恢复可用 | multi-step research 与完整 cancel propagation 仍是 P1 生命周期补强项 |
| 源码学习 | 展示与恢复可用 | symbol mapping 与 CI association 精度仍不足以证明稳定理解源码关系 |
| 理解验证 | 真实全栈通过 | 空泛“懂了” reject；正确推理进入 committed truth 和 transfer，并刷新恢复 |
| 学习结束 | 真实全栈通过 | closure preview、冻结候选、MemoryRun hash、确认写入、summary、刷新、归档并新建 |
| 中断恢复 | 真实全栈通过 | Stop 后 partial 保存为 interrupted；刷新恢复；同 turn id 续写；前缀不重复；只提交一次 |
| 失败重试 | 真实全栈通过、成功证据可审查 | 零-token failed / fixture failure 均有明确 retry；一次恢复点击；刷新恢复最终结果 |

## 5. P0-E1 第一切片：首次学习与理解验证

PR #77 建立首个真实组合门禁：

```text
Playwright browser
-> Vite proxy
-> production FastAPI routes
-> ExternalDataPolicyChatService / TaskContract / pedagogy
-> production SQLite repositories
-> session reload and UI restoration
```

- 测试入口只替换外部模型与网络 gateway；生产 route、application service、transaction 和 repository 继续执行；
- 每个用例清空临时数据库、WAL/SHM 和导出目录，desktop / mobile 不共享状态；
- desktop / 390px 覆盖首次系统学习、SQLite durable truth、刷新恢复、空泛理解 reject、正确推理 commit；
- CI #1579 全量门禁通过。

真实门禁暴露并修复默认路由缺口：`TaskContract` 已识别 `learn`，但自动学习方式仍可能进入普通 direct answer。当前“带我系统学习……”自动进入苏格拉底协议；用户显式选择直接讲解时仍保留手动控制。

## 6. P0-E1 第二切片：上传、证据与 learning closure

### 6.1 真实上传与资料学习

```text
File chooser
-> multipart upload
-> 服务端文件合同
-> Markdown parser
-> document / revision identity
-> staging index
-> active index
-> local retrieval
-> EvidenceSnapshot
-> selected evidence
-> refresh restoration
```

- RAG 上传目录、索引文件和 SQLite 均隔离在临时运行时；
- 浏览器不通过 `page.route` 伪造上传、检索或聊天 API；
- 用户明确要求完整讲解时，生产披露策略将真实检索到的本地文档标记为 selected；普通苏格拉底推导阶段仍允许 withholding；
- UI、API、RAG index、SQLite turn snapshot 和刷新结果一致。

### 6.2 learning closure

```text
committed learning state
-> LearningClosureRun
-> deterministic external generator
-> frozen candidates
-> MemoryRun preview
-> updates hash
-> user confirmation
-> safe writer
-> ThreadSummaryState
-> refresh
-> archive and new session
```

- 保留生产 LearningClosureService、MemoryRun、hash 校验、safe writer、summary metadata 与归档流程；
- 只替换外部 closure candidate generator；
- 修复 Vite 缺少 `/learning-closure-runs` 代理的问题；
- desktop / 390px 均完成 preview、确认写入、长期记忆读取、刷新恢复、归档并新建；
- CI #1595 通过全部基础门禁、34/34 fixture Golden Journeys 与 8/8 real-stack cases。

## 7. P0-E1 第三切片：中断续写与失败重试

### 7.1 stream interruption -> continuation

- 浏览器真实点击 Stop，Abort 传到 FastAPI；
- partial reply 保存为 `interrupted`，thread committed truth 不变；
- attempted snapshot 保留，但不存在 `committed_learning_state`；
- 刷新后恢复卡显示 partial 和“从断点继续”；
- continuation 复用原 turn id，只生成剩余后缀，不重复已有前缀；
- 成功后同一 turn 变为 completed，只提交一次 learning state。

### 7.2 zero-token failure -> retry

- Provider 在首 token 前异常时保存为 `failed`，不再错误标记为 `interrupted`；
- UI 只提供“重新生成”，不提供无意义的断点继续；
- failed parent 保留 attempted truth，不推进 thread committed state；
- retry 创建一个 child turn，成功后 parent 变为 superseded；
- 只有成功 child 提交 learning state，刷新后只恢复最终结果。

CI #1609 通过全部基础门禁、34/34 fixture Golden Journeys 与 12/12 real-stack cases。

## 8. P0-E2：可审查成功体验证据

### 8.1 第一切片已完成：成功产物与真实动作指标

PR #83 建立了稳定证据合同：

- browser recorder 自动采集 click、Tab/Enter/Escape、composer submit、wheel/touch/滚动键、明确决策、恢复动作和 surface switch；
- recorder 使用 session storage 跨刷新保留完整旅程，而不依赖用例手写计数；
- 首次回答、返回学习、失败重试各保留 3 个命名步骤，覆盖 desktop 与 390px，共 18 张 PNG；
- 所有截图为真实 viewport 尺寸：desktop 1440×900、mobile 390×844；不使用 full-page，避免固定 composer 覆盖页面中段和截图过程污染滚动指标；
- manifest 记录 journey、project、step、viewport、scroll position、document height 和可见 product surfaces；
- `product_surfaces` 按所有成功步骤取并集，不再只统计结束页面的 main/dialog；
- global teardown 强制校验 18 张截图、manifest、6 条 observed metric、文件非空和交叉引用；
- CI #1626 通过全部后端/静态/前端门禁、34/34 fixture Golden Journeys、evidence completeness teardown 与 12/12 real-stack cases。

人工初步查看产物时已记录一个待 P0-E2 最终试玩复核的表达问题：fixture 的 503 失败恢复卡仍使用“上次回答在生成过程中中断”这一泛化标题，功能路径正确，但 failed 与 interrupted 的用户语义可能不够清楚。当前切片不扩张产品修改，保留为人工试玩输入。

### 8.2 当前执行项：360px / 窄高度与复杂内容

1. 增加 360px 与 360×520 窄高度项目，不扩大到新浏览器引擎；
2. 覆盖长中文连续文本、长 URL、长代码块和多段列表；
3. 使用真实 compositionstart / compositionupdate / compositionend 验证输入法组合期间 Enter 不误发送，组合结束后可正常发送；
4. 使用 wheel/touch 手势产生真实滚动指标，并验证刷新后消息位置、恢复卡和 composer 仍可达；
5. 检查关键文字截断、横向溢出、代码块内部滚动、固定元素遮挡和安全区；
6. 将代表性绿色步骤加入成功证据包与 manifest，而不是只保留失败截图。

### 8.3 后续：人工试玩记录

- 基于成功截图、manifest 和 observed metrics，而不是只看测试通过；
- 记录阻断、困惑点、可接受项和需要进入修复切片的问题；
- P0-E2 结论写回本文件后，才允许解冻 Provider replay。

## 9. P1 / P2 缺口

**P1：**

1. P0-E2 通过后，解冻真实 Provider AnswerClaim replay，但保持 record-only，不接生产 ChatTurn；
2. 根据真实 replay 决定先做 claim producer 还是 RAG-K1f / K2；
3. 加强 GitHub replay 的 symbol mapping、CI association precision 和 partial-result 解释；
4. 补 multi-step research / cancel 的完整生命周期门禁。

**P2：**

1. 增加 Firefox/WebKit 兼容抽样；
2. 清理 README 中 Streamlit“已移除”与“兼容入口仍存在”的表述差异；
3. 继续校准 Golden Journey 指标，使点击、决策、surface、恢复能够跨用例比较。

## 10. 当前冻结与执行状态

- `main` 当前 P0-E2 第一切片 merge SHA：`c90bc39ad3bbe9137e035d0892122b3b86755749`；
- PR #83 已 closed / merged，最终 feature head `f95796bd1126cb2ea1329ef94cfe1630834da731`，CI #1626 完整全绿；
- 当前状态分支：`docs/p0-e2-success-evidence-status`；
- 下一实现顺序：360px/复杂内容 -> 人工试玩记录 -> P0-E2 总结；
- 真实 Provider claim replay 在 P0-E2 通过前继续冻结；
- 生产 claim producer、claim UI、Streamlit 清理、RAG-K1f、RAG-K2、自适应 LearningPlan、G10-D 可执行代理继续冻结；
- 合并策略：独立小分支 -> Draft PR -> 完整门禁 -> 全绿合并。

## 11. 文档规则

- 当前状态只更新本文件；status-only 更新留在 active branch；
- `ARCHITECTURE_STATUS.md` 只维护稳定 owner/边界；`STATE_MODEL.md` 只维护稳定数据模型；
- 不新增并列长期状态文档；代码、CI、分支和 PR 变化必须同步本文件。

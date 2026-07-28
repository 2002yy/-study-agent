# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-07-28  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**P0-E1 前两个真实全栈切片已进入 `main`；正在补最后一个 interruption continuation / failed retry 切片。**  
> 下一阶段：**P0-E1 完成后进入 P0-E2 可审查成功体验证据；真实 Provider AnswerClaim replay 在两者完成前继续冻结。**

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
- SlideOver 键盘焦点闭环、复制结果反馈、上传前置合同和窄屏/软键盘体验门禁；
- React -> FastAPI -> SQLite 的确定性真实全栈浏览器运行时。

近期已进入 `main`：

- PR #72 `3796bfe3bbc7c83feac9eeb9f195803a5ed57228`，最终 CI #1496；
- PR #73 `676fe23a0f26d500712b71c6e175d99d953f1e80`，最终 CI #1520；
- PR #74 `911e83769c1b53849fe21772099bec0323357180`，最终 head CI #1546；
- PR #76 `267969d92f0eaed4d6b2dc6b631a5380dd86f591`，最终 CI #1554；
- PR #77 `836a50c306b1af17f1c01e07dc96291cb5da9b30`，最终 head CI #1579；
- PR #78 `b5bf2239cc93f1d30e3914010ee88d548ab2b8ca`，第一切片状态同步；
- PR #79 `6934b77e88e49244614af4e74eae980911229c80`，最终 head CI #1595。

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

## 4. 已验证的产品闭环

| 闭环 | 当前结论 | 真实证据边界 |
|---|---|---|
| 首次开始 | 真实全栈通过 | desktop / 390px 从 UI 进入 Vite、FastAPI、application service 与 SQLite，并刷新恢复 |
| 返回学习 | 基础可用 | fixture 旅程已覆盖；真实动作成本将在 P0-E2 采集 |
| 上传资料学习 | 真实全栈通过 | Markdown 校验、解析、document/revision identity、staging/activation、检索、selected evidence 与刷新恢复 |
| 联网研究 | 基础恢复可用 | multi-step research 与完整 cancel propagation 仍是 P1 生命周期补强项 |
| 源码学习 | 展示与恢复可用 | symbol mapping 与 CI association 精度仍不足以证明稳定理解源码关系 |
| 理解验证 | 真实全栈通过 | 空泛“懂了” reject；正确推理进入 committed truth 和 transfer，并刷新恢复 |
| 学习结束 | 真实全栈通过 | closure preview、冻结候选、MemoryRun hash、确认写入、summary、刷新、归档并新建 |
| 中断/失败恢复 | 待最后切片 | 缺同一真实全栈运行中的 interruption continuation 与 failed retry 证明 |

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

真实门禁暴露并修复了默认路由缺口：`TaskContract` 已识别 `learn`，但自动学习方式仍可能进入普通 direct answer。当前“带我系统学习……”自动进入苏格拉底协议；用户显式选择直接讲解时仍保留手动控制。

## 6. P0-E1 第二切片：上传、证据与 learning closure

PR #79 在同一真实运行时中新增：

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
- 修复 Vite 缺少 `/learning-closure-runs` 代理的问题，避免 commit 在到达 FastAPI 前被前端 404 截断；
- desktop / 390px 均完成 preview、确认写入、长期记忆读取、刷新恢复、归档并新建；
- CI #1595 通过 pytest、RAG K1、Ruff、package、detect-secrets、expanded mypy、前端测试/构建、34/34 fixture Golden Journeys 与 8/8 real-stack cases。

## 7. P0-E1 最后切片：当前执行项

只补恢复真值链，不新增顶级产品表面：

1. **stream interruption -> continuation**
   - 服务端确定性流在输出部分内容后中断；
   - turn 保存为 `interrupted`，partial reply 可见且可刷新恢复；
   - learning state 不因 partial 覆盖 committed truth；
   - 用户继续生成后复用同一个 turn id，保留前缀，不重复内容；
   - 最终只产生一个 completed turn 和一次学习状态提交。

2. **failed turn -> retry**
   - 服务端第一次确定性失败，turn 保存为 `failed`；
   - UI 暴露现有“重新生成”入口；
   - retry 创建同 thread 的 child turn，parent truth 保留并在成功后 superseded；
   - failed attempt 不推进学习状态；
   - 刷新只恢复最终 committed result，不产生重复提交。

3. **门禁要求**
   - desktop / 390px；
   - 核心 API 无浏览器 fixture；
   - UI、API、SQLite durable state 与刷新结果一致；
   - 34 个既有 Golden Journeys、8 个现有 real-stack cases 与全部后端/静态门禁不回退。

## 8. P0-E2：可审查的成功体验证据

P0-E1 完成后立即执行：

- 对选定绿色 Golden Journeys 保留关键步骤截图，而不是只在失败时保留 trace/screenshot/video；
- 点击、键盘、发送、滚动、surface 切换和恢复动作由测试辅助层实际采集，不再由用例手写常量；
- `product_surfaces` 反映抽屉、恢复卡、上传承接、证据层和 closure review；
- 加入 360px/窄高度、长中文、长代码块、输入法 composition 和真实滚动位置检查；
- 完成一次基于成功产物的人工试玩记录，识别“功能正确但难以理解或推进”的问题。

## 9. P1 / P2 缺口

**P1：**

1. P0-E1 / P0-E2 通过后，解冻真实 Provider AnswerClaim replay，但保持 record-only，不接生产 ChatTurn；
2. 根据真实 replay 决定先做 claim producer 还是 RAG-K1f / K2；
3. 加强 GitHub replay 的 symbol mapping、CI association precision 和 partial-result 解释；
4. 补 multi-step research / cancel 的完整生命周期门禁。

**P2：**

1. 增加 Firefox/WebKit 与更小宽度兼容抽样；
2. 清理 README 中 Streamlit“已移除”与“兼容入口仍存在”的表述差异；
3. 校准 Golden Journey 指标，使点击、决策、surface、恢复能够跨用例比较。

## 10. 当前冻结与执行状态

- `main` 当前 P0-E1 第二切片 merge SHA：`6934b77e88e49244614af4e74eae980911229c80`；
- PR #79 已 closed / merged，最终 feature head `5a2731a3a27c12e4515929f4b4267e3f45ac0f49`，CI #1595 完整全绿；
- 当前状态分支：`docs/p0-e1-slice2-merged-status`；
- 下一实现顺序：interruption continuation 与 failed retry -> P0-E2；
- 真实 Provider claim replay 在 P0-E1 / P0-E2 通过前继续冻结；
- 生产 claim producer、claim UI、Streamlit 清理、RAG-K1f、RAG-K2、自适应 LearningPlan、G10-D 可执行代理继续冻结；
- 合并策略：独立小分支 -> Draft PR -> 完整门禁 -> 全绿合并。

## 11. 文档规则

- 当前状态只更新本文件；status-only 更新留在 active branch；
- `ARCHITECTURE_STATUS.md` 只维护稳定 owner/边界；`STATE_MODEL.md` 只维护稳定数据模型；
- 不新增并列长期状态文档；代码、CI、分支和 PR 变化必须同步本文件。

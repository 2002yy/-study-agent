# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-07-29  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**P0-E1、P0-E2 与 P0-E3 第一切片“真实 Provider AnswerClaim replay 运行合同”已进入 `main`；当前等待显式选择 Provider / 精确模型并执行真实 record-only replay。**  
> 冻结边界：**生产 claim producer / claim UI、生产 ChatTurn 接入与可执行 agent 扩张继续冻结，必须由真实 replay 结果决定后续顺序。**

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
- 当前仍冻结横向产品扩张，以真实 replay、质量门禁和核心学习闭环为判断标准。

## 2. 已完成主链

- TaskContract、LearningClosureRun、ThreadSummaryState、结构化恢复卡；
- RAG K1a-K1e、EvidenceSnapshot、ResearchRun source truth；
- AnswerClaimSnapshot v1、deterministic evaluator self-test 与 record-only real-provider replay adapter；
- 真实 Provider 回答报告 -> 离线 AnswerClaim 严格校验 -> 双 artifact 的手动 workflow 合同；
- 生产路径学习验证 E2E；
- desktop / 390px / 定向 360×520 Golden Journeys；
- 核心首屏按需加载与隐藏功能错误隔离；
- 资料与来源三层收口；
- 学习结束 review-first；
- desktop / mobile SessionNavigator 单一交互 owner；
- 新手入口与设置渐进披露；
- SlideOver 键盘焦点闭环、复制反馈、上传前置合同和窄屏/软键盘体验门禁；
- React -> FastAPI -> SQLite 的确定性真实全栈浏览器运行时；
- 首次学习、理解验证、真实上传/索引/证据、learning closure、中断续写和失败重试的真实组合门禁；
- 命名成功截图、manifest、浏览器真实动作 recorder、对话滚动几何与证据完整性 teardown；
- 长中文、长 URL、宽代码、IME composition、真实 wheel 滚动、回到最新与刷新恢复的 360×520 门禁。

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
- PR #83 `c90bc39ad3bbe9137e035d0892122b3b86755749`，最终 head CI #1626；
- PR #84 `28176449373d9819a40ad35768741095d3b888c5`，P0-E2 第一切片状态同步，CI #1630；
- PR #85 `fab62bc526acef7c7f6fd0ebcdcef8661c01ad49`，最终 head CI #1659；
- PR #86 `a974efdf712df4a4dd6b0ef5690327c558c932a4`，P0-E2 完成状态同步；
- PR #87 `97bd0a02b6738d7d34aac112ccbc756a851bd14c`，P0-E3 replay 运行合同，最终 head CI #1680。

## 3. 当前真实指标

### RAG K1

- 12 documents；30 retrieval cases / 26 answerable；10 answer-quality gold；
- source recall@K 0.923077；nDCG 0.903600；adaptive recall@K 0.942308；
- multi-source recall@K 0.9；stale / forbidden leakage 0；
- deterministic answerable 26/26；unanswerable block 4/4。

这些是固定 corpus 回归合同，不代表真实模型最终质量。

### AnswerClaim real-provider replay

- 固定输入：完整 10 条 K1 answer-quality gold；
- 运行合同：已完成并进入 `main`；
- 实际 real-provider artifact：**尚未执行**；
- claim coverage、unsupported-claim rate、link alignment、refusal leakage、稳定性、latency、usage 与成本：**暂无真实数字**；
- deterministic / synthetic 测试只证明合同可执行，不得冒充真实模型质量。

### GitHub replay

- 15 repos；17 cases；15 Provider replay；partial rate 0.7647；
- symbol mapping P/R/F1 0.625 / 0.4545 / 0.5263；
- CI association P/R/F1 0.3529 / 1.0 / 0.5217。

G10-D 可执行代理继续冻结。

### P0-E2 observed journey metrics

以下数字来自浏览器事件 recorder，而不是用例手写常量；前三条 desktop 与 390px 结果一致：

| 旅程 | 点击 | 配置/推进决策 | 恢复动作 | 发送 | 用户滚动 | 表面并集 |
|---|---:|---:|---:|---:|---:|---|
| 首次回答 | 0 | 0 | 0 | 1 | 0 | main、returning restore |
| 返回学习 | 1 | 1 | 1 | 1 | 0 | main、returning restore |
| 失败重试 | 1 | 0 | 1 | 1 | 0 | main、interrupted recovery、returning restore |
| 360×520 复杂内容 | 1 | 0 | 0 | 1 | 1 | main、returning restore |

- 四条旅程均无页面级横向溢出；首次回答为 keyboard-only 路径。
- 复杂内容旅程中的一次点击为“回到最新”；真实 wheel 记录为 `wheel:-700`。
- IME 组合期间的 Enter 不提交；composition end 后 Enter 只提交一次。

### P0-E2 成功证据包

- 23 张真实 viewport PNG：desktop 1440×900 共 9 张、mobile 390×844 共 9 张、narrow 360×520 共 5 张；
- 360×520 对话可视高度 251px；
- 用户滚动后距底部 700px；点击“回到最新”后距底部 0；刷新后仍为 0；
- 宽代码只在代码块内部横向滚动；长 URL 在消息边界内换行；
- global teardown 强制校验截图数量、尺寸、manifest、observed metrics、文件非空和交叉引用。

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
| 窄屏复杂内容 | 通过、成功证据可审查 | 360×520 长文/URL/代码、IME、真实滚动、回到最新、主动发送定位与刷新恢复 |

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

## 8. P0-E2：可审查成功体验证据——已完成

### 8.1 第一切片：成功产物与真实动作指标

PR #83 建立稳定证据合同：

- browser recorder 自动采集 click、Tab/Enter/Escape、composer submit、wheel/touch/滚动键、明确决策、恢复动作和 surface switch；
- recorder 使用 session storage 跨刷新保留完整旅程，而不依赖用例手写计数；
- 首次回答、返回学习、失败重试各保留 3 个命名步骤，覆盖 desktop 与 390px，共 18 张 PNG；
- 截图使用真实 viewport，不使用 full-page，避免固定 composer 覆盖页面中段和截图过程污染滚动指标；
- manifest 记录 journey、project、step、viewport、scroll position、document height 和可见 product surfaces；
- `product_surfaces` 按所有成功步骤取并集，不再只统计结束页面；
- CI #1626 通过全部门禁。

### 8.2 第二切片：360×520、复杂内容、IME 与真实滚动

PR #85 增加一个定向 `narrow-chromium` 项目，而不是把全部旅程扩成三倍：

- 覆盖长中文连续文本、长 URL、宽代码和多段列表；
- 验证长 URL 不撑破消息，宽代码由代码块内部滚动承接；
- compositionstart / compositionupdate / compositionend 期间 Enter 不误发送；
- 使用真实 wheel 产生滚动，验证“回到最新”和刷新恢复；
- manifest 增加 conversation scrollTop / scrollHeight / clientHeight / distance-from-bottom；
- evidence completeness 从 18 张扩展到 23 张；
- Playwright 明确分离 34 条 fixture、1 条 narrow 和 12 条 real-stack。

真实门禁连续暴露并修复：

1. 移动端 chat 可能按内容高度扩张，conversation 不是真正 scroll owner；
2. 长 Markdown 刷新恢复可能停在中段；
3. 用户在旧内容位置主动发送后，新问题和回答不可见；
4. “回到最新”可能被 composer 覆盖或被 sticky header 拦截；
5. 在 360×520 下，学习状态、topbar 与单列 composer 一度只给对话留下约 10px。

最终结构：conversation 拥有独立 viewport shell；短手机窗口只保留目标与验证状态，topbar 操作保持单行，composer 使用紧凑横向发送。390×844 正常移动布局不受短高度规则影响。CI #1659 通过全部门禁、35/35 fixture+narrow 与 12/12 real-stack。

### 8.3 基于成功证据的人工复核记录

本次人工复核基于 23 张成功截图、manifest 与 observed metrics；不是实体手机和真实操作系统输入法的实机测试。

**已消除的阻断：**

- 360×520 对话区不再坍缩，稳定保留 251px 阅读高度；
- composer、顶部操作和“回到最新”互不遮挡；
- 主动发送后回到最新，后台新增内容仍尊重用户旧阅读位置；
- 刷新后恢复到最终回答；
- 长 URL、代码块和列表未造成页面横向溢出。

**可接受项：**

- 短高度下隐藏阶段与下一步等次要状态，只保留目标和验证状态，符合渐进披露原则；
- “回到最新”浮在对话右下角，会覆盖小块正文，但只在离开底部时出现，且可立即恢复；
- 宽代码依赖代码块内横向滑动，没有额外提示，当前不构成阻断。

**仍需后续处理：**

- fixture 503 恢复卡的泛化标题仍可能让 failed 与 interrupted 语义不够清楚，列入 P1 文案校准；
- 浏览器 composition 事件已覆盖，但实体安卓/iOS 输入法、软键盘安全区和真实触摸惯性仍需实机抽样；
- Firefox/WebKit 未进入当前门禁。

**P0-E2 结论：通过。** 当前 Chromium desktop、390×844 与定向 360×520 范围内，成功过程已经可查看、可度量、可人工复核。允许解冻真实 Provider AnswerClaim replay，但只能 record-only，不得直接接入生产 ChatTurn。

## 9. P0-E3：真实 Provider AnswerClaim replay（record-only）

### 9.1 第一切片：运行合同——已完成

PR #87 已建立以下合同：

```text
fixed 10-case K1 gold
-> production K1e real-provider answer replay
-> Provider-authored answer / assertions / cited_sources
-> immutable raw report
-> offline AnswerClaim adapter
-> AnswerClaimSnapshotV1 strict validation
-> record-only quality report
```

- 第二阶段不再次调用 Provider；
- 不从自然语言回答重新抽取或补写 claim；
- Provider assertion 映射为 `factual / asserted / provider_structured`；
- citation 映射为 strict known-evidence `direct_support` link；
- 保留最终回答换行用于稳定 `answer_hash`；
- 要求完整 10-case scope、零 failed case、Provider/model/endpoint fingerprints；
- 记录 source report fingerprint、latency、usage 与可选操作者核实的人民币成本；
- 未知 evidence、重复 claim、空最终回答等错误只暴露失败，不伪造补分；
- 手动 workflow 上传 K1e 与 AnswerClaim 两个 JSON artifact；
- CI #1680 通过 897 pytest、全部静态/前端/浏览器与 12/12 real-stack 门禁。

### 9.2 当前下一步：执行真实 replay

1. 明确一个仓库已配置 credential 的 Provider；
2. 明确 exact model name 与 pro/flash 档位；
3. 可选填写已核实的人民币成本，不得从 token 数猜测；
4. 手动执行 `.github/workflows/rag-provider-replay.yml`；
5. 下载并审查两个 artifact；
6. 至少重复运行，比较 claim coverage、unsupported claim、citation alignment、refusal leakage、latency、usage、成本与输出稳定性；
7. 根据失败分布决定先做 claim producer 改进，还是 RAG-K1f / K2。

在真实 artifact 产生前，不存在可报告的真实 AnswerClaim 模型指标。

## 10. P1 / P2 缺口

**P1：**

1. failed / interrupted 恢复卡文案语义校准；
2. 加强 GitHub replay 的 symbol mapping、CI association precision 和 partial-result 解释；
3. 补 multi-step research / cancel 的完整生命周期门禁；
4. 实体手机输入法、软键盘安全区与触摸滚动抽样。

**P2：**

1. 增加 Firefox/WebKit 兼容抽样；
2. 清理 README 中 Streamlit“已移除”与“兼容入口仍存在”的表述差异；
3. 继续校准 Golden Journey 指标，使点击、决策、surface、恢复能够跨用例比较。

## 11. 当前冻结与执行状态

- `main` 当前 P0-E3 replay 合同 merge SHA：`97bd0a02b6738d7d34aac112ccbc756a851bd14c`；
- PR #87 已 closed / merged，最终 feature head `1b86e92ce53b650139f4c80ea4e32e4cac41f77b`，CI #1680 完整全绿；
- 当前状态分支：`docs/p0-e3-contract-status`；
- 下一实现顺序：真实 record-only replay -> 重复稳定性 replay -> 结果分析 -> 决定 claim producer 或 RAG-K1f/K2；
- 真实 Provider replay workflow 需要 workflow_dispatch；当前连接器未暴露该写操作；
- 生产 claim producer、claim UI、生产 ChatTurn 接入、自适应 LearningPlan、G10-D 可执行代理继续冻结；
- 合并策略：独立小分支 -> Draft PR -> 完整门禁 -> 全绿合并。

## 12. 文档规则

- 当前状态只更新本文件；status-only 更新留在 active branch；
- `ARCHITECTURE_STATUS.md` 只维护稳定 owner/边界；`STATE_MODEL.md` 只维护稳定数据模型；
- 不新增并列长期状态文档；代码、CI、分支和 PR 变化必须同步本文件。

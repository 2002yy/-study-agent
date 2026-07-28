# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-07-28  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**P0-A1–P0-A8 与独立评估已进入 `main`；P0-E1 首个真实全栈切片已通过实现 head 全量门禁，正在状态同步后重跑最终 CI。**  
> 当前代码切片：`p0-e1/real-stack-browser-gates`，Draft PR #77。

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

## 2. 已完成主链

- TaskContract、LearningClosureRun、ThreadSummaryState、结构化恢复卡；
- RAG K1a-K1e、EvidenceSnapshot、ResearchRun source truth；
- AnswerClaimSnapshot v1 与 record-only 离线评测；
- 生产路径学习验证 E2E；
- desktop / 390px 五类 Golden Journey；
- 核心首屏按需加载与隐藏功能错误隔离；
- 资料与来源三层收口；
- 学习结束 review-first；
- desktop / mobile SessionNavigator 单一交互 owner；
- 新手入口与设置渐进披露；
- SlideOver 键盘焦点闭环、复制结果反馈、上传前置合同和窄屏/软键盘体验门禁。

已进入 `main`：

- PR #61 `597006e99919ea7e5f5b02f01b1536b446da9a55`，CI #1317；
- PR #62 `fcfb9bc66750d10c822306fae735424e658b19ef`，CI #1340；
- PR #63 `f1b2a4f9d481a16e5c93e6ac8fb4c0f9ee2f45c2`，CI #1357；
- PR #64 `451bc4a78fc3eda6219083371591aa46c8e62900`，CI #1368；
- PR #65 `b700da1a2751769959ae1b41966f5da0a854162a`，CI #1389；
- PR #66 `b1ac5a841aab5948b4fee623aeaea1d87e1b8af9`，CI #1407；
- PR #67 `c19d5070b9bcf73ed46a81731bbeae842b757208`，CI #1416；
- PR #68 `4da85690043e9144b18dabaf0b4d2359c16eaeb8`，CI #1437；
- PR #69 `04ac7d59c2f7ed76eee7192c3500ebbb6bc6d286`，CI #1449；
- PR #70 `ccdea493d8d0119e9ba0b9c203a06b5f14de1229`，CI #1462；
- PR #71 `cca4bdfac775909956f90aeaddc5bcfc96597e12`，CI #1481；
- PR #72 `3796bfe3bbc7c83feac9eeb9f195803a5ed57228`，最终 CI #1496；
- PR #73 `676fe23a0f26d500712b71c6e175d99d953f1e80`，最终 CI #1520；
- PR #74 `911e83769c1b53849fe21772099bec0323357180`，最终 head CI #1546；
- PR #76 `267969d92f0eaed4d6b2dc6b631a5380dd86f591`，最终 CI #1554。

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

## 4. P0-A1–P0-A4 已完成

- 真实 FastAPI -> ChatService -> TaskContract -> pedagogy -> SQLite -> SessionService 学习真值链已验证；
- 正确解释进入 committed truth，“懂了”、误解、semantic timeout 和非法 evidence ref 不推进；
- 首次问答、返回学习、503 恢复、资料学习、联网研究和源码学习在 desktop / 390px 全部通过；
- 首屏只依赖 `/health`、`/sessions`、`/runtime/settings`；隐藏模块按需加载；
- Sources 抽屉分为“本次回答依据 / 我的资料 / 检索诊断”，普通层只显示 adopted evidence。

## 5. P0-A5 / P0-A6 已完成

PR #72 在用户提交 `fae13fc90345a9147a3f08b9c8f156dc43300ab9` 基础上完成审计修正：

- closure 默认层的“本次确认 / 还需继续”优先读取 committed structured state，不把模型生成的 `progress` 候选直接包装成 committed truth；
- 建议下一步与保存范围继续读取冻结候选和 linked MemoryRun；
- Memory target、append/replace、refs、confidence 和 pending observation 留在高级明细；
- desktop sidebar 与 mobile drawer 共享一个 SessionNavigator interaction store；
- query、rename、group 和 archive-confirm state 不再分叉；
- 58 files / 205 Vitest、全部 desktop/390px Playwright journeys、pytest、RAG K1、Ruff、package、secrets、mypy、TypeScript 与 Vite build 全部通过。

## 6. P0-A7 已完成：新手与设置渐进披露

- 输入框继续承担默认直接问答，首次回答不要求先选模式；
- 新会话默认只显示“系统学习 / 上传资料”，联网研究和项目推进进入次级展开；
- 普通设置只显示学习方式、互动氛围、资料使用、联网/上下文隐私和默认值保存；
- 角色、强制角色、本会话微调、完整提示词、模型档位、上下文深度和检索参数进入高级设置；
- 未修改 TaskContract、ChatService 路由、设置 API 或恢复语义；
- CI #1512 只暴露测试适配问题；修复 cleanup、隐藏/可见断言和旧文案后，CI #1518 与最终 CI #1520 全绿；
- 59 files / 208 Vitest、TypeScript、Vite build 和 26 个 Playwright 用例全部通过；
- `progressive_onboarding` 在 desktop / 390px 均为 0 必需点击、0 配置决策、1 个 product surface、无横向溢出；
- `progressive_settings` 在 desktop / 390px 均为 3 次点击、0 配置决策、2 个 product surface、无横向溢出。

## 7. P0-A8 已完成并进入 main：焦点、反馈与窄屏体验

PR #74 已于 2026-07-28 squash merge，main commit 为 `911e83769c1b53849fe21772099bec0323357180`。实现 head `e3eb406c2e1c65da244dc797c212171a34fcb7fc` 的 CI #1544 与最终 status-sync head `31bd2ff17178eb60d7cc6e4cbb83763250f8126c` 的 CI #1546 均完整全绿。

### P0-A8.1 焦点与键盘

- `SlideOver` 打开后聚焦唯一关闭按钮；遮罩与关闭按钮使用不同可访问名称；
- Tab 从最后一个可交互元素回到第一个，Shift+Tab 反向循环，焦点不会逃出 dialog；
- 保留 Escape 关闭、背景滚动锁定和关闭后焦点返回原触发控件；
- Vitest 与 desktop / 390px Playwright 均覆盖 keyboard-only 路径。

### P0-A8.2 复制反馈

- 回答正文、中断回答、已采用证据和证据诊断四类复制入口均显示 success / failure 状态；
- Clipboard API 不可用或拒绝时，不再静默吞错；
- 可见按钮文案与 `aria-live` 状态同时反馈，且不暴露浏览器内部异常文本。

### P0-A8.3 上传约束与提示

- 前端单一合同与服务端当前约束一致：`.md`、`.markdown`、`.txt`、`.pdf`、`.docx`；
- 单文件上限 10 MiB，单批次上限 25 MiB；空文件、不支持类型、超限和混合无效批次在网络请求前整体拒绝；
- 文件选择器 `accept`、入口说明、前置校验和错误文案共用同一合同；
- 服务端继续负责 MIME、文件签名、UTF-8 和 DOCX 结构等权威校验，前端不伪装后端成功。

### P0-A8.4 触控、软键盘与窄屏

- 关键移动端交互目标达到至少 44px；
- 学习缺口、下一步、错误、会话、来源和上传说明允许换行，不再以单行 ellipsis 丢失关键内容；
- 动态 viewport、安全区、抽屉和 composer 布局加固；
- 390×520 模拟输入聚焦/软键盘收缩后，输入框与发送按钮仍在 viewport 内且可操作；
- desktop / 390px 所有新增与既有旅程均通过横向溢出检查。

### P0-A8 门禁结果

- CI #1538 暴露 SlideOver 两个关闭入口同名的真实可访问性歧义，产品代码修正为唯一关闭控件名称；
- CI #1542 已通过后端和 62 files / 217 Vitest、TypeScript、Vite build，并通过 32/34 浏览器用例；剩余 2 项仅为 Playwright 模糊定位同时命中背景按钮；
- CI #1544 在精确定位修正后完整全绿；
- 最终 status-sync head 的 CI #1546 再次完整全绿；
- pytest、RAG K1、Ruff、package、detect-secrets、expanded mypy、62 files / 217 Vitest、TypeScript、Vite build 和 34/34 desktop / 390px Playwright 全部通过；
- 新增浏览器门禁覆盖 SlideOver 焦点循环、无效上传不发请求、Clipboard 拒绝反馈、390×520 composer 可达、44px 触控目标和无横向溢出；
- 未修改学习真值、TaskContract、RAG 排序、Provider 行为、服务端上传策略或顶级产品表面。

## 8. 独立功能与使用体验评估结论

本轮独立检查覆盖当时 `main` 的架构 owner、持久化模型、生产路径测试、Playwright 旅程、CI #1546 及其浏览器/RAG 产物。评估后由 PR #76 将下一阶段收敛为 P0-E1 真实全栈门禁和 P0-E2 可审查体验证据。

### 8.1 成熟度判断

- **存在：通过。** 开始任务、持续学习、资料学习、联网研究、源码学习、理解验证、学习结束、刷新恢复和失败恢复均已有生产 owner 或明确的既有 owner 扩展边界。
- **可用：有条件通过。** 固定 fixture 旅程覆盖完整产品表面；P0-E1 第一切片进一步证明首次系统学习和理解验证可经过真实 React、FastAPI 与 SQLite。
- **稳定：在确定性测试条件下通过。** CI #1577 的 pytest、RAG K1、静态门禁、前端单测/构建、34/34 fixture Playwright 与 4/4 real-stack Playwright 全绿。
- **达到产品目标：仍未完全证明。** 首次学习与正确/空泛理解已有真实全栈证明，但上传解析/索引、closure、stream continuation、failed retry 和成功体验人工审查仍未完成；真实 Provider 教学与 claim 质量也尚未测量。

### 8.2 核心闭环逐项判断

| 闭环 | 当前结论 | 主要限制 |
|---|---|---|
| 首次开始 | 真实全栈第一切片通过 | desktop / 390px 均从 UI 进入 FastAPI、application service 与 SQLite，并通过刷新恢复 |
| 返回与持续学习 | 基础可用 | “继续这里”先填入提示，再由用户发送；尚未纳入真实全栈动作成本采集 |
| 上传资料学习 | 可用 | 浏览器层尚未走真实解析、revision、索引激活和失败不切换链路 |
| 联网研究 | 基础恢复可用 | multi-step research 与完整 cancel propagation 仍为 partial owner |
| 源码学习 | 展示与恢复可用 | GitHub replay 的 symbol mapping 与 CI association 精度仍不足以证明稳定理解源码关系 |
| 理解验证 | 首个真实全栈切片通过 | 空泛“懂了”明确 reject 且不进入 transfer；正确推理进入 committed truth 并刷新恢复；真实 Provider 质量尚未测量 |
| 学习结束 | review-first 与 hash-confirm 边界成立 | 浏览器旅程尚未覆盖保存后刷新、重新进入和长期记忆实际恢复 |
| 刷新/失败/中断恢复 | 首次学习刷新恢复已通过 | 仍缺同一真实全栈运行中的 interruption continuation 与 failed retry 证明 |

### 8.3 P0 评估缺口

这些不是“再加一个功能”的 P0，而是决定现有功能能否被认定为真实可用的证据缺口。

#### P0-E1：真实全栈确定性浏览器门禁

已完成第一切片：

- CI 同时启动 React/Vite、FastAPI/Uvicorn 与临时 SQLite；
- 浏览器不通过 `page.route` 伪造核心业务 API；只有 Provider、Memory、RAG 和外部网络 gateway 使用服务端 deterministic fake；
- desktop / 390px 覆盖首次系统学习、SQLite durable truth、刷新恢复、空泛理解 reject、正确推理 commit 与再次刷新恢复；
- 浏览器展示、服务端状态、SQLite truth 和重新加载结果一致；
- 全量既有门禁没有回退。

剩余切片：

1. 真实文件上传 -> 解析 -> revision -> 索引激活 -> 基于资料开始学习；
2. learning closure preview -> hash-confirm commit -> 刷新/归档/重新进入；
3. stream interruption -> continuation，确保 partial 不覆盖 committed truth；
4. failed turn -> retry -> parent superseded，确保只提交一次；
5. 在现有 WebLookup owner 上补必要的真实研究恢复链路，不扩张第二套研究系统。

#### P0-E2：可审查的成功体验证据

- 对选定的绿色 Golden Journeys 保留关键步骤截图，而不是只在失败时保留 trace/screenshot/video；
- 点击、键盘操作、发送、滚动、surface 切换和恢复动作由测试辅助层实际采集，不再由用例手写常量；
- `product_surfaces` 不只统计 `main` 与 dialog，还要反映抽屉、恢复卡、上传承接、证据层和 closure review；
- 加入 360px/窄高度、长中文、长代码块、输入法 composition 和真实滚动位置检查；
- 完成一次基于成功产物的人工试玩记录，专门识别“功能正确但难以理解或推进”的问题。

### 8.4 P1 / P2 缺口

**P1：**

1. P0-E1 / P0-E2 通过后，解冻真实 Provider AnswerClaim replay，但保持 record-only，不接生产 ChatTurn；
2. 根据真实 replay 暴露的问题决定先做 claim producer 还是 RAG-K1f / K2，不能依据 deterministic gold producer 的 1.0 自测分数直接接生产；
3. 加强 GitHub replay 的 symbol mapping、CI association precision 和 partial-result 解释，再讨论源码学习的自动推进；
4. 补 multi-step research/cancel 的完整生命周期门禁。

**P2：**

1. 增加 Firefox/WebKit 与更小宽度的兼容抽样，但不把浏览器矩阵扩张为当前 P0；
2. 清理 README 中 Streamlit“已移除”与“兼容入口仍存在”的表述差异，再决定 legacy 代码删除；
3. 校准 Golden Journey 指标定义，使“点击、决策、surface、恢复”能够跨用例稳定比较。

## 9. P0-E1 第一切片实现结果

PR #77 在不接真实外部 Provider 的前提下建立了首个真实组合门禁：

```text
Playwright browser
-> Vite proxy
-> production FastAPI routes
-> ExternalDataPolicyChatService / TaskContract / pedagogy
-> production SQLite repositories
-> session reload and UI restoration
```

- 新增 `tools.real_stack_test_server`，只替换外部模型、Memory、RAG 与网络 gateway；生产 route、application service、transaction 和 repository 继续执行；
- 新增独立 Playwright real-stack 配置，同时启动 Uvicorn 与 Vite；默认 fixture 套件明确排除该 spec，避免两套 owner 混跑；
- 每个用例通过 test-only reset 清空临时数据库、WAL/SHM 和导出目录，desktop / mobile 不共享残留状态；
- 2 条旅程在 desktop / 390px 各执行一次，共 4/4：首次学习并刷新；空泛理解 reject 后正确推理 commit 并刷新；
- CI #1577 的 real-stack 日志为 `4 passed (11.8s)`，同时全部既有门禁全绿。

真实全栈门禁还暴露并修复了一个此前 fixture 隐藏的生产缺口：`TaskContract` 已识别 `learn`，但“带我系统学习……”在自动学习方式下仍可能被通用路由选为“普通”，从而只进入 `direct_answer`，没有建立学习目标。当前新增高优先级 `system_learning` 路由规则，使自动方式进入苏格拉底协议；用户显式选择“直接讲解”时仍保留“普通”，没有剥夺手动控制。

边界：

- 本切片没有接入真实 Provider、Embedding 或外部网络；
- 没有修改 AnswerClaim 生产接入、RAG 排序、Memory 写入合同或新建顶级产品表面；
- 这只是 P0-E1 第一切片，不代表整个真实学习闭环已经封板。

## 10. 评估后的阶段决策

1. **P0-E1 第一切片已通过实现 head 门禁，并修复了一个真实默认路由 P0 缺口。**
2. **暂不宣布产品闭环完成。** 下一顺序为 P0-E1 上传/closure 切片 -> interruption/retry 切片 -> P0-E2 可审查体验证据。
3. P0-E1 / P0-E2 全部通过后，下一项才解冻真实 Provider AnswerClaim replay；首次运行只产出基线、错误样本、延迟和成本，不修改生产 prompt、ChatTurn 或学习真值。
4. 生产 claim producer、claim UI 在真实 replay 证明 schema、claim/evidence link 和 leakage 质量前继续冻结。
5. 自适应 LearningPlan 与 G10-D 可执行代理继续冻结；当前系统最缺的仍不是更多自动规划，而是对现有闭环的真实证明。
6. 若 Provider replay 显示主要失败来自检索或证据供给，先推进 RAG-K1f / K2；若检索充足而 claim 提取失败，再推进 producer。不得并行扩张两条生产路径。

## 11. 下一阶段完成标准

- 浏览器通过真实 FastAPI 与临时 SQLite 完成核心学习闭环，核心业务 API 无 `page.route` fixture；
- 至少一条正确理解和一条错误/空泛理解从 UI 发起，并在刷新后验证 committed truth；
- 上传、研究、closure、interruption 和 retry 的 UI、API、durable state 与恢复结果一致；
- 选定成功旅程有可查看截图与实际采集的操作指标；
- desktop、390px、360px/窄高度无关键文本截断、横向溢出或 composer 不可达；
- 人工试玩明确记录阻断、困惑点和可接受项；
- 全量既有 CI 不回退；评估结论再次写回本文件后，才允许解冻 Provider replay。

## 12. 当前冻结与执行状态

- `main` 当前独立评估 merge SHA：`267969d92f0eaed4d6b2dc6b631a5380dd86f591`；
- PR #76 已 closed / merged，CI #1554 完整全绿；
- 当前实现分支：`p0-e1/real-stack-browser-gates`，Draft PR #77；
- 实现 head `e7d695cc89f029c3edfc2c03c54dbd2948a598b0` 的 CI #1577 完整全绿；
- 当前状态同步提交后必须对最新 head 重跑完整 CI，未全绿前 PR #77 保持 Draft；
- 下一实现顺序：真实上传/索引与 closure -> interruption continuation 与 failed retry -> P0-E2；
- 真实 Provider claim replay 在 P0-E1 / P0-E2 通过前继续冻结；
- 生产 claim producer、claim UI、Streamlit 清理、RAG-K1f、RAG-K2、自适应 LearningPlan、G10-D 可执行代理继续冻结；
- 合并策略继续保持：独立小分支 -> Draft PR -> 完整门禁 -> 全绿合并。

## 13. 文档规则

- 当前状态只更新本文件；status-only 更新留在 active branch；
- `ARCHITECTURE_STATUS.md` 只维护稳定 owner/边界；`STATE_MODEL.md` 只维护稳定数据模型；
- 不新增并列长期状态文档；代码、CI、分支和 PR 变化必须同步本文件。

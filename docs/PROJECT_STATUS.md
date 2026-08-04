# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-08-04  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**停止横向扩张，集中梳理核心学习功能、产品入口、运行状态与桌面/移动端体验。**  
> 冻结边界：**Provider replay 扩展、生产 claim producer / claim UI、生产 ChatTurn 接入、群聊能力扩张、新闻产品化与可执行 agent 均不是当前开发主线。**  
> 当前切片：**Draft PR #97 已完成研究产品表面和前端 wiring 的第一轮收拢；完整 CI 尚未确认，后端 NewsRun / ResearchRun owner 未改，下一步是 operation scope 合同。**

本文件只维护当前事实、可复核证据、缺口和执行顺序。不得新增并列长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT 文档。

## 1. 产品边界

```text
当前目标
-> 教学 / 练习
-> 资料与证据
-> 理解验证
-> 已确认 / 未解决
-> 下一步
-> 整理、恢复与继续学习
```

- React 是当前产品交互面；FastAPI 提供生产路由与应用服务；SQLite durable entities 是运行真值。
- RAG 服务于围绕用户自己的资料学习；Web Research 服务于需要外部事实的学习任务。
- GitHub 是源码学习证据来源，不是第二个顶级工作台。
- Memory 是学习连续性基础设施；Workflow 只属于高级诊断。
- planned / attempted / partial / failed 不得覆盖 committed learning truth。
- 当前冻结横向功能扩张，以主学习闭环是否清晰、可恢复、可验证、可在窄屏操作为判断标准。

### 1.1 功能集中化目标

普通用户最终只需要理解四个稳定入口：

1. **学习会话**：提问、教学、练习、理解验证和恢复；
2. **资料与来源**：上传资料、本次回答依据、联网来源和检索诊断；
3. **学习成果**：本次收束、确认写入、归档与继续；
4. **设置**：学习方式、资料使用、外部数据策略和少量高级参数。

实验能力统一降级到单一“实验室”边界；群聊、手动工具和开发者诊断不再与主学习闭环争夺同等入口。新闻不作为独立顶级产品，而是联网研究的一种时效性预设。

## 2. 当前核心功能基线

- 当前核心功能基线 SHA：`9e0adb8c6833b4e1733dfb897d5fc7a92c9df5ab`；
- PR #92：修复失败刷新恢复与长会话恢复入口，merge SHA `47d252e0bd33126022d76de324af8d67e62dac5e`；
- PR #93：修复联网研究取消状态收口，merge SHA `b4a996bbed74beca5a861490e39b4b67d4abc8b5`；
- PR #96：解释联网研究阶段与 partial 结果使用边界，merge SHA `a2eed731037f7dfa6970a26cf9f65a53fb919206`；
- 核心架构精简与 CI 修复：删除旧 Streamlit 入口、收紧依赖与打包边界，并修复真实全栈 RAG 路径、查询规划和测试状态隔离，SHA `9e0adb8c6833b4e1733dfb897d5fc7a92c9df5ab`；
- 当前基线 GitHub Actions run `30826682687` 已全绿；本轮 PR #97 的门禁结果尚未写入事实基线。

## 3. 已验证的产品闭环

| 闭环 | 当前结论 | 真实证据边界 |
|---|---|---|
| 首次开始 | 真实全栈通过 | React -> FastAPI -> SQLite；无需先做配置决策 |
| 返回学习 | 可恢复并继续 | 恢复目标、上下文和下一步，继续后刷新仍一致 |
| 上传资料学习 | 真实全栈通过 | 文件合同、解析、document/revision、索引、EvidenceSnapshot、刷新恢复 |
| 联网研究 | 取消与恢复闭环通过 | 慢研究 -> 请求取消 -> durable `cancelled` -> 刷新 -> 同 run 从 checkpoint 重试完成 |
| 源码学习 | 展示与恢复可用 | symbol mapping 与 CI association 精度仍不足以证明稳定源码关系理解 |
| 理解验证 | 真实全栈通过 | 空泛“懂了”不提交；正确推理才进入 committed truth 和 transfer |
| 学习结束 | 真实全栈通过 | closure preview、确认写入、summary、刷新、归档并新建 |
| 中断续写 | 真实全栈通过 | partial 保存为 `interrupted`；刷新后同 turn 续写；前缀不重复；只提交一次 |
| 零 token 失败 | 真实全栈通过 | `failed` 刷新后仍可重新生成；retry child 完成后 parent `superseded` |
| 长会话恢复 | desktop / 390×844 / 360×520 通过 | 恢复卡位于当前 conversation viewport，不再落在历史顶部 |
| 窄屏复杂内容 | 360×520 通过 | 长中文、长 URL、宽代码、IME、真实滚动、回到最新与刷新恢复 |

## 4. 功能集中化与体验审计

### 4.1 已经稳定、应当保护的骨架

- `RestoreCard` 已覆盖新用户、返回学习、失败重试和中断续写；
- `LearningStrip` 已把目标、阶段、缺口、下一步和验证状态压缩到会话顶部；
- 上传资料后会回到“系统学习 / 直接提问”，而不是把用户丢进资料管理页；
- `SourcesPanel` 已分成“本次回答依据 / 我的资料 / 检索诊断”，并区分候选资料与实际回答依据；
- 学习结束经过 closure preview、用户确认和 hash-locked MemoryRun 后才写入；
- durable run、刷新恢复、窄屏、IME 和复杂内容已有强回归门禁。

上述能力不是本轮重构对象；任何集中化修改不得改变其 committed truth、持久化和恢复合同。

### 4.2 P0：新闻与联网研究形成用户可见双轨

原产品表面同时存在：聊天内可恢复 ResearchRun、独立 NewsWorkspace，以及群聊内嵌的第二份 NewsWorkspace。用户面对近似入口，内部则由 NewsRun 与 WebLookup/ResearchRun 两套 durable run 承担。

目标用户模型统一为：

```text
提出需要外部事实的问题
-> 自动判断或显式选择联网研究
-> ResearchRun 搜索、阅读、筛选、恢复
-> 证据进入“资料与来源”
-> 继续单人学习，或将已确认结果交给群聊讨论
```

本轮采用分层收拢：先删除重复产品入口和 wiring，不同时删除后端兼容能力或迁移 durable entity。

### 4.3 P0：Workspace 仍是总线式集中

`App.tsx` 已是 composition-only，但 `WorkspaceRuntime`、`useWorkspaceControllers` 与 `WorkspaceView` 仍共同承载聊天、RAG、上传、研究、新闻、群聊、工具、记忆、诊断、多个本地设置和多类 run ID。

目标边界：

```text
LearningSessionRuntime
  -> chat / sessions / pedagogy / recovery / closure

EvidenceRuntime
  -> upload / RAG / research / GitHub evidence / sources

ExtensionRuntime
  -> group chat / legacy news / controlled tools / workflows
```

先通过产品入口收拢降低交叉面，再拆运行时；不在同一批同时改变前端 owner 和后端 durable entity。

### 4.4 P0：会话切换与 operation scope 合同需复核

`START_NEW_CHAT_SESSION` 当前会清除 NewsRun、WebLookupRun、ToolRun、MemoryRun、LearningClosureRun、RAG query 和 RAG write ID；但稳定原则要求普通会话切换不能全局取消无关 operation scope。

待补合同：

- 新建聊天必须清除聊天消息、当前摘要、学习阶段和会话 closure；
- 独立资料上传、独立研究和诊断运行不得仅因切换会话而丢失；
- 只有明确绑定当前 session/turn 的 run 才随会话切换收口；
- reducer 清 ID、浏览器请求中止和服务端 cancel 必须分别建模，不能互相冒充。

### 4.5 P1：普通用户可见系统能力过多

目标是普通模式仅保留会话历史、资料与来源、学习成果和设置；群聊、手动工具和开发者诊断统一进入实验室，并默认不加载。

### 4.6 P1：学习成果与手动长期记忆管理混层

默认学习结束流程只应回答“本次学了什么、确认了什么、还有什么不会、下一步是什么、将写入什么”。七类长期记忆目标、手动候选编辑、替换/追加和置信度明细应降到高级管理区。

### 4.7 P1：样式 owner 分散

当前同一组件的桌面、移动端、恢复、渐进披露和产品边界规则散落在多个按历史整改批次命名的 CSS 文件中。后续按组件迁移样式 owner；全局只保留 token、reset、accessibility 和应用布局基线。

### 4.8 P2：兼容债务

- CORS 当前由 `CORSMiddleware` 和手写安全中间件共同处理，应统一 owner；
- deprecated / 410 路由仍挂载在生产 app，应在替代覆盖稳定后逐批删除；
- `Sidebar` 兼容别名和 SettingsPanel 未使用 props 应清理；
- `selectedPanel` 等不再对应当前抽屉式 UI 的状态应删除；
- Firefox、WebKit 和实体手机仍需要抽样。

## 5. 当前执行切片：P0-R2 研究产品表面收拢

- 分支：`agent/research-experience-consolidation`
- Draft PR：`#97 收拢联网研究与新闻入口`
- 当前状态：代码已提交到分支；完整 CI 尚未确认，不能标记完成或合并。

### 5.1 已完成

1. 从普通“更多”菜单移除独立“新闻研究”入口；
2. 删除 `WorkspaceView` 中独立新闻抽屉；
3. 群聊不再嵌入完整 `NewsWorkspace`；
4. 从 `WorkspaceView -> WechatPanel` wiring 删除 NewsController、新闻查询、正文读取和搜索/停止回调；
5. 从 `WechatPanel` 公共 props 删除上述遗留依赖；
6. 保留群聊对已经存在的 ResearchRun 结果进行只读展示和显式使用选择；
7. 更新 ChatPanel 产品边界测试，并新增 WechatPanel 产品边界测试。

### 5.2 明确保留、未改动

- NewsRun、NewsWorkspace 和新闻 API 仍保留为兼容/实验能力；
- ResearchRun 数据模型、数据库、checkpoint、取消、恢复和 retry 语义未改；
- partial 研究结果仍不会自动进入下一轮聊天；
- RestoreCard、LearningStrip、SourcesPanel、RAG、MemoryRun 和学习结束 committed truth 未改；
- `WorkspaceRuntime` 中仍存在 NewsController、news query、readArticles 和 active NewsRun ID，等待确认无剩余产品调用者后再清理。

### 5.3 待完成

1. 等待并检查 PR #97 的前端单元测试、TypeScript/Vite build、浏览器门禁和后端全量门禁；
2. 若门禁发现旧旅程仍依赖新闻抽屉，修正测试建模而不是恢复重复产品入口；
3. 增加 operation scope reducer 合同，明确新建会话应保留哪些独立 run；
4. 依据合同修复 `START_NEW_CHAT_SESSION` 的误清理风险；
5. 再清理 WorkspaceRuntime / useWorkspaceControllers 中无产品调用者的 NewsRun 状态和控制器；
6. 最后决定 NewsRun 后端是保留为实验 adapter，还是迁移为 ResearchRun 的新闻预设。

### 5.4 验收标准

- 普通用户只理解一个“联网研究”概念；
- 聊天研究仍可取消、刷新恢复、重试和显式用于下一轮聊天；
- 群聊不自行创建第二套研究真值；
- 新会话不会误清理无关资料写入或独立研究；
- desktop、390×844、360×520 核心旅程不退化；
- TypeScript build、前端单元测试、fixture/narrow journey 和相关 real-stack journey 通过。

## 6. 最近核心修复

### 6.1 失败刷新恢复与长会话入口

PR #92 修复 failed/interrupted 语义、零 token retry-only、恢复卡视口位置和 360×520 短屏可见性；后端 durable status 与 committed learning truth 未改变。

### 6.2 联网研究取消与 partial 结果解释

PR #93 让取消等待 durable 终态并支持刷新后同 run 重试；PR #96 明确 partial 结果不会自动进入聊天，可由用户显式选用或重试补全。

### 6.3 核心架构精简

- 删除旧 Streamlit 展示层和依赖；
- React + FastAPI 成为唯一产品运行时；
- 修复 RAG 隔离路径、查询规划、真实全栈 reset 和测试状态污染；
- 当前基线已通过全量 pytest、RAG K1、Ruff、打包、detect-secrets、mypy、前端构建与浏览器门禁。

## 7. 当前质量门禁

当前核心基线 `9e0adb8` 的 GitHub Actions run `30826682687` 已完整通过：

- 全量 pytest；
- RAG K1 固定 corpus 基线；
- Ruff、项目打包检查、detect-secrets；
- expanded mypy baseline；
- 前端单元测试、TypeScript 与 Vite production build；
- 38 条 Chromium fixture / narrow Golden Journeys；
- desktop 与 390×844 专用真实全栈浏览器门禁。

测试边界：

- 浏览器门禁替换外部模型、搜索或文件来源时，仍保留生产 route、application service、transaction 和 repository；
- real-stack 核心 API 不使用 `page.route` 伪造；
- 每个真实旅程使用隔离的临时 SQLite、RAG、memory 和输出目录；
- 失败必须暴露真实产品或测试建模问题，不通过降低断言强行变绿。

## 8. 当前真实指标

### RAG K1 固定回归

- 12 documents；30 retrieval cases / 26 answerable；10 answer-quality gold；
- source recall@K `0.923077`；nDCG `0.903600`；adaptive recall@K `0.942308`；
- multi-source recall@K `0.9`；stale / forbidden leakage `0`；
- deterministic answerable `26/26`；unanswerable block `4/4`。

这些数字只代表固定 corpus 回归合同，不代表真实模型最终回答质量。

### 成功体验证据

- 23 张已保留的真实 viewport PNG：desktop 1440×900 共 9 张、mobile 390×844 共 9 张、narrow 360×520 共 5 张；
- 360×520 对话可视高度 251px；
- 真实 wheel 滚动后距底部 700px；“回到最新”和刷新后均恢复到 0；
- 宽代码只在代码块内部横向滚动；长 URL 在消息边界内换行；
- 浏览器 composition 事件验证：组合期间 Enter 不提交，composition end 后只提交一次。

### 仍属冻结的评测能力

仓库中仍保留 record-only AnswerClaim real-provider replay 与方舟 smoke/full 运行合同，但尚未执行实际 real-provider artifact；不得报告不存在的真实 coverage、alignment、latency、usage 或成本数字。

## 9. 后续优先级

**P0：产品与状态真值**

1. 完成 PR #97 门禁并收口研究产品表面；
2. 补齐 operation scope 合同并修复会话切换误清理风险；
3. 清理剩余 NewsRun 前端运行状态；
4. 将 Workspace 总线拆成 Learning / Evidence / Extension 三个运行时边界。

**P1：核心体验**

1. 压缩普通用户功能入口，建立单一实验室；
2. 拆分“本次学习成果”和“长期记忆高级管理”；
3. 继续逐批检查首次学习、返回学习、上传资料、理解验证和学习结束的真实交互细节；
4. 加强源码学习 symbol mapping、CI association precision 与 partial-result 用户解释；
5. 对实体安卓/iOS 输入法、软键盘安全区、触摸惯性和返回键做实机抽样。

**P2：维护与兼容性**

1. 样式按组件 owner 收拢；
2. 统一 CORS owner，逐批移除 410 / deprecated 路由；
3. 清理 Sidebar 兼容别名、未使用 props 和残留 reducer state；
4. 增加 Firefox / WebKit 兼容抽样；
5. 继续统一 Golden Journey 的点击、决策、surface、恢复和耗时指标。

## 10. 执行规则

- 只从 Study Agent 核心学习流程出发选择下一批，不因为仓库已有实验合同就继续扩张；
- 优先级：阻断 -> 高频体验问题 -> 状态真值错误 -> 可维护性 -> 低频兼容性；
- 每批使用独立小分支 -> Draft PR -> 完整门禁 -> 全绿合并；
- 新功能或修复必须同时给出单元、真实全栈或人工验收边界；
- 不报告未实际运行的 Provider 指标，不把 deterministic / synthetic 结果冒充真实模型质量；
- 产品表面、前端 owner 与后端 durable owner 分批收拢，避免一次改动同时破坏多个稳定边界。

## 11. 文档规则

- 当前状态只更新本文件；
- `ARCHITECTURE_STATUS.md` 只维护稳定 owner / 边界；
- `STATE_MODEL.md` 只维护稳定数据模型；
- 不新增并列长期状态文档；代码、CI、分支和 PR 变化必须同步本文件。

# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-08-05  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**按 Learning / Evidence / Extension 三个领域收口运行时 owner，并保护真实持久化、恢复、学习结束与窄屏闭环。**  
> 当前切片：**Draft PR #106 已把 active session、summary 合并、新建确认、中断放弃与 pedagogy phases 收口到 LearningSessionRuntime view model；代码基线 CI run `30987459136` 全绿。**  
> 冻结边界：**Provider replay 扩展、生产 claim UI、群聊能力扩张、新闻产品化和可执行 agent 均不是当前开发主线。**

本文件只维护当前事实、可复核证据、缺口和执行顺序。不得新增并列长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT 文档。

## 1. 产品与真值边界

```text
教学 / 练习
-> 资料与证据
-> 理解验证
-> 已确认 / 未解决
-> 下一步
-> 整理、恢复与继续学习
```

- React 是当前交互面；FastAPI 提供生产路由与应用服务；SQLite durable entities 是运行真值。
- RAG 服务于用户自己的资料；Web Research 服务于外部事实学习。
- GitHub 是源码学习证据来源，不拥有第二套前端 runtime 或 durable entity。
- planned / attempted / partial / failed 不得覆盖 committed learning truth。
- 普通用户最终只保留学习会话、资料与来源、学习成果、设置四个稳定入口。

## 2. 已合并主线

- 核心真实全栈基线：`9e0adb8c6833b4e1733dfb897d5fc7a92c9df5ab`；
- PR #97：联网研究产品表面集中化，merge SHA `3b1b9ef92c0496a659e2be3bf6075d529eb01826`；
- PR #98：主工作区遗留 NewsRun 状态清理，merge SHA `6b357bfe3b63d072f9374f19e149866171145b7a`；
- PR #99：前端兼容壳与无效设置合同清理，merge SHA `04770915e08528cb639edeba9839223072340f61`；
- PR #100：NewsWorkspace / NewsController 删除与 NewsRun 兼容边界，merge SHA `42ed5fdf01f25dd56f68215ac034f77bd117bb9d`；
- PR #101：EvidenceRuntime 第一批 owner 抽离，merge SHA `a5db630c1758cbb5019b6fc035c90d26cf54ec05`；
- PR #102：Evidence recovery port 与源码证据 owner 边界，merge SHA `d3da42dec0298138a48902cce860fc15f19eb808`；
- PR #103：单一 activeQuery 跨域 selector，merge SHA `22d3d0f562ed4a92b324c0f0d2c426332e8a2e47`；
- PR #104：LearningSessionRuntime 第一批 owner，merge SHA `b98a777f98e309b41a964c45c1c54c5ca0a54386`；
- PR #105：LearningSessionRuntime chat/session owner，merge SHA `43f6cfbada931ccbf58712c995dbd087f7e19048`。

## 3. 当前待合并切片

- 分支：`agent/learning-session-view-model`；
- Draft PR：`#106 收口 LearningSessionRuntime 会话派生视图`；
- base：`main` at `d8b6aba970c982c6444f72c34cdc0296e219bdcc`；
- 代码基线：`63224367f13551762fbf214f5388d8db41f104cd`；
- 代码基线 CI：run `30987459136`，结论 `success`。

## 4. 必须保护的稳定闭环

| 闭环 | 当前结论 | 真实证据边界 |
|---|---|---|
| 首次开始 | 真实全栈通过 | React -> FastAPI -> SQLite；无需先配置 |
| 返回学习 | 可恢复并继续 | 目标、上下文、设置、run ID、消息与下一步恢复 |
| 上传资料学习 | 真实全栈通过 | 文件合同、索引、EvidenceSnapshot、刷新恢复 |
| 联网研究 | 取消与恢复通过 | durable ResearchRun、同 run 重试与恢复 |
| 源码学习 | 展示与恢复可用 | 通用 EvidenceSnapshot / EvidenceTrail |
| 理解验证 | 真实全栈通过 | 正确推理才进入 committed truth |
| 学习结束 | 真实全栈通过 | closure preview、确认写入、summary、归档并新建 |
| 中断续写 | 真实全栈通过 | partial 保存、同 turn 续写、只提交一次 |
| 长会话与窄屏 | desktop / mobile / 360×520 通过 | 恢复卡、宽代码、IME、滚动、刷新恢复 |

必须继续保护：`RestoreCard`、`LearningStrip`、`SourcesPanel`、MemoryRun、ResearchRun、RAG query/write run、WorkspacePersistence v4 和学习结束 committed truth。

## 5. 当前运行时 owner

### EvidenceRuntime

`useEvidenceRuntime` 集中拥有 RAG settings/enabled、RagQueryRun、RagWriteRun、ResearchRun、RAG/上传/联网研究 controller、Sources 实际加载和 `EvidenceRecoveryPort`。

为 Learning chat 提供窄 `EvidenceLearningPort`，只暴露聊天所需的 RAG 与联网研究依赖，不把 Evidence controller owner 迁入 Learning。

### LearningSessionRuntime

`useLearningSessionRuntime` 集中拥有：

- `chatSettings`、角色保持与会话指令；
- MemoryRun、LearningClosureRun 与 `useMemoryController`；
- 唯一生产 `useChatController`；
- chat/session 消息、thread、lastChat、stream recovery 与发送状态；
- `LearningRecoveryPort`；
- 跨域清理窄端口 `LearningArtifactPort`；
- 学习会话派生 `view`。

`useWorkspaceControllers` 不再构造 ChatController / MemoryController；`WorkspaceView` 不再现场推导学习会话状态。

## 6. PR #106：学习会话派生 view model

### 6.1 纯 selector

`frontend/src/app/learningSessionViewModel.ts` 统一定义：

```text
selectActiveLearningSession()
selectLearningSessionSummary()
selectNewSessionConfirmation()
```

规则保持不变：

- 当前 thread 匹配唯一 active session；没有 thread 时返回 `null`；
- server summary 为 `not_summarized` 时，同 thread 且更新的本地 summary 优先；
- 其他 thread 的本地 summary 不得泄漏到当前会话；
- 只有出现用户消息时，新建会话才弹确认；
- 已整理与未整理的两段确认文案逐字保持不变。

### 6.2 LearningSessionRuntime view

Learning runtime 暴露单一 view model：

```text
activeSession
sessionSummary
sessionId
isSending
streamRecovery
visitedPhases
requestNewSession()
abandonRecovery()
```

其中：

- `requestNewSession()` 负责既有确认语义并调用唯一 ChatController；
- `abandonRecovery()` 负责 interrupted-turn abandon API、恢复卡清理、刷新与错误反馈；
- 缺少 session/turn ID 的恢复记录只清本地恢复卡，不发无效请求；
- pedagogy phases 只通过 learning view 向 `LearningStrip` 暴露。

### 6.3 WorkspaceView 收口

WorkspaceView 已删除：

- `snapshot.sessions.find(...)`；
- server/local summary 现场合并；
- `requestNewSession` 现场实现；
- `abandonInterruptedTurn` import 与 `abandonRecovery` 现场实现；
- 对 `state.pedagogyPhases` 的学习域直读。

它只负责把 `learningView` 绑定到 `SessionNavigator`、`ChatPanel`、`LearningStrip`、`SettingsPanel` 和 `MemoryPanel`。

### 6.4 兼容边界

- 确认文案与触发条件不变；
- session/turn/recovery API 不变；
- WorkspacePersistence schema 仍为 v4；
- localStorage 字段名不变；
- SQLite schema 与 durable entity 不变；
- MemoryRun、closure 与 committed learning truth 不变；
- UI 布局与普通用户入口不变。

## 7. PR #106 验证证据

代码基线 commit `63224367f13551762fbf214f5388d8db41f104cd` 的 CI run `30987459136` 完整通过：

- 全量 pytest；
- RAG K1 固定 corpus；
- Ruff；
- 项目打包；
- detect-secrets；
- expanded mypy baseline gate；
- 69 个前端测试文件、250 项测试；
- TypeScript / Vite production build；
- 38 条 desktop、mobile、360×520 Golden Journeys；
- 真实 FastAPI + SQLite 浏览器门禁。

说明：raw expanded mypy 仍有既有存量错误；baseline 为 current=125、baseline=127、resolved=2，未宣称 raw mypy 全量清零。

### 受控失败记录

- CI `30986833827`：新增边界测试按预期失败，证明 selector、summary、确认与 abandon owner 仍在 WorkspaceView；其他前置门禁通过。
- CI `30987103482`：69/69 前端测试文件、249/249 测试通过；TypeScript 发现无 active thread 时 selector 参数类型过窄。
- commit `63224367f13551762fbf214f5388d8db41f104cd` 将 thread 参数改为可空并补无 thread 单测，随后完整 CI 全绿。

这些修正没有放宽 owner、确认、恢复、持久化或产品行为边界。

## 8. 下一执行顺序

### P1-R5：抽离 ExtensionRuntime

```text
ExtensionRuntime
-> group chat / controlled tools / workflows / compatibility adapters
```

第一批先盘点并迁移：

- `useGroupChatController` 与 group thread 派生/恢复；
- `useToolController` 与 ToolRun ID；
- `useWorkflowController`；
- extension drawer lazy-load；
- 与 WorkspaceCoordinator 的 cancel / clear 窄端口。

不得把 Evidence、Learning、普通设置或 durable truth 搬入 ExtensionRuntime。

### P1-R6：普通模式与单一实验室入口

普通模式只保留学习会话、资料与来源、学习成果、设置。群聊、工具和开发者诊断进入单一实验室，默认不加载。

### 剩余债务

- GitHub symbol mapping 与 CI association 增强，但继续写入通用 EvidenceSnapshot；
- 删除 NewsWorkspace 遗留无 owner CSS selector；
- CORS 统一为单一 owner；
- 410 tombstone 只在迁移窗口结束后单独删除；
- 补 Firefox、WebKit 和实体手机抽样。

# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-08-05  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**按 Learning / Evidence / Extension 三个领域收口运行时 owner，并保护真实持久化、恢复、学习结束与窄屏闭环。**  
> 当前切片：**Draft PR #107 已抽离 ExtensionRuntime 第一批 owner；代码基线 CI run `30994619469` 完整通过。**  
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
- PR #105：LearningSessionRuntime chat/session owner，merge SHA `43f6cfbada931ccbf58712c995dbd087f7e19048`；
- PR #106：LearningSessionRuntime 会话派生 view model，merge SHA `761ea7634c97b71de7f40eed15ab0b52229631c1`。

## 3. 当前待合并切片

- 分支：`agent/extension-runtime-foundation`；
- Draft PR：`#107 抽离 ExtensionRuntime 第一批 owner`；
- base：`main` at `f60e93d8285c204be69cbe2d5f5f49429817d156`；
- 代码基线：`36d9cef3dfb611313a967574889601433ff68cc7`；
- 代码基线 CI：run `30994619469`，结论 `success`。

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

### ExtensionRuntime

`useExtensionRuntime` 第一批集中拥有：

- 唯一生产 `useGroupChatController`；
- 唯一生产 `useToolController`；
- 唯一生产 `useWorkflowController`；
- group thread 与 ToolRun ID；
- `ExtensionRecoveryPort`；
- group / tools / timeline drawer 数据加载；
- 单一 `activeQuery` 派生及 Tool invocation；
- `ExtensionCoordinatorPort` 的 group cancel、tool invalidate、ToolRun clear 与 workflow clear。

`WorkspaceCoordinator` 仍是跨域协调 owner，只消费 ExtensionRuntime 的窄端口；Memory drawer、Learning、Evidence、普通设置和 durable truth 未迁入 ExtensionRuntime。

## 6. PR #107：ExtensionRuntime 第一批 owner

### 6.1 controller owner

原先由 `useWorkspaceControllers` 直接构造的三个扩展 controller 已迁入：

```text
useExtensionRuntime
-> useGroupChatController
-> useToolController
-> useWorkflowController
```

`WorkspaceRuntime` 只构造一次 ExtensionRuntime；`useWorkspaceControllers` 只消费 runtime 输出并继续负责跨域 Role、Settings 与 WorkspaceCoordinator 组合。

### 6.2 恢复与持久化

新增：

```text
ExtensionRecoveryPort
-> wechatThreadId
-> toolRunId
-> restore()
```

`useWorkspaceRecovery` 不再接收 group/tool setter，而是统一组合：

```text
extension.state
learning.state
evidence.state
```

WorkspacePersistence schema 仍为 v4，`wechatThreadId` 与 `toolRunId` 字段名保持不变。

### 6.3 drawer lazy-load

ExtensionRuntime 只在对应 drawer 打开时请求：

```text
group -> wechat
tools -> tools
timeline -> workflows
```

Memory drawer 仍由学习侧组合层加载；Sources drawer 仍由 EvidenceRuntime 加载。

### 6.4 跨域协调

新增窄端口：

```text
ExtensionCoordinatorPort
-> cancelGroup()
-> invalidateTool()
-> clearToolRun()
-> clearWorkflow()
```

WorkspaceCoordinator 没有迁入 ExtensionRuntime，也没有创建第二套协调状态。Chat 与 Web Research 的取消、RAG clear 仍由原领域 owner 提供。

### 6.5 activeQuery 单一 owner

`selectActiveQuery()` 仍是唯一 selector；生产代码中 `const activeQuery =` 只在 ExtensionRuntime 声明一次。工具 invocation 与 WorkspaceView 的 Sources 搜索继续共享同一个值，没有复制 fallback 逻辑。

### 6.6 兼容边界

- 群聊确认、发送、停止、重置与错误文案不变；
- ToolRun、Workflow 与 operation registry 行为不变；
- group/tool 恢复字段不变；
- WorkspacePersistence schema 仍为 v4；
- API、SQLite schema 与 durable entity 不变；
- UI 布局、普通用户入口和 committed learning truth 不变。

## 7. PR #107 验证证据

代码基线 commit `36d9cef3dfb611313a967574889601433ff68cc7` 的 CI run `30994619469` 完整通过：

- 全量 pytest；
- RAG K1 固定 corpus；
- Ruff；
- 项目打包；
- detect-secrets；
- expanded mypy baseline gate；
- 70 个前端测试文件、257 项测试；
- TypeScript / Vite production build；
- 38 条 desktop、mobile、360×520 Golden Journeys；
- 真实 FastAPI + SQLite 浏览器门禁。

说明：raw expanded mypy 仍有既有存量错误；baseline 为 current=125、baseline=127、resolved=2，未宣称 raw mypy 全量清零。

### 受控失败记录

- CI `30993884476`：新增 ExtensionRuntime owner 边界按预期失败；后端、RAG、Ruff、打包、密钥与 mypy baseline 均通过，证明旧 owner 尚在组合层。
- CI `30994190845`：ExtensionRuntime、recovery 与 controller 边界已通过；70 个前端文件中仅旧 `activeQuerySelector` 静态断言仍要求组合层 owner，实际 selector 已随 Tool owner 迁入 ExtensionRuntime。
- commit `36d9cef3dfb611313a967574889601433ff68cc7` 更新为验证 ExtensionRuntime 单一声明、组合层消费和 Sources / tools 共用，随后完整 CI 全绿。

这些修正没有放宽 controller、query、恢复、持久化或产品行为合同。

## 8. 下一执行顺序

### P1-R5B：收口扩展视图与实验室装载边界

下一批将 `WorkspaceView` 中的扩展组件绑定收口为单一 Extension view model，并为普通模式默认不加载实验能力建立边界：

- group / tools / timeline 的 view props；
- extension drawer 可见性与加载条件；
- 扩展错误状态与 busy 状态；
- compatibility adapters 的唯一入口；
- 不移动 Learning、Evidence、Memory 或普通设置。

### P1-R6：普通模式与单一实验室入口

普通模式只保留学习会话、资料与来源、学习成果、设置。群聊、工具和开发者诊断进入单一实验室，默认不加载。

### 剩余债务

- GitHub symbol mapping 与 CI association 增强，但继续写入通用 EvidenceSnapshot；
- 删除 NewsWorkspace 遗留无 owner CSS selector；
- CORS 统一为单一 owner；
- 410 tombstone 只在迁移窗口结束后单独删除；
- 补 Firefox、WebKit 和实体手机抽样。

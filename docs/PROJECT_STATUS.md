# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-08-05  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**按 Learning / Evidence / Extension 三个领域收口运行时 owner，并保护真实持久化、恢复、学习结束与窄屏闭环。**  
> 当前切片：**Draft PR #105 已完成 `useChatController`、chat/session 恢复与持久化 owner 向 LearningSessionRuntime 的迁移；代码基线 CI run `30933752318` 全绿。**  
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
- PR #104：LearningSessionRuntime 第一批 owner，merge SHA `b98a777f98e309b41a964c45c1c54c5ca0a54386`。

## 3. 当前待合并切片

- 分支：`agent/learning-chat-session-runtime`；
- Draft PR：`#105 迁移 LearningSessionRuntime 的 chat/session owner`；
- base：清理后的 `main` at `b0566d9d0a9c162818ddd8e9a3f644bd7609758b`；
- 代码基线：`b45f8455abf210058a300a577d16ea28e70c2717`；
- 完整 CI：run `30933752318`，结论 `success`。

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

`useLearningSessionRuntime` 现在集中拥有：

- `chatSettings`、角色保持与会话指令；
- MemoryRun、LearningClosureRun 与 `useMemoryController`；
- 唯一生产 `useChatController`；
- chat/session 消息、thread、lastChat、stream recovery 与发送状态；
- `LearningRecoveryPort`；
- 跨域清理窄端口 `LearningArtifactPort`。

`useWorkspaceControllers` 不再 import 或构造 `useChatController` / `useMemoryController`，只消费 Learning runtime。

## 6. PR #105：chat/session owner 迁移

### 6.1 解除 WorkspaceCoordinator 循环依赖

`useChatController` 在恢复、新建和归档会话时需要清理 RAG、ToolRun 与 Workflow。跨域清理仍由 `WorkspaceCoordinator` 拥有，没有迁入 LearningRuntime。

新增：

```text
LearningArtifactPort
-> clearChatArtifacts()
```

LearningRuntime 持有稳定 callback；跨域组合层通过 `bindArtifactPort()` 绑定 Coordinator 实现。禁止复制 controller 或创建第二套 chat state。

### 6.2 chat/session 恢复与持久化

`LearningRecoveryPort` 现在统一处理：

- `singleChatSessionId` 与兼容 `sessionId`；
- MemoryRun / LearningClosureRun；
- chat settings、角色保持、会话指令；
- `lastRoute`、`lastRag`、`lastSessionId`；
- `cachedMessages`；
- hydrate session、seed messages 与 restored lastChat。

`useWorkspaceRecovery` 不再 import、接收或调用 ChatController，只编排：

```text
learning.restore()
evidence.restore()
learning.hydrateRuntimeSettings()
evidence.hydrateRuntimeSettings()
```

`isSending` 仍只属于 `WorkspacePersistenceState`，用于写入节流，不进入恢复 payload。

### 6.3 兼容边界

- WorkspacePersistence schema 仍为 v4；
- 原 localStorage 字段名不变；
- session/turn/recovery API 不变；
- SQLite schema 与 durable entity 不变；
- MemoryRun、closure 与 committed learning truth 不变；
- WorkspaceCoordinator 仍是跨域清理 owner；
- 用户界面和交互入口不变。

## 7. PR #105 验证证据

代码基线 commit `b45f8455abf210058a300a577d16ea28e70c2717` 的 CI run `30933752318` 已完整通过：

- 893 项 pytest；
- RAG K1 固定 corpus；
- Ruff；
- 项目打包；
- detect-secrets；
- expanded mypy baseline gate；
- 67 个前端测试文件、243 项测试；
- TypeScript / Vite production build；
- 38 条 desktop、mobile、360×520 Golden Journeys；
- 真实 FastAPI + SQLite 浏览器门禁。

说明：raw expanded mypy 仍有既有存量错误；run 中 baseline 为 current=125、baseline=127、resolved=2，未宣称 raw mypy 全量清零。

### 受控失败记录

- CI `30932705424`：892 项测试通过，旧 packaging guard 仍要求 ChatController 在跨域组合层；更新为验证 LearningRuntime 唯一 owner。
- CI `30932952815`：后端门禁通过，两个旧前端静态断言绑定旧 Settings/recovery owner；收窄到真实职责。
- CI `30933377232`：67/67 文件、243/243 测试通过；TypeScript 发现 `isSending` 被误放入恢复类型，修正为只持久化、不恢复。

这些修正没有放宽实际 owner、持久化或产品行为边界。

## 8. 操作审计

本批开始时误将临时 `noop` 文件写入 `main`，commit `79065ae99593e0a9edf2e8007dd4acc39a80dd2e`；随后立即以 commit `b0566d9d0a9c162818ddd8e9a3f644bd7609758b` 删除。主线无净文件变化，功能分支从清理后的 commit 建立。

## 9. 下一执行顺序

### P1-R4C：收口学习会话派生视图

下一批将 WorkspaceView 中仍在现场推导的学习会话状态归入 LearningSessionRuntime 的 view model：

- active session selector；
- server/local session summary 合并规则；
- 新建会话确认语义；
- interrupted-turn abandon action；
- pedagogy phases 与 RestoreCard 所需会话派生状态。

只移动派生逻辑与 action owner，不改变界面、确认文案、session API 或 committed truth。

### P1-R5：抽离 ExtensionRuntime

```text
ExtensionRuntime
-> group chat / controlled tools / workflows / compatibility adapters
```

### P1-R6：普通模式与单一实验室入口

普通模式只保留学习会话、资料与来源、学习成果、设置。群聊、工具和开发者诊断进入单一实验室，默认不加载。

### 剩余债务

- GitHub symbol mapping 与 CI association 增强，但继续写入通用 EvidenceSnapshot；
- 删除 NewsWorkspace 遗留无 owner CSS selector；
- CORS 统一为单一 owner；
- 410 tombstone 只在迁移窗口结束后单独删除；
- 补 Firefox、WebKit 和实体手机抽样。

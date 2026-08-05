# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-08-05  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**Learning / Evidence / Extension 三个领域的运行时 owner 已基本收口，正在完成实验能力与普通学习界面的最后隔离。**  
> 当前切片：**Draft PR #108 已完成 ExtensionRuntime view model、扩展面板绑定和默认不加载边界；代码基线 CI run `30997820310` 完整通过。**  
> 下一主线：**P1-R6 普通模式与单一“实验室”入口。**  
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

## 2. 当前总体进度

### 2.1 已完成的产品与遗留清理

- PR #97：联网研究产品表面集中化，merge SHA `3b1b9ef92c0496a659e2be3bf6075d529eb01826`；
- PR #98：主工作区遗留 NewsRun 状态清理，merge SHA `6b357bfe3b63d072f9374f19e149866171145b7a`；
- PR #99：前端兼容壳与无效设置合同清理，merge SHA `04770915e08528cb639edeba9839223072340f61`；
- PR #100：NewsWorkspace / NewsController 删除与 NewsRun 兼容边界，merge SHA `42ed5fdf01f25dd56f68215ac034f77bd117bb9d`。

这组工作完成了旧 News 产品面的退场，避免其继续拥有独立 runtime、drawer 或 durable truth。

### 2.2 已完成的 Evidence 领域收口

- PR #101：EvidenceRuntime 第一批 owner 抽离，merge SHA `a5db630c1758cbb5019b6fc035c90d26cf54ec05`；
- PR #102：Evidence recovery port 与源码证据 owner 边界，merge SHA `d3da42dec0298138a48902cce860fc15f19eb808`；
- PR #103：单一 activeQuery 跨域 selector，merge SHA `22d3d0f562ed4a92b324c0f0d2c426332e8a2e47`。

EvidenceRuntime 已统一拥有 RAG、上传、联网研究、恢复和 Sources 数据加载；GitHub 源码学习继续落入通用 EvidenceSnapshot。

### 2.3 已完成的 Learning 领域收口

- PR #104：LearningSessionRuntime 第一批 owner，merge SHA `b98a777f98e309b41a964c45c1c54c5ca0a54386`；
- PR #105：LearningSessionRuntime chat/session owner，merge SHA `43f6cfbada931ccbf58712c995dbd087f7e19048`；
- PR #106：LearningSessionRuntime 会话派生 view model，merge SHA `761ea7634c97b71de7f40eed15ab0b52229631c1`。

LearningSessionRuntime 已统一拥有学习设置、ChatController、MemoryController、会话恢复、closure 与学习会话 view；WorkspaceView 不再现场推导 active session、summary、确认或中断恢复动作。

### 2.4 Extension 领域进度

- PR #107：ExtensionRuntime 第一批 controller / recovery owner，merge SHA `bb89b062747f3bb32cffa85f32d76e25dd19dcd3`；
- Draft PR #108：Extension view model 与实验能力装载边界，代码基线 `368e94e83fe5347851dffdc8ae43aa008bd79eb8`，CI run `30997820310` 完整通过。

P1-R5 完成后，ExtensionRuntime 将同时拥有 controller、恢复、按需加载和面板所需 view，不再经由跨域组合层或 WorkspaceView 中转扩展内部状态。

## 3. 当前待合并切片

- 分支：`agent/extension-view-model`；
- Draft PR：`#108 收口 ExtensionRuntime 扩展视图边界`；
- base：`main` at `f4ebf9c3ea21987896332d65da19ae1a7789763b`；
- 代码基线：`368e94e83fe5347851dffdc8ae43aa008bd79eb8`；
- 代码基线 CI：run `30997820310`，结论 `success`。

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

`useEvidenceRuntime` 集中拥有：

- RAG settings / enabled；
- RagQueryRun、RagWriteRun、ResearchRun；
- RAG、上传、联网研究 controller；
- Sources 实际加载；
- `EvidenceRecoveryPort`；
- 提供给 Learning 的窄 `EvidenceLearningPort`。

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

`useExtensionRuntime` 集中拥有：

- 唯一生产 `useGroupChatController`；
- 唯一生产 `useToolController`；
- 唯一生产 `useWorkflowController`；
- group thread 与 ToolRun ID；
- `ExtensionRecoveryPort`；
- 单一 `activeQuery` 与 Tool invocation；
- `ExtensionCoordinatorPort`；
- group / tools / timeline 显式 drawer contract 与按需加载；
- `ExtensionViewModel`。

`WorkspaceCoordinator` 仍是跨域协调 owner，只消费各领域窄端口；Memory、Evidence、Learning、普通设置与 durable truth 未迁入 ExtensionRuntime。

## 6. PR #108：扩展 view model 与装载边界

### 6.1 单一 ExtensionViewModel

ExtensionRuntime 现在通过一个 view 暴露：

```text
activeDrawer
activeQuery
group
  -> wechat / web lookup / session / controller
tools
  -> tool count / controller
timeline
  -> workflow runs / controller
```

WorkspaceRuntime 只把 `extension.view` 直接交给 WorkspaceView；`useWorkspaceControllers` 只消费 `extension.coordinator`，不再中转扩展 controller、activeQuery 或 view 状态。

### 6.2 ExtensionDrawers

新增 `ExtensionDrawers.tsx`，集中绑定：

```text
group -> WechatPanel
tools -> ToolPanel
timeline -> TimelinePanel
```

WorkspaceView 已删除对这三个 panel 和 controller 的直接认识，只保留：

```text
<ExtensionDrawers view={extensionView} />
```

### 6.3 显式 drawer contract 与默认不加载

新增：

```text
EXTENSION_DRAWERS = [group, tools, timeline]
selectExtensionDrawer()
```

规则：

- 没有 drawer 时返回 `null`；
- sessions / sources / memory / settings 等普通 drawer 返回 `null`；
- 只有 group / tools / timeline 才触发 Extension 数据加载；
- 普通学习路径不会预加载 wechat、tools 或 workflows。

### 6.4 兼容入口隔离

现有“群聊讨论 / 受控工具 / 开发者诊断”三个入口暂时保持原行为，但已从 ChatPanel 的内联实现迁入唯一 `ExtensionLauncher`。

这一步不是最终“实验室”产品面；它只建立兼容 adapter 的唯一 owner，下一批可以把三个入口替换成一个实验室入口，而不再次修改 ChatPanel 核心学习逻辑。

### 6.5 activeQuery 共享

`selectActiveQuery()` 仍是唯一 selector。ExtensionRuntime 生成同一 `activeQuery`：

- Tool invocation 使用它；
- WorkspaceView 的 Sources 搜索通过 `extensionView.activeQuery` 使用它；
- `useWorkspaceControllers` 不再中转或复制它。

### 6.6 兼容边界

- 三个现有实验入口的文案、点击和面板行为不变；
- 群聊确认、发送、停止、重置与错误文案不变；
- ToolRun、Workflow 与 operation registry 行为不变；
- WorkspacePersistence schema 仍为 v4；
- API、SQLite schema 与 durable entity 不变；
- 普通学习、Memory、Evidence 和 committed learning truth 不变。

## 7. PR #108 验证证据

代码基线 commit `368e94e83fe5347851dffdc8ae43aa008bd79eb8` 的 CI run `30997820310` 完整通过：

- 全量 pytest；
- RAG K1 固定 corpus；
- Ruff；
- 项目打包；
- detect-secrets；
- expanded mypy baseline gate；
- 72 个前端测试文件、264 项测试；
- TypeScript / Vite production build；
- 38 条 desktop、mobile、360×520 Golden Journeys；
- 真实 FastAPI + SQLite 浏览器门禁。

说明：raw expanded mypy 仍有既有存量错误；baseline 为 current=125、baseline=127、resolved=2，未宣称 raw mypy 全量清零。

### 受控失败记录

- CI `30996958715`：首个 Extension view 边界按预期失败；70 个既有前端文件、257 项测试仍通过，证明 panel binding、drawer contract 和 launcher owner 尚未迁移。
- CI `30997472272`：实际实现和 TypeScript 类型已通过大部分合同；仅 3 项旧静态断言仍要求组合层中转扩展字段，且过宽 FeatureLoader 类型残留 `groupThreadId`。
- commit `368e94e83fe5347851dffdc8ae43aa008bd79eb8` 将组合层 loader 收窄为 memory-only，并更新为“组合层只消费 ExtensionCoordinatorPort”的真实合同，随后完整 CI 全绿。

这些修正没有放宽 view owner、默认不加载、恢复、持久化或产品行为边界。

## 8. 后续任务

### P1-R6：普通模式与单一实验室入口

目标：普通模式只展示稳定学习功能；实验能力进入一个明确、默认休眠的入口。

执行项：

1. ChatPanel 的普通菜单只保留资料与来源、学习成果、设置；
2. 用一个“实验室”入口替换三个独立实验入口；
3. 实验室内部再选择群聊、受控工具、开发者诊断；
4. 未打开实验室时不请求 wechat、tools、workflows；
5. 保持旧 drawer ID 的短期兼容，但新 UI 不直接依赖它们；
6. 增加 desktop / mobile / 360×520 的实验室打开、返回和焦点测试。

### P2：平台债务清理

按风险与独立性拆分：

1. 删除 NewsWorkspace 遗留、无 owner 的 CSS selector；
2. CORS 配置统一为单一 owner；
3. 410 tombstone 在迁移窗口结束后单独删除；
4. GitHub symbol mapping 与 CI association 增强，但继续写入通用 EvidenceSnapshot；
5. 清理兼容 adapter，只在新实验室入口稳定后执行。

### P2：验证覆盖补强

- Firefox 抽样；
- WebKit 抽样；
- 至少一台实体手机的输入法、滚动、drawer 与恢复流程抽样；
- 保留 Chromium 全量 Golden Journeys 与真实 FastAPI + SQLite 门禁。

## 9. 阶段判断

当前系统已经完成运行时架构的主体收口：

```text
EvidenceRuntime
LearningSessionRuntime
ExtensionRuntime
        ↓ 窄端口
WorkspaceCoordinator
        ↓ view model
WorkspaceView
```

剩余主线不再是大规模 controller 搬迁，而是产品入口简化、兼容层退出与平台债务清理。P1-R6 完成后，可结束本轮“运行时 owner + 普通模式收口”阶段，转入独立、小批量的 P2 整理与能力增强。

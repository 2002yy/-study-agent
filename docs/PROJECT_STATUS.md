# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-08-05  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**按 Learning / Evidence / Extension 三个领域收口运行时 owner，并保护真实持久化、恢复、学习结束与窄屏闭环。**  
> 当前切片：**PR #104 已合并 `main`，LearningSessionRuntime 已接管学习设置、MemoryRun/ClosureRun、MemoryController 与恢复端口；下一批迁移 chat/session owner。**  
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

## 3. 当前主线状态

- 当前 `main` 功能基线：PR #104 merge SHA `b98a777f98e309b41a964c45c1c54c5ca0a54386`；
- PR #104 代码基线：`33b19c41bc9ca102417b9de01416142fb45eda17`；
- 代码基线 CI：run `30930508714`，结论 `success`；
- 最终 PR head：`7df757d404bca8133b28b76a7222787ec1f60116`；
- 最终 head CI：run `30930983820`，结论 `success`；
- 当前没有待合并的功能 PR。

## 4. 必须保护的稳定闭环

| 闭环 | 当前结论 | 真实证据边界 |
|---|---|---|
| 首次开始 | 真实全栈通过 | React -> FastAPI -> SQLite；无需先配置 |
| 返回学习 | 可恢复并继续 | 目标、上下文、设置、run ID 与下一步恢复 |
| 上传资料学习 | 真实全栈通过 | 文件合同、索引、EvidenceSnapshot、刷新恢复 |
| 联网研究 | 取消与恢复通过 | durable ResearchRun、同 run 重试与恢复 |
| 源码学习 | 展示与恢复可用 | 通用 EvidenceSnapshot / EvidenceTrail |
| 理解验证 | 真实全栈通过 | 正确推理才进入 committed truth |
| 学习结束 | 真实全栈通过 | closure preview、确认写入、summary、归档并新建 |
| 中断续写 | 真实全栈通过 | partial 保存、同 turn 续写、只提交一次 |
| 长会话与窄屏 | desktop / mobile / 360×520 通过 | 恢复卡、宽代码、IME、滚动、刷新恢复 |

必须继续保护：`RestoreCard`、`LearningStrip`、`SourcesPanel`、MemoryRun、ResearchRun、RAG query/write run、WorkspacePersistence v4 和学习结束 committed truth。

## 5. Evidence 与查询边界

### EvidenceRuntime

`useEvidenceRuntime` 集中拥有：

- RAG enabled/settings；
- RagQueryRun、RagWriteRun、ResearchRun ID；
- RAG、上传、联网研究 controller；
- Sources 抽屉实际数据加载；
- `EvidenceRecoveryPort`。

WorkspaceRuntime 和恢复层不得重新直接持有 evidence setter。

### activeQuery

`selectActiveQuery()` 是唯一跨域查询推导：

```text
当前输入非空 -> 当前输入
否则 -> 上一轮 RAG query
均为空 -> 空字符串
```

Sources 搜索和受控 Tool invocation 共用同一结果；聊天发送和群聊发送的 `input.trim()` 仍属于各自提交校验。

## 6. LearningSessionRuntime 第一批

`frontend/src/app/useLearningSessionRuntime.ts` 已集中拥有：

- `chatSettings`；
- `keepCurrentRole`；
- `conversationInstruction`；
- MemoryRun ID；
- LearningClosureRun ID；
- `useMemoryController`；
- session summary 写入 dispatch；
- `LearningRecoveryPort`。

### 6.1 WorkspaceRuntime 收口

WorkspaceRuntime 不再直接声明：

- `useState<ChatSettings>`；
- keep-current-role state；
- conversation-instruction state；
- MemoryRun / ClosureRun setter；
- MemoryController。

它只创建：

```text
const learning = useLearningSessionRuntime({ refresh })
```

并把 `learning` 交给跨域组合层、视图绑定和恢复端口。

### 6.2 跨域组合层

`useWorkspaceControllers`：

- 不再 import 或构造 `useMemoryController`；
- 从 `options.learning` 读取学习设置和 `memoryController`；
- 当前仍构造唯一的 `useChatController`；
- WorkspaceCoordinator 继续属于跨域组合层。

### 6.3 Learning recovery port

`LearningRecoveryPort` 统一暴露：

```text
state
restore()
hydrateRuntimeSettings()
```

`useWorkspaceRecovery` 只接收 `learning: learning.recovery`，不得直接调用学习 setter。

### 6.4 兼容边界

- WorkspacePersistence schema 仍为 v4；
- `memoryRunId`、`learningClosureRunId`、`chatSettings`、`keepCurrentRole`、`conversationInstruction` 字段名不变；
- session/turn/recovery API 不变；
- SQLite schema 与 durable entity 不变；
- MemoryRun 与 closure 确认语义不变；
- committed learning truth 不变。

## 7. PR #104 验证证据

代码基线 commit `33b19c41bc9ca102417b9de01416142fb45eda17` 的 CI run `30930508714` 与最终 head commit `7df757d404bca8133b28b76a7222787ec1f60116` 的 CI run `30930983820` 均完整通过：

- 全量 pytest；
- RAG K1 固定 corpus；
- Ruff；
- 项目打包；
- detect-secrets；
- expanded mypy baseline gate；
- 67 个前端测试文件、240 项测试；
- TypeScript / Vite production build；
- 38 条 desktop、mobile、360×520 Golden Journeys；
- 真实 FastAPI + SQLite 浏览器门禁。

说明：raw expanded mypy 仍有既有存量错误；通过的是仓库既定 baseline gate，未宣称 raw mypy 全量清零。

## 8. 下一执行顺序

### P1-R4B：迁移 chat/session owner

下一批继续将以下职责归入 LearningSessionRuntime：

- `useChatController`；
- active session 与 session summary selector；
- session restore / new / archive 的会话侧 owner；
- pedagogy phase 和 RestoreCard 所需的会话状态；
- chat persistence/recovery port。

必须先解决 WorkspaceCoordinator 与 chat controller 的跨域清理依赖，不得通过复制 controller 或新增第二套 chat state 绕开。

### P1-R5：抽离 ExtensionRuntime

```text
ExtensionRuntime
-> group chat / controlled tools / workflows / compatibility adapters
```

### P1-R6：普通模式与单一实验室入口

普通模式只保留：会话历史、资料与来源、学习成果、设置。群聊、工具和开发者诊断进入单一实验室，默认不加载。

### 剩余债务

- GitHub symbol mapping 与 CI association 增强，但继续写入通用 EvidenceSnapshot；
- 删除 NewsWorkspace 遗留无 owner CSS selector；
- CORS 统一为单一 owner；
- 410 tombstone 只在迁移窗口结束后单独删除；
- 补 Firefox、WebKit 和实体手机抽样。

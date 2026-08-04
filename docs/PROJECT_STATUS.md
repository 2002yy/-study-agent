# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-08-04  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**停止横向扩张，集中梳理核心学习功能、产品入口、运行状态与桌面/移动端体验。**  
> 当前切片：**PR #100 已合并 `main`；Draft PR #101 已完成 EvidenceRuntime 第一批 owner 抽离，代码基线 CI run `30917787585` 全绿。**  
> 冻结边界：**Provider replay 扩展、生产 claim producer / claim UI、生产 ChatTurn 接入、群聊能力扩张、新闻产品化和可执行 agent 均不是当前开发主线。**

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
- 新闻不是独立顶级产品，而是联网研究的一种时效性预设。
- GitHub 是源码学习证据来源，不是第二个顶级工作台。
- Memory 是学习连续性基础设施；Workflow 只属于高级诊断。
- planned / attempted / partial / failed 不得覆盖 committed learning truth。
- 普通用户最终只需要理解四个稳定入口：学习会话、资料与来源、学习成果、设置。
- 群聊、手动工具、开发者诊断和兼容能力最终统一进入单一“实验室”边界。

## 2. 当前核心基线

### 2.1 已合并主线

- 核心架构精简与真实全栈基线：`9e0adb8c6833b4e1733dfb897d5fc7a92c9df5ab`；
- PR #92：失败刷新恢复与长会话恢复入口；
- PR #93：联网研究取消状态收口；
- PR #96：联网研究阶段与 partial 结果使用边界；
- PR #97：联网研究产品表面集中化，squash merge SHA `3b1b9ef92c0496a659e2be3bf6075d529eb01826`；
- PR #98：主工作区遗留 NewsRun 状态与过时 action 清理，squash merge SHA `6b357bfe3b63d072f9374f19e149866171145b7a`；
- PR #99：前端类型、布局兼容壳和无效设置合同清理，squash merge SHA `04770915e08528cb639edeba9839223072340f61`；
- PR #100：NewsWorkspace / NewsController 前端适配层删除与 NewsRun 兼容边界收口，squash merge SHA `42ed5fdf01f25dd56f68215ac034f77bd117bb9d`。

### 2.2 当前待合并切片

- 分支：`agent/evidence-runtime-extraction`；
- Draft PR：`#101 抽离 EvidenceRuntime owner`；
- 代码基线 commit：`b6bd09aa5a81d6f055176badb5316b8c32401da0`；
- 完整 CI：run `30917787585`，结论 `success`。

## 3. 已验证的产品闭环

| 闭环 | 当前结论 | 真实证据边界 |
|---|---|---|
| 首次开始 | 真实全栈通过 | React -> FastAPI -> SQLite；无需先配置 |
| 返回学习 | 可恢复并继续 | 目标、上下文和下一步恢复；继续后刷新一致 |
| 上传资料学习 | 真实全栈通过 | 文件合同、解析、索引、EvidenceSnapshot、刷新恢复 |
| 联网研究 | 取消与恢复闭环通过 | durable ResearchRun、取消、刷新、同 run 重试 |
| 研究资料选择 | 已收口 | run 与回答证据可恢复；一次性选择不会跨刷新或会话自动继承 |
| 源码学习 | 展示与恢复可用 | symbol mapping 与 CI association 仍需增强 |
| 理解验证 | 真实全栈通过 | 空泛“懂了”不提交；正确推理才进入 committed truth |
| 学习结束 | 真实全栈通过 | closure preview、确认写入、summary、刷新、归档并新建 |
| 中断续写 | 真实全栈通过 | partial 保存、同 turn 续写、前缀不重复、只提交一次 |
| 零 token 失败 | 真实全栈通过 | failed 可恢复；retry child 完成后 parent superseded |
| 长会话恢复 | desktop / mobile / 360×520 通过 | 恢复卡保持在当前 conversation viewport |
| 窄屏复杂内容 | 360×520 通过 | 长中文、URL、宽代码、IME、滚动与刷新恢复 |

## 4. 必须保护的稳定骨架

- `RestoreCard`：新用户、返回学习、失败重试和中断续写；
- `LearningStrip`：目标、阶段、缺口、下一步和验证状态；
- 上传后回到“系统学习 / 直接提问”，不把用户丢进资料管理页；
- `SourcesPanel`：本次回答依据、我的资料、检索诊断三层分离；
- 学习结束必须经过 preview、确认和 hash-locked MemoryRun；
- durable run、刷新恢复、窄屏、IME 和复杂内容已有强回归门禁。

任何运行时拆分不得改变 committed truth、持久化格式、恢复语义或上述交互闭环。

## 5. 已完成的集中化切片

### 5.1 PR #97：新闻与联网研究产品表面合并

1. 删除普通菜单和群聊中的独立新闻工作区；
2. 普通用户联网研究统一使用 durable ResearchRun；
3. completed run 恢复后默认只展示，不自动继承为下一轮聊天资料；
4. 切换聊天线程时复位一次性 `useInChat=false`，但不删除 run 或回答证据。

### 5.2 PR #98：主工作区遗留 NewsRun 状态清理

1. 删除 `activeNewsRunId`、旧新闻查询状态和 NewsController wiring；
2. `WorkspacePersistence` schema 升至 v4，旧 `newsRunId` 显式丢弃；
3. 删除过时 reducer action；
4. 聊天切换保留独立 Research / Tool / RAG run。

### 5.3 PR #99：前端类型与布局兼容合同收尾

1. 删除 `DrawerId.news` 和当前 `WorkspaceState.newsRunId`；
2. 删除旧 Sidebar / Inspector 兼容壳；
3. `SettingsPanel` props 只保留真实使用的输入；
4. 静态边界禁止兼容壳与无效合同重新接回。

### 5.4 PR #100：NewsWorkspace / NewsRun 最终边界

1. 全树审计确认 NewsWorkspace / NewsController 没有生产前端调用者；
2. 删除 NewsWorkspace、NewsController 及专属测试；
3. 普通用户新闻能力只能通过 ResearchRun / Web Research；
4. 后端 NewsRun 暂留为 headless compatibility durable workflow；
5. 六条旧新闻 URL 仅保留无业务副作用的 410 tombstone；
6. tombstone 不得执行旧流程或写入群聊文件。

## 6. PR #101：EvidenceRuntime 第一批 owner 抽离

### 6.1 已迁移 owner

新增 `frontend/src/app/useEvidenceRuntime.ts`，集中拥有：

- `ragEnabled` 与 `ragSettings`；
- `activeRagQueryRunId`、`activeRagWriteRunId`、`activeWebLookupRunId` 的读取和 dispatch；
- `useRagController`；
- `useUploadController`；
- `useWebLookupController`；
- 聊天线程变化时的一次性研究选择复位；
- Sources 抽屉打开时的 RAG 状态与知识文档加载。

### 6.2 顶层运行时变化

- `WorkspaceRuntime` 不再直接保存 RAG 设置或三个 evidence run ID；
- `WorkspaceRuntime` 只实例化 `useEvidenceRuntime`，再将其公开合同交给恢复、视图与跨域组合；
- `useWorkspaceControllers` 不再构造 WebLookup / RAG / Upload controller；
- `useWorkspaceControllers` 仍负责聊天、群聊、工具、记忆和 evidence 之间的跨域编排；
- `WorkspaceView` 的用户可见 props 和交互行为未变化；
- `useWorkspaceRecovery` 的 localStorage schema 与恢复字段未变化。

### 6.3 永久边界

静态测试锁定：

- WebLookup、RAG、Upload controller 只能由 EvidenceRuntime 构造；
- WorkspaceRuntime 不得重新持有 evidence run ID 或 `RagSettings` state；
- Sources 抽屉的 RAG 与文档加载只能由 EvidenceRuntime 执行；
- 跨域组合层可以明确跳过 `sources`，但不得调用 RAG 加载或 `refreshDocuments()`；
- WorkspaceCoordinator 仍属于跨域组合层，不下沉到 EvidenceRuntime。

## 7. PR #101 验证证据

代码基线 commit `b6bd09aa5a81d6f055176badb5316b8c32401da0` 的 CI run `30917787585` 已完整通过：

- 全量 pytest；
- RAG K1 固定 corpus；
- Ruff；
- 项目打包；
- detect-secrets；
- expanded mypy baseline gate；
- 64 个前端测试文件、231 项测试；
- TypeScript / Vite production build；
- 38 条 desktop、mobile、360×520 Golden Journeys；
- 真实 FastAPI + SQLite 浏览器门禁。

CI 首轮发现一条新静态测试把“跨域层明确跳过 sources”误判成 owner。修正后的合同允许声明委托，但禁止跨域层实际加载 RAG 或知识文档。没有为通过测试恢复旧 owner，也没有改变产品行为。

说明：raw expanded mypy 仍有既有存量错误；通过的是仓库既定 baseline gate，未宣称 raw mypy 全量清零。

## 8. 当前明确保留

- ResearchRun SQLite schema、checkpoint、cancel、resume、retry；
- RAG query/write durable run 与恢复字段；
- 后端 NewsRun durable entity、`/news/runs` 与六条 410 tombstone；
- RestoreCard、LearningStrip、SourcesPanel、MemoryRun；
- 学习结束 committed truth；
- `useWorkspaceRecovery` 的跨域持久化协调；
- WorkspaceCoordinator 的跨域取消与清理职责。

本批没有创建第二套 evidence 状态，也没有迁移数据库或 API。

## 9. 下一执行顺序

### P1-R2：继续收窄 EvidenceRuntime 合同

1. 将 evidence 恢复字段组合封装为明确的 `ids / setIds / settings` 合同，减少 WorkspaceRuntime 展开字段；
2. 审计 GitHub evidence 的生产 owner，将其归入 EvidenceRuntime，而不是新增顶级工作区；
3. 评估 `activeQuery` 是否应拆成跨域 selector，避免工具与 Sources 各自推导；
4. 保持 WorkspacePersistence schema 不变。

### P1-R3：抽离 LearningSessionRuntime

```text
LearningSessionRuntime
-> chat / sessions / pedagogy / recovery / closure
```

先移动 owner，不改变 session、turn、closure 或 committed truth。

### P1-R4：抽离 ExtensionRuntime

```text
ExtensionRuntime
-> group chat / controlled tools / workflows / compatibility adapters
```

### P1-R5：普通模式与单一实验室入口

普通模式只保留：会话历史、资料与来源、学习成果、设置。群聊、工具和开发者诊断进入单一实验室，默认不加载。

### P1/P2：剩余债务

- 删除 NewsWorkspace 遗留的无 owner CSS selector；
- CORS 统一为单一 owner；
- 410 tombstone 只在明确迁移窗口结束后单独删除；
- 补 Firefox、WebKit 和实体手机抽样；
- GitHub symbol mapping 与 CI association 继续增强。

## 10. PR #101 合并条件

- 最新 head 完整 CI 全绿；
- 状态文档与代码事实一致；
- 不改变 WorkspacePersistence schema；
- 不改变 ResearchRun、RAG、MemoryRun 或 committed learning truth；
- 不恢复 NewsWorkspace、NewsController 或新闻顶级入口；
- PR 保持可回滚，范围只包含 EvidenceRuntime 第一批 owner 抽离。

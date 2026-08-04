# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-08-04  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**停止横向扩张，集中梳理核心学习功能、产品入口、运行状态与桌面/移动端体验。**  
> 当前切片：**PR #99 已合并 `main`；Draft PR #100 已删除无生产调用者的 NewsWorkspace / NewsController 前端适配层，并明确后端 NewsRun 与 410 迁移墓碑边界。代码基线 CI run `30915516437` 全绿。**  
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
- PR #99：前端类型、布局兼容壳和无效设置合同清理，squash merge SHA `04770915e08528cb639edeba9839223072340f61`。

### 2.2 当前待合并切片

- 分支：`agent/news-compatibility-boundary`；
- Draft PR：`#100 收口新闻兼容适配层`；
- 代码基线 commit：`fbd321cb4782aca42b554eb2010d9e2fd54b69ca`；
- 完整 CI：run `30915516437`，结论 `success`。

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

## 4. 功能集中化已完成切片

### 4.1 必须保护的稳定骨架

- `RestoreCard`：新用户、返回学习、失败重试和中断续写；
- `LearningStrip`：目标、阶段、缺口、下一步和验证状态；
- 上传后回到“系统学习 / 直接提问”，不把用户丢进资料管理页；
- `SourcesPanel`：本次回答依据、我的资料、检索诊断三层分离；
- 学习结束必须经过 preview、确认和 hash-locked MemoryRun；
- durable run、刷新恢复、窄屏、IME 和复杂内容已有强回归门禁。

这些能力不是当前清理对象。任何集中化修改不得改变其 committed truth、持久化和恢复合同。

### 4.2 PR #97：新闻与联网研究产品表面合并

1. 从普通菜单移除独立“新闻研究”；
2. 删除主工作区新闻抽屉；
3. 群聊不再嵌入完整 `NewsWorkspace`；
4. 群聊只读展示已有 ResearchRun，不再创建第二套研究真值；
5. 聊天入口继续创建带 `owner_turn_id` 的 durable ResearchRun；
6. 保留取消、刷新恢复和同 run 重试；
7. completed run 恢复后默认只展示，不自动选为下一轮聊天资料；
8. 切换聊天线程时复位一次性 `useInChat=false`，但不删除 run 或回答证据。

### 4.3 PR #98：主工作区遗留 NewsRun 状态清理

1. 删除 `activeNewsRunId`、`SET_ACTIVE_NEWS_RUN`、旧新闻查询和 `readArticles` 状态；
2. 主工作区不再构造或返回 `useNewsController`；
3. 删除 NewsRun 取消端口和 run ID wiring；
4. 群聊 reset 只影响群聊 scope；
5. `WorkspacePersistence` schema 升至 v4，恢复旧 payload 时主动丢弃 `newsRunId`；
6. reducer 删除 `selectedPanel`、`SELECT_PANEL` 和无生产调用者的 `START_NEW_CHAT_SESSION`；
7. 聊天切换保留独立 Research / Tool / RAG run；
8. 静态边界测试禁止退休字段和 NewsController 回到主工作区。

### 4.4 PR #99：前端类型与布局兼容合同收尾

1. `DrawerId` 删除 `"news"`；
2. 当前 `WorkspaceState` 删除 `newsRunId`；
3. 旧 payload 可含 `newsRunId`，但恢复时显式丢弃，不再写回；
4. 工作区直接依赖 `SettingsPanel`；
5. 删除 `SettingsPanel` 五个未使用 props；
6. 删除仅做重导出的 `layout/Sidebar.tsx`；
7. 删除已被独立抽屉取代的 `layout/Inspector.tsx`；
8. 扩展静态边界测试，禁止兼容壳和无效合同重新接回。

### 4.5 PR #100：NewsWorkspace / NewsRun 最终边界

#### 调用者审计

临时 inventory CI run `30914499344` 对 `frontend/src`、`src` 和 `tests` 做全树扫描，结论：

- `NewsWorkspace` 与 `useNewsController` 没有生产前端调用者；
- 它们只剩自身文件、专属单元测试与边界测试；
- `/news/runs` 前端 API helper 只被退休 controller 使用；
- 后端 `/news/runs` route、NewsService、SQLite durable entity 和跨层回归测试仍完整存在；
- 六条旧新闻 URL 已由测试明确保护为 410 迁移墓碑，且不得执行旧流程。

#### 已完成

1. 删除 `features/news-workspace/NewsWorkspace.tsx`；
2. 删除 `features/news-workspace/newsController.ts`；
3. 删除 NewsController 专属单元测试与旧 controller boundary test；
4. `WebLookupRunBoundary.test.ts` 改为永久断言旧 UI/controller 不得恢复；
5. 新增仓库级兼容边界：NewsRun 客户端命令只能留在 `frontend/src/api.ts`，其他生产前端不得成为 owner；
6. 保留 `NewsRunResponse` 与 `/news/runs` 客户端 helper，作为无 UI 的 headless compatibility adapter；
7. 保留后端 NewsRun durable entity、完整 server-owned `/news/runs` 工作流和跨层测试；
8. 保留 `/news/round`、`/wechat/news-round`、`/news/search`、`/news/enrich`、`/news/digest`、`/news/discuss` 六条 410 迁移墓碑；
9. 410 墓碑只拒绝请求并指向 `/news/runs`，不得执行 `src.api.run_news_round` 或写入群聊文件。

#### 最终结论

```text
普通用户新闻能力
-> 只能通过 durable ResearchRun / Web Research

退休前端 NewsWorkspace / NewsController
-> 删除，不再保留实验 UI

后端 NewsRun
-> 暂时保留为 headless compatibility durable workflow

旧新闻 URL
-> 保留 410 tombstone，不再拥有业务实现
```

## 5. PR #100 验证证据

代码基线 commit `fbd321cb4782aca42b554eb2010d9e2fd54b69ca` 的 CI run `30915516437` 已完整通过：

- 全量 pytest；
- RAG K1 固定 corpus；
- Ruff；
- 项目打包；
- detect-secrets；
- expanded mypy baseline gate；
- 完整前端测试；
- TypeScript / Vite production build；
- 38 条 desktop、mobile、360×520 Golden Journeys；
- 真实 FastAPI + SQLite 浏览器门禁。

审计与 CI 实际发现：六条 410 路由不是可直接删除的无主代码，而是仓库明确测试的兼容墓碑。第一次尝试改为 404 后，`test_legacy_news_round_routes_are_gone_without_running_legacy_flow` 精确失败；最终恢复 410 拒绝合同，没有恢复任何旧业务流。

说明：raw expanded mypy 仍有既有存量错误；通过的是仓库既定 baseline gate，未宣称 raw mypy 全量清零。

## 6. 当前明确保留

- ResearchRun SQLite schema、checkpoint、cancel、resume、retry；
- 后端 NewsRun durable entity 与 `/news/runs`；
- 六条无业务副作用的新闻 410 迁移墓碑；
- RestoreCard、LearningStrip、SourcesPanel、RAG、MemoryRun；
- 学习结束 committed truth；
- Workspace runtime 的 durable owner；
- 普通模式与实验室入口的后续设计空间。

当前已不存在：普通用户新闻顶级入口、新闻抽屉、NewsWorkspace、NewsController、NewsRun 工作区状态、NewsRun 持久化 owner。

## 7. 下一执行顺序

### P1-R1：运行时按领域拆分

```text
LearningSessionRuntime
  -> chat / sessions / pedagogy / recovery / closure

EvidenceRuntime
  -> upload / RAG / research / GitHub evidence / sources

ExtensionRuntime
  -> group chat / controlled tools / workflows / compatibility adapters
```

拆分原则：

- 先移动 owner，不改变 durable entity；
- 每个切片只迁移一个领域；
- 继续跑完整前端、窄屏和真实全栈门禁；
- 不允许重新制造第二套会话或研究真值。

第一刀优先抽离 `EvidenceRuntime`，因为上传、RAG、ResearchRun、GitHub evidence 和 Sources 已有较清晰的共同边界。

### P1-R2：普通模式与单一实验室入口

普通模式只保留：会话历史、资料与来源、学习成果、设置。群聊、工具和开发者诊断进入单一实验室，默认不加载。

### P1-R3：学习成果与长期记忆分层

默认学习结束只展示本次成果、未解决项、下一步和将写入内容；长期记忆目标、手动候选编辑和置信度明细降到高级管理。

### P1/P2：样式与后端兼容债务

- 删除 NewsWorkspace 后遗留的无 owner CSS selector，在 CSS owner 批次统一处理；
- CORS 统一为单一 owner；
- 410 墓碑只在明确迁移窗口结束后单独删除；
- 补 Firefox、WebKit 和实体手机抽样。

## 8. PR #100 合并条件

- 最新 head 的完整 CI 全绿；
- 状态文档与代码事实一致；
- 不恢复新闻顶级入口、NewsWorkspace 或 NewsController；
- 不删除后端 durable NewsRun；
- 410 路由只做无副作用 tombstone；
- 不改变 ResearchRun、RAG、MemoryRun 或 committed learning truth；
- PR 保持可回滚，范围只包含新闻兼容边界收口。

# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-08-04  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**停止横向扩张，集中梳理核心学习功能、产品入口、运行状态与桌面/移动端体验。**  
> 当前切片：**PR #97 已合并 `main`；Draft PR #98 已完成主工作区遗留 NewsRun 状态与过时会话 action 的运行时清理，代码基线 CI run `30907587238` 全绿。**  
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
- GitHub 是源码学习证据来源，不是第二个顶级工作台。
- Memory 是学习连续性基础设施；Workflow 只属于高级诊断。
- planned / attempted / partial / failed 不得覆盖 committed learning truth。
- 普通用户最终只需要理解四个稳定入口：学习会话、资料与来源、学习成果、设置。
- 群聊、手动工具、开发者诊断和兼容能力最终统一进入单一“实验室”边界。
- 新闻不是独立顶级产品，而是联网研究的一种时效性预设。

## 2. 当前核心基线

### 2.1 已合并主线

- 核心架构精简与真实全栈基线：`9e0adb8c6833b4e1733dfb897d5fc7a92c9df5ab`；
- PR #92：失败刷新恢复与长会话恢复入口；
- PR #93：联网研究取消状态收口；
- PR #96：联网研究阶段与 partial 结果使用边界；
- PR #97：联网研究产品表面集中化，squash merge SHA `3b1b9ef92c0496a659e2be3bf6075d529eb01826`。

### 2.2 当前待合并切片

- 分支：`agent/frontend-state-consolidation`；
- Draft PR：`#98 清理前端遗留 NewsRun 状态与过时会话 action`；
- 代码基线 commit：`5ddcfd85369a224d49b1c329ee6bf1d1544f2837`；
- 完整 CI：run `30907587238`，结论 `success`。

## 3. 已验证的产品闭环

| 闭环 | 当前结论 | 真实证据边界 |
|---|---|---|
| 首次开始 | 真实全栈通过 | React -> FastAPI -> SQLite；无需先配置 |
| 返回学习 | 可恢复并继续 | 目标、上下文和下一步恢复；继续后刷新一致 |
| 上传资料学习 | 真实全栈通过 | 文件合同、解析、索引、EvidenceSnapshot、刷新恢复 |
| 联网研究 | 取消与恢复闭环通过 | durable ResearchRun、取消、刷新、同 run 重试 |
| 研究资料选择 | 已收口 | run 与回答证据可恢复；“用于下一轮聊天”不会跨刷新或会话自动继承 |
| 源码学习 | 展示与恢复可用 | symbol mapping 与 CI association 仍需增强 |
| 理解验证 | 真实全栈通过 | 空泛“懂了”不提交；正确推理才进入 committed truth |
| 学习结束 | 真实全栈通过 | closure preview、确认写入、summary、刷新、归档并新建 |
| 中断续写 | 真实全栈通过 | partial 保存、同 turn 续写、前缀不重复、只提交一次 |
| 零 token 失败 | 真实全栈通过 | failed 可恢复；retry child 完成后 parent superseded |
| 长会话恢复 | desktop / mobile / 360×520 通过 | 恢复卡保持在当前 conversation viewport |
| 窄屏复杂内容 | 360×520 通过 | 长中文、URL、宽代码、IME、滚动与刷新恢复 |

## 4. 功能集中化审计结论

### 4.1 已稳定、必须保护

- `RestoreCard`：新用户、返回学习、失败重试和中断续写；
- `LearningStrip`：目标、阶段、缺口、下一步和验证状态；
- 上传后回到“系统学习 / 直接提问”，不把用户丢进资料管理页；
- `SourcesPanel`：本次回答依据、我的资料、检索诊断三层分离；
- 学习结束必须经过 preview、确认和 hash-locked MemoryRun；
- durable run、刷新恢复、窄屏、IME 和复杂内容已有强回归门禁。

这些能力不是当前清理对象。任何集中化修改不得改变其 committed truth、持久化和恢复合同。

### 4.2 已完成：新闻与联网研究产品表面合并

PR #97 已完成：

1. 从普通菜单移除独立“新闻研究”；
2. 删除主工作区新闻抽屉；
3. 群聊不再嵌入完整 `NewsWorkspace`；
4. 群聊只读展示已有 ResearchRun，不再自行创建第二套研究真值；
5. 聊天入口继续创建带 `owner_turn_id` 的 durable ResearchRun；
6. 保留取消、刷新恢复和同 run 重试；
7. completed run 恢复后默认只展示，不自动选为下一轮聊天资料；
8. 切换聊天线程时复位一次性 `useInChat=false`，但不删除 run 或回答证据。

### 4.3 已完成：主工作区遗留 NewsRun 运行时状态清理

PR #98 当前已完成：

1. 删除 `WorkspaceRuntime` 中的 `activeNewsRunId`、`SET_ACTIVE_NEWS_RUN`、旧新闻查询和 `readArticles` 状态；
2. 删除 `useWorkspaceControllers` 对 `useNewsController` 的构造、返回、取消端口和 run ID wiring；
3. 群聊重置不再承担“清除关联新闻”的跨领域副作用；
4. `WorkspaceCoordinator` 不再拥有 NewsRun 取消端口；
5. `WorkspacePersistence` schema 从 v3 升到 v4；
6. 恢复 v3 或无版本旧 payload 时主动丢弃 `newsRunId`；
7. `useWorkspaceRecovery` 不再保存或恢复 NewsRun ID；
8. reducer 删除 `activeNewsRunId`、`selectedPanel`、`SELECT_PANEL` 和无生产调用者的 `START_NEW_CHAT_SESSION`；
9. 聊天会话切换继续保留独立 Research / Tool / RAG run，只清理绑定聊天 closure 的 MemoryRun 和 LearningClosureRun；
10. 群聊重置只修改群聊 scope；
11. 新增静态边界测试，禁止 `NewsController` 和退休字段重新接回主工作区。

### 4.4 operation scope 的最终结论

- 生产 `chatController.startNewSession()` 使用 `TRANSITION_CHAT_SESSION + clearChatArtifacts()`，不使用已删除的 `START_NEW_CHAT_SESSION`；
- 因此旧 action 的多 run 清理不是已发生的生产 bug，而是历史 action / 测试债务；
- 真正已确认且已修复的风险是一次性 `useInChat` 选择跨刷新或会话继承；
- reducer 清 ID、浏览器 AbortController 失效、服务端 cancel 必须继续分别建模。

## 5. PR #98 验证证据

代码基线 run `30907587238` 已完整通过：

- 全量 pytest；
- RAG K1 固定 corpus；
- Ruff；
- 项目打包；
- detect-secrets；
- expanded mypy baseline gate；
- 66 个前端测试文件、229 项测试；
- TypeScript / Vite production build；
- desktop、mobile、360×520 fixture / narrow Golden Journeys；
- 真实 FastAPI + SQLite 浏览器门禁。

说明：raw expanded mypy 仍有既有存量错误；通过的是仓库既定 baseline gate，未宣称 raw mypy 全量清零。

## 6. 当前明确保留

本批没有删除或迁移：

- 后端 `NewsRun` durable entity；
- `NewsWorkspace` 实现与单元测试；
- 新闻兼容 API；
- ResearchRun SQLite schema、checkpoint、cancel、resume、retry；
- RestoreCard、LearningStrip、SourcesPanel、RAG、MemoryRun；
- 学习结束 committed truth。

当前仍有两个无运行时 owner 的纯类型残留：

- `DrawerId` 中的 `"news"`；
- 旧 `WorkspaceState.newsRunId`。

由于 `types.ts` 是大体量共享合同，本批没有为删除两个字面量而整文件重写。它们已无主工作区调用者，应在下一次类型合同整理中删除并由 build 验证。

## 7. 下一执行顺序

### P0-R4：类型合同与兼容边界收尾

1. 删除 `DrawerId="news"` 与 `WorkspaceState.newsRunId`；
2. 检查旧 `Inspector`、Sidebar alias 和 SettingsPanel 未使用 props；
3. 明确 NewsWorkspace 是实验 adapter 还是直接冻结；
4. 决定后端 NewsRun 保留为实验 adapter，或迁移成 ResearchRun 的新闻预设；
5. 删除替代路径已覆盖的 deprecated / 410 新闻路由。

### P1：运行时按领域拆分

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

### P1：普通模式与实验室入口

普通模式只保留：会话历史、资料与来源、学习成果、设置。群聊、工具和开发者诊断进入单一实验室，默认不加载。

### P1：学习成果与长期记忆分层

默认学习结束只展示本次成果、未解决项、下一步和将写入内容；七类长期记忆目标、手动候选编辑和置信度明细降到高级管理。

### P1/P2：样式与后端兼容债务

- 按组件迁移 CSS owner；全局仅保留 token、reset、accessibility 和布局基线；
- CORS 统一为单一 owner；
- 分批删除 deprecated / 410 路由；
- 补 Firefox、WebKit 和实体手机抽样。

## 8. 合并条件

PR #98 合并前必须满足：

- 状态文档与代码事实一致；
- 最新 head 的完整 CI 全绿；
- 不恢复新闻顶级入口；
- 不删除后端 durable NewsRun；
- 不改变 ResearchRun、RAG、MemoryRun 或 committed learning truth；
- PR 保持可回滚、范围仅限前端状态集中化。

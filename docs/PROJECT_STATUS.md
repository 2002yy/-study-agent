# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-08-05  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**停止横向扩张，按 Learning / Evidence / Extension 三个领域收口运行时 owner，并保护真实持久化、恢复和窄屏闭环。**  
> 当前切片：**PR #102 已合并 `main`；Draft PR #103 已完成单一 `activeQuery` 跨域 selector，代码基线 CI run `30928667587` 全绿。**  
> 冻结边界：**Provider replay 扩展、生产 claim UI、群聊能力扩张、新闻产品化和可执行 agent 均不是当前开发主线。**

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
- GitHub 是源码学习的证据来源场景，不是第二个顶级工作台，也不拥有独立前端状态。
- 新闻不是独立顶级产品，而是联网研究的一种时效性预设。
- planned / attempted / partial / failed 不得覆盖 committed learning truth。
- 普通用户最终只需要理解四个稳定入口：学习会话、资料与来源、学习成果、设置。
- 群聊、手动工具、开发者诊断和兼容能力最终统一进入单一“实验室”边界。

## 2. 已合并主线

- 核心真实全栈基线：`9e0adb8c6833b4e1733dfb897d5fc7a92c9df5ab`；
- PR #97：联网研究产品表面集中化，merge SHA `3b1b9ef92c0496a659e2be3bf6075d529eb01826`；
- PR #98：主工作区遗留 NewsRun 状态清理，merge SHA `6b357bfe3b63d072f9374f19e149866171145b7a`；
- PR #99：前端类型、布局兼容壳和无效设置合同清理，merge SHA `04770915e08528cb639edeba9839223072340f61`；
- PR #100：NewsWorkspace / NewsController 删除与 NewsRun 兼容边界，merge SHA `42ed5fdf01f25dd56f68215ac034f77bd117bb9d`；
- PR #101：EvidenceRuntime 第一批 owner 抽离，merge SHA `a5db630c1758cbb5019b6fc035c90d26cf54ec05`；
- PR #102：Evidence recovery port 与源码证据 owner 边界，merge SHA `d3da42dec0298138a48902cce860fc15f19eb808`。

## 3. 当前待合并切片

- 分支：`agent/active-query-selector`；
- Draft PR：`#103 收口 activeQuery 跨域 selector`；
- base：`main` at `d798fe4294519063562d697ab05fef54a5a129dd`；
- 代码基线 head：`484fe952a2860538f6bf10f83893f73f33bc22ef`；
- 完整 CI：run `30928667587`，结论 `success`。

## 4. 必须保护的稳定闭环

| 闭环 | 当前结论 | 真实证据边界 |
|---|---|---|
| 首次开始 | 真实全栈通过 | React -> FastAPI -> SQLite；无需先配置 |
| 返回学习 | 可恢复并继续 | 目标、上下文、设置和下一步恢复；刷新一致 |
| 上传资料学习 | 真实全栈通过 | 文件合同、解析、索引、EvidenceSnapshot、刷新恢复 |
| 联网研究 | 取消与恢复闭环通过 | durable ResearchRun、取消、刷新、同 run 重试 |
| 研究资料选择 | 已收口 | 一次性选择不会跨刷新或会话自动继承 |
| 源码学习 | 展示与恢复可用 | 复用通用 EvidenceSnapshot / EvidenceTrail；symbol mapping 与 CI association 仍需增强 |
| 理解验证 | 真实全栈通过 | 空泛“懂了”不提交；正确推理才进入 committed truth |
| 学习结束 | 真实全栈通过 | closure preview、确认写入、summary、刷新、归档并新建 |
| 中断续写 | 真实全栈通过 | partial 保存、同 turn 续写、前缀不重复、只提交一次 |
| 长会话与窄屏 | desktop / mobile / 360×520 通过 | 恢复卡、长 URL、宽代码、IME、滚动和刷新恢复 |

必须继续保护：`RestoreCard`、`LearningStrip`、`SourcesPanel`、MemoryRun、ResearchRun、RAG query/write run、WorkspacePersistence v4 与学习结束 committed truth。

## 5. PR #101：EvidenceRuntime 第一批 owner 抽离

`frontend/src/app/useEvidenceRuntime.ts` 已集中拥有：

- `ragEnabled` 与 `ragSettings`；
- RagQueryRun、RagWriteRun、ResearchRun ID 与 dispatch；
- `useRagController`、`useUploadController`、`useWebLookupController`；
- 会话切换时的一次性研究选择复位；
- Sources 抽屉的 RAG 与知识文档加载。

永久边界：

- WorkspaceRuntime 不再直接持有 evidence state；
- `useWorkspaceControllers` 不再构造 evidence controller；
- Sources 的实际加载只能由 EvidenceRuntime 执行；
- WorkspaceCoordinator 继续属于跨域组合层。

## 6. PR #102：Evidence 恢复合同收口

### 6.1 新恢复端口

EvidenceRuntime 新增：

- `EvidenceRecoveryInput`：只接收 RagQueryRun、RagWriteRun、ResearchRun、RAG settings 和 enabled；
- `EvidenceRecoveryState`：只读提供持久化所需 evidence 字段；
- `EvidenceRecoveryPort`：统一暴露 `state`、`restore()`、`hydrateRuntimeSettings()`。

`WorkspaceRuntime` 只向 `useWorkspaceRecovery` 传入：

```text
evidence: evidence.recovery
```

不再逐项传入 evidence run ID、setter、RAG settings 和 enabled。`useWorkspaceRecovery` 不能直接操作 EvidenceRuntime setter，只能调用窄端口。

### 6.2 持久化与源码证据边界

- `WorkspacePersistence` schema 仍为 v4；
- localStorage 字段名和旧 payload 恢复格式均未改变；
- 没有迁移 API、SQLite schema 或 durable entity；
- GitHub 源码学习继续复用 server `evidence-snapshot-v1`、`normalizeEvidence()` 和 `EvidenceTrail`；
- 永久边界禁止 GitHub 专属 runtime、controller、run ID 或第二套 durable owner。

## 7. PR #103：activeQuery 跨域 selector

### 7.1 生产引用审计

受控 inventory CI run `30928295744` 扫描生产前端，确认真正属于 activeQuery 合同的引用只有：

1. `useWorkspaceControllers` 中“当前输入，否则上一轮 RAG query”的唯一推导；
2. `WorkspaceView` 中 Sources 检索消费 `activeQuery`；
3. 受控工具 invocation 使用 `query: activeQuery`。

以下 `input.trim()` 属于各自领域的提交校验，不属于 activeQuery：

- 单聊发送；
- ChatPanel 回车与发送按钮可用性；
- 群聊发送。

因此本批没有把聊天输入校验下沉到 selector，也没有改变发送行为。

### 7.2 单一 selector

新增 `frontend/src/app/activeQuerySelector.ts`：

```text
selectActiveQuery
-> trim 当前输入
-> 当前输入非空：返回当前输入
-> 当前输入为空：返回 trim 后的上一轮 RAG query
-> 两者都为空：返回空字符串
```

selector 是纯函数：

- 不引入 React hook；
- 不创建 state；
- 不持久化 query；
- 不拥有 RAG、Tool 或 Learning runtime；
- 只在跨域组合层 `useWorkspaceControllers` 求值一次。

### 7.3 消费边界

- `currentToolInvocation.query` 使用同一个 `activeQuery`；
- Sources 搜索继续调用 `ragController.search(activeQuery)`；
- `WorkspaceView` 不重新推导 query；
- EvidenceRuntime 与 ToolController 不新增 fallback 逻辑；
- 生产代码中只有 `useWorkspaceControllers` 声明 `const activeQuery =`。

### 7.4 回归合同

新增永久测试覆盖：

- 当前输入优先且去除首尾空白；
- 输入为空时回退到上一轮 RAG query；
- 两者均为空时返回空字符串；
- selector 不依赖 React；
- 生产代码只有一个 activeQuery 声明 owner；
- Tool invocation 与 Sources 搜索共享该结果；
- 旧内联推导表达式不得恢复。

## 8. PR #103 验证证据

代码基线 commit `484fe952a2860538f6bf10f83893f73f33bc22ef` 的 CI run `30928667587` 已完整通过：

- 全量 pytest；
- RAG K1 固定 corpus；
- Ruff；
- 项目打包；
- detect-secrets；
- expanded mypy baseline gate；
- 66 个前端测试文件、238 项测试；
- TypeScript / Vite production build；
- 38 条 desktop、mobile、360×520 Golden Journeys；
- 真实 FastAPI + SQLite 浏览器门禁。

说明：raw expanded mypy 仍有既有存量错误；通过的是仓库既定 baseline gate，未宣称 raw mypy 全量清零。

## 9. 下一执行顺序

### P1-R4：抽离 LearningSessionRuntime

```text
LearningSessionRuntime
-> chat / sessions / pedagogy / recovery / closure
```

第一批只移动 owner 与恢复端口：

- chat controller；
- active session / session summary selector；
- session restore / new / archive；
- pedagogy phase 与 RestoreCard 所需状态；
- closure / MemoryRun 的会话侧入口。

不得改变 session、turn、closure、MemoryRun、WorkspacePersistence 或 committed truth。

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
- 410 tombstone 只在明确迁移窗口结束后单独删除；
- 补 Firefox、WebKit 和实体手机抽样。

## 10. PR #103 合并条件

- 最新 head 完整 CI 全绿；
- 状态文档与代码事实一致；
- 不改变聊天发送、Sources 搜索或 Tool invocation 的用户可见语义；
- 不改变 WorkspacePersistence、API、SQLite schema 或 committed learning truth；
- PR 保持可回滚，范围只包含 activeQuery selector 与边界测试。

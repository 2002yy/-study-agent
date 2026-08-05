# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-08-05  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**P1 运行时 owner 与普通模式收口、P2-A 遗留样式 owner 清理均已完成，当前进入 P2-B 平台配置治理。**  
> 当前切片：**PR #110 已合并 `main`；NewsWorkspace 遗留样式清理与 WeChat 联网结果样式归属迁移完成，功能 merge SHA `6772b29e5a6457eecbc334e6bead7dfa1aa4e229`。**  
> 下一主线：**P2-B 平台配置与 CORS 单一 owner。**  
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
- 普通用户稳定入口为：学习会话、资料与来源、学习成果、设置。
- 群聊、受控工具与开发者诊断属于实验能力，只能从单一“实验室”入口进入，默认休眠。
- 产品面退场后，其 CSS、DOM class 和兼容命名必须同步证明 owner；不能只凭名称猜测“死代码”。

## 2. 已完成主线

### 2.1 遗留 News 产品面退场

- PR #97：联网研究产品表面集中化，merge SHA `3b1b9ef92c0496a659e2be3bf6075d529eb01826`；
- PR #98：主工作区遗留 NewsRun 状态清理，merge SHA `6b357bfe3b63d072f9374f19e149866171145b7a`；
- PR #99：前端兼容壳与无效设置合同清理，merge SHA `04770915e08528cb639edeba9839223072340f61`；
- PR #100：NewsWorkspace / NewsController 删除与 NewsRun 兼容边界，merge SHA `42ed5fdf01f25dd56f68215ac034f77bd117bb9d`；
- PR #110：退场样式与现役 WeChat lookup owner 清理，merge SHA `6772b29e5a6457eecbc334e6bead7dfa1aa4e229`。

旧 News 产品面不再拥有独立 runtime、drawer、DOM class、全局样式或 durable truth。保留的 `NewsRunResponse` 等 API 兼容类型不等于生产 DOM 或样式 owner。

### 2.2 EvidenceRuntime 收口

- PR #101：EvidenceRuntime 第一批 owner，merge SHA `a5db630c1758cbb5019b6fc035c90d26cf54ec05`；
- PR #102：Evidence recovery port 与源码证据 owner，merge SHA `d3da42dec0298138a48902cce860fc15f19eb808`；
- PR #103：单一 activeQuery 跨域 selector，merge SHA `22d3d0f562ed4a92b324c0f0d2c426332e8a2e47`。

### 2.3 LearningSessionRuntime 收口

- PR #104：LearningSessionRuntime 第一批 owner，merge SHA `b98a777f98e309b41a964c45c1c54c5ca0a54386`；
- PR #105：LearningSessionRuntime chat/session owner，merge SHA `43f6cfbada931ccbf58712c995dbd087f7e19048`；
- PR #106：LearningSessionRuntime 会话派生 view model，merge SHA `761ea7634c97b71de7f40eed15ab0b52229631c1`。

### 2.4 ExtensionRuntime 与普通模式收口

- PR #107：ExtensionRuntime controller / recovery owner，merge SHA `bb89b062747f3bb32cffa85f32d76e25dd19dcd3`；
- PR #108：Extension view model 与扩展面板装载边界，merge SHA `914e548144657cedf88eb0d497dcca0ac6252c2f`；
- PR #109：普通模式与单一实验室入口，merge SHA `af45cc1cb162b1ad409d1b2cfec2ab29c1f5cb9b`。

## 3. 当前运行时架构

```text
EvidenceRuntime
LearningSessionRuntime
ExtensionRuntime
        ↓ 窄端口
WorkspaceCoordinator
        ↓ view model
WorkspaceView
```

- **EvidenceRuntime**：RAG、上传、ResearchRun、RagQueryRun、RagWriteRun、Sources、EvidenceRecoveryPort。
- **LearningSessionRuntime**：ChatController、MemoryController、学习设置、会话、流式恢复、LearningClosure、LearningRecoveryPort、LearningArtifactPort。
- **ExtensionRuntime**：group、tool、workflow controller，扩展恢复、选择性加载、实验室 surface / capability view。
- **WorkspaceCoordinator**：只负责真正跨域的取消、清理和重置顺序，不拥有第二份领域状态。

## 4. P2-A 遗留样式与 owner 清理

### 4.1 审计结论

初始发现全局 `styles.css` 仍包含：

```text
.news-form
.news-result
.news-list
.news-item
```

逐文件核对后得到两类结论：

- `.news-form` 已无生产 DOM owner，属于真正死样式，已删除；
- `.news-result / .news-list / .news-item` 当时仍被现役 `WechatPanel` 的联网研究结果使用，不可直接删除。

因此本批执行“死样式删除 + 活样式 owner 迁移”，避免把仍在使用的群聊联网结果变成无样式内容。

### 4.2 WeChat 样式所有权迁移

现役 DOM 与样式统一迁移为：

```text
wechat-lookup-result
wechat-lookup-list
wechat-lookup-item
```

对应视觉声明位于：

```text
frontend/src/features/wechat-workspace/wechatLookup.css
```

`WechatPanel.tsx` 显式导入该文件。原有间距、边框、背景、链接强调、长文本换行、字号与状态文本样式保持不变；helper 名称也从 `newsItem*` 调整为 `lookupItem*`。

### 4.3 永久边界

`legacyNewsStylesBoundary.test.ts` 持续检查：

- 全局 `styles.css` 不得重新出现 `.news-form / .news-result / .news-list / .news-item`；
- 生产 TS/TSX 的静态 `className` token 不得重新出现上述旧类名；
- `WechatPanel` 必须显式导入局部 lookup CSS；
- `wechat-lookup-result / list / item` 必须同时存在于 owner DOM 和 owner CSS 中。

### 4.4 浏览器故障注入修正

旧 bootstrap fixture 曾使用 `**/wechat*` 注入 `/wechat` 接口故障，误把 `wechatLookup.css` 返回为 503，导致 Vite 根模块无法渲染。

当前 fixture 只在以下条件同时满足时注入隐藏能力故障：

- resource type 为 `fetch` 或 `xhr`；
- URL pathname 精确等于一个隐藏后端端点。

CSS、TS、图片和其他静态资源一律 fallback；真实 `/wechat`、`/tools`、`/memory` 等接口仍保持严格故障注入。

### 4.5 未改变边界

本批没有修改 API 路由或响应 schema、SQLite schema、durable entity、WorkspacePersistence v4、Learning / Evidence / Extension 业务行为、committed learning truth 或实验室默认休眠合同。

## 5. 必须保护的稳定闭环

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
| 长会话与窄屏 | desktop / mobile / 360×520 通过 | 恢复卡、宽代码、长链接、IME、滚动与刷新恢复 |
| 实验室休眠 | desktop / mobile / 360×520 通过 | 首页零扩展请求；选择后只加载对应能力 |
| WeChat lookup 样式 | desktop / mobile / 360×520 通过 | 局部 owner CSS 正常加载，无旧 `.news-*` DOM/CSS |

继续保护：RestoreCard、LearningStrip、SourcesPanel、MemoryRun、ResearchRun、RAG query/write run、WorkspacePersistence v4 和学习结束 committed truth。

## 6. PR #110 验证证据

- 有效红边界 commit：`4839ba42657e0475c8f0386226a490089f002cdc`；
- 有效红 CI：run `31005785577`；
- 代码基线 commit：`f1b7cacb106ef249ab68ab498ea395864a7636c1`；
- 代码基线 CI：run `31008156692`，结论 `success`；
- 最终 PR head：`9c326330d12fbaab8d5fbc8a283d668b82abc0e2`；
- 最终 head CI：run `31008811658`，结论 `success`；
- 功能 merge SHA：`6772b29e5a6457eecbc334e6bead7dfa1aa4e229`。

两轮绿色基线均完整通过：

- 全量 pytest；
- RAG K1 固定 corpus；
- Ruff；
- 项目打包；
- detect-secrets；
- expanded mypy baseline gate；
- 74 个前端测试文件、273 项测试；
- TypeScript / Vite production build；
- 41 条 desktop、mobile、360×520 Golden Journeys；
- 真实 FastAPI + SQLite 浏览器门禁。

说明：raw expanded mypy 仍有既有存量错误；baseline 为 `current=125, baseline=127, resolved=2`，未宣称 raw mypy 全量清零。

### 受控失败与审计修正

- commit `072c871fe5afa4eebd614ed228824dec4b8924fd` / run `31005285033`：首版测试自身存在转义语法错误，不作为有效红边界证据。
- commit `4839ba42657e0475c8f0386226a490089f002cdc` / run `31005785577`：有效红边界证明旧 CSS 存在，同时发现源码扫描过宽。
- runs `31006158792`、`31006427898`：推动扫描器收窄为逐文件静态 class token。
- commit `c29aff1d896dfb09f0d671a4ddfe90be77d09a5e` / run `31006769176`：文件级证据证明 `WechatPanel` 仍真实使用三个旧类名，纠正“全部是死 CSS”的初始判断。
- commit `79b02d3c8ab716db4badb46ff64a09e776546bcf` / run `31007505420`：74/273 与 build 通过，39/41 浏览器旅程通过；两项 bootstrap 因 `**/wechat*` 误拦截 `wechatLookup.css` 失败。
- commit `f1b7cacb106ef249ab68ab498ea395864a7636c1`：故障注入改为 fetch/xhr + 精确 pathname，随后 run `31008156692` 全绿。

## 7. 后续任务

### P2-B：平台配置与 CORS 单一 owner

1. 盘点 CORS 来源在应用工厂、环境配置、测试 fixture 与启动入口中的全部定义；
2. 建立单一解析 owner，显式区分开发、测试、生产来源；
3. 增加重复配置、空值、通配符与 credentials 冲突的永久边界；
4. 保持现有 FastAPI 路由和真实浏览器闭环不变。

### P2-C：兼容层退出

1. 迁移窗口结束后删除 410 tombstone；
2. 实验室入口稳定后删除旧 group / tools / timeline 新 UI adapter；
3. 每次删除前先证明无生产调用与无恢复数据依赖。

### P2-D：源码学习与验证增强

- 增强 GitHub symbol mapping 与 CI association，但继续写入通用 EvidenceSnapshot；
- Firefox 抽样；
- WebKit 抽样；
- 至少一台实体手机验证输入法、滚动、drawer、实验室与恢复流程；
- Chromium 全量 Golden Journeys 与真实 FastAPI + SQLite 门禁继续作为主回归基线。

## 8. 阶段判断

P2-A 已合并完成：

- 真正无 owner 的 NewsWorkspace 样式已删除；
- 仍在使用的 lookup 样式已迁移到 WeChat owner；
- 旧 `.news-*` CSS 与 DOM 命名受到永久边界保护；
- 浏览器故障注入不再误伤静态资源；
- 产品行为与持久化边界未改变。

当前没有待合并的功能 PR，主线已转入 P2-B 平台配置与 CORS 单一 owner。

# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-08-07  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**P1 运行时 owner 与普通模式收口、P2-A 遗留样式 owner 清理、P2-B 平台配置治理均已完成；当前推进 P2-C 兼容层退出。**  
> 当前切片：**Draft PR #114 已退出旧 `group / tools / timeline` drawer surface 兼容适配；最终代码 head `ffed392c8fccdf8aa93a4f2d57164a89199be726`，CI run `31181998973` 完整通过。P2-C 兼容层退出已完成代码与回归基线。**  
> 下一主线：**P2-D 源码学习与验证增强：GitHub symbol mapping + CI association、Firefox / WebKit 抽样，以及实体手机输入法、滚动、drawer、实验室与恢复验证。**  
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
- 平台配置必须由单一 owner 解析、验证和执行；应用装配层、测试和启动脚本不得各自维护第二套安全规则。

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

### 2.5 平台配置与 CORS owner

- PR #111：单一 CORS policy owner、环境分层、输入校验和永久边界；
- 代码基线 head `4a7f47614d466ba18713536469b34bcf9611a075`，CI run `31011592445` 完整通过；
- 最终 head `1b10820574c73fec864ab44f0e81c7c86ef02c23`，CI run `31012164767` 完整通过；
- 功能 merge SHA `6f743db0750e5cacf6370b2fee3cdd091b946f78`。

### 2.6 兼容层退出（进行中）

- PR #112：六条旧 News 410 tombstone 退出，旧路径转为真正未注册的 404；
- 有效红边界 commit `84248b1cff7f45f8a1c34ed09f9c0540cf66f60f`，CI run `31113239279`；
- 代码基线 head `5dae5af86500f878a8fee173625a47e146fa8303`，CI run `31114230217` 完整通过；
- 最终 head `6976fde10d2b201e0ba0019bcbab96939cb272c6`，CI run `31116107948` 完整通过；
- 功能 merge SHA `9482be8b5d73ba6a407a208c00af92ccc478ff96`；
- 现役 `/news/runs*` durable workflow、SQLite NewsRun 与恢复语义保持不变；
- PR #113：旧 News 阶段模型与兼容导出退出；
- 有效红边界 commit `b400b2db38393882c2db52aba38ee513ed9366d6`，CI run `31176698695`：905 项通过、1 项按预期失败；
- 红边界额外发现 `src/application/helpers.py::news_result_payload` 仍引用 `NewsSearchResponse`，确认其已无路由 owner 后同步退出；
- 最终代码 head `0d634dbcd0bd66bdab919efc9ba7cbbde69110cd`，CI run `31177047560` 完整通过；
- 最终 PR head `bc3c06f043eae5f195516741c88a45205e21864b`，CI run `31177513884` 完整通过；
- 功能 merge SHA `39e5efe91a75099b6cf5646aa9060d2945b5604c`；
- `NewsRun* / NewsLookup* / ResearchRun* / WebLookupRun*` 现役合同、durable `/news/runs*`、SQLite NewsRun 与恢复语义保持不变。
- PR #114：旧 Extension drawer surface 兼容适配退出；
- 审计确认 `group / tools / timeline` 仍是现役实验能力 ID 与 controller owner，不能删除；真正无 owner 的是旧 drawer surface 恢复适配。`WorkspacePersistence` 不持久化 `activeDrawer`，新 UI 只打开 `lab`；
- 有效红边界 commit `4a3e6138f7dbafb9a834ad3a8fdb232bae9ab785`，CI run `31179197610`：274 项通过、2 项按预期失败，且“现役 controller 必须保留”边界通过；
- 实现后 run `31179428611` 发现旧 `useExtensionRuntimeBoundary.test.ts` 仍断言 `EXTENSION_DRAWERS`；同步改为 capability 合同；
- head `a8f2533d945d182ee545cac2ac41625b2b5547e4` / run `31179663893` 中 276 个 Vitest 已全部通过，但 TypeScript build 进一步抓到 reducer 测试仍把 `"group"` 当作 `DrawerId`；改为真实 `lab` surface，不使用 cast 绕过类型；
- Extension drawer 代码基线 head `c65189c9c38e9b09abd11803d875a10e22b47a58`，CI run `31179908482` 完整通过；
- 状态同步验证暴露 360×520 长 URL Golden Journey 对 `overflowWrap` computed-style 的脆弱依赖；同类失败在 CI `31180448052`、`31180866352` 与 `31181558554` 复现。没有放宽为空串，而是改为真实行为合同：长 URL 必须形成多个 line box、消息体不得横向 overflow、链接边界不得越出消息体；CSS owner 不变；
- 最终代码 head `ffed392c8fccdf8aa93a4f2d57164a89199be726`，CI run `31181998973` 完整通过，41/41 Golden Journeys 与真实 FastAPI + SQLite 门禁均绿色；
- `DrawerId` 现只包含普通 drawer 与 `lab`；`group / tools / timeline` 只属于 `ExtensionCapabilityId`。`useGroupChatController / useToolController / useWorkflowController`、ExtensionRuntime 恢复端口和按需加载继续保留。

## 3. 当前运行时架构

```text
EvidenceRuntime
LearningSessionRuntime
ExtensionRuntime
        ↓ 窄端口
WorkspaceCoordinator
        ↓ view model
WorkspaceView

Platform configuration
        ↓ 单一解析 / 校验 owner
FastAPI middleware assembly
```

- **EvidenceRuntime**：RAG、上传、ResearchRun、RagQueryRun、RagWriteRun、Sources、EvidenceRecoveryPort。
- **LearningSessionRuntime**：ChatController、MemoryController、学习设置、会话、流式恢复、LearningClosure、LearningRecoveryPort、LearningArtifactPort。
- **ExtensionRuntime**：group、tool、workflow controller，扩展恢复、选择性加载、实验室 surface / capability view。
- **WorkspaceCoordinator**：只负责真正跨域的取消、清理和重置顺序，不拥有第二份领域状态。
- **CORS policy owner**：只由 `src/api/cors.py` 解析环境、规范化来源、拒绝危险组合并生成预检与响应头；`src/api/app.py` 只负责装配和调用。

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

## 5. P2-B 平台配置与 CORS 单一 owner

### 5.1 审计结论

原 `src/api/app.py` 同时存在两套规则：

1. Starlette `CORSMiddleware` 中硬编码 localhost / 127.0.0.1 的 5173 与 4173；
2. API security middleware 中再次读取 `STUDY_AGENT_CORS_ORIGINS`，手工处理 OPTIONS 和响应头。

这会造成来源定义、credentials、预检与普通响应分别受不同 owner 控制。启动脚本和 `src/config.py` 未发现第二套 CORS 解析，因此本批只收口真实重复 owner，不制造新的通用配置框架。

### 5.2 单一 policy owner

新增：

```text
src/api/cors.py
```

统一负责：

- `STUDY_AGENT_ENV` 环境识别；
- `STUDY_AGENT_CORS_ORIGINS` 来源解析；
- `STUDY_AGENT_CORS_ALLOW_CREDENTIALS` 布尔校验；
- origin 规范化和稳定去重；
- 预检 method / header 校验；
- 204 / 403 预检响应；
- 普通响应与 API token 401 的 CORS 头；
- `Vary: Origin` 合并。

`src/api/app.py` 不再导入或配置 `CORSMiddleware`，也不再维护硬编码来源、第二套解析函数或第二套响应头实现。

### 5.3 环境边界

未显式设置 `STUDY_AGENT_CORS_ORIGINS` 时：

```text
development -> localhost / 127.0.0.1 的 5173 与 4173
test        -> http://testserver
production  -> 无默认来源
```

补充语义：

- 环境变量缺失：使用当前环境默认来源；
- 环境变量存在但为空：显式关闭 CORS；
- 重复来源：规范化后按首次出现顺序去重；
- 非绝对 http(s) origin、携带用户信息、path、query 或 fragment：启动请求时 fail closed；
- wildcard `*`：必须独占来源列表，且 `allow_credentials=false`；
- 未知环境名和非法布尔值：fail closed，不静默退回开发配置。

### 5.4 永久边界

`tests/test_cors_policy.py` 持续检查：

- development / test / production 默认来源严格分离；
- 空值、重复来源、大小写与尾斜杠规范化；
- wildcard 与 credentials 冲突；
- wildcard 与具体来源混用；
- 非法环境、布尔值和 origin；
- `app.py` 不得重新出现 `CORSMiddleware`、本地来源字面量或 `Access-Control-Allow-Origin` 实现；
- 其他 `src/api` 模块不得新增第二个 `STUDY_AGENT_CORS_ORIGINS` owner 或响应头 owner。

### 5.5 未改变边界

- 允许来源的 preflight 仍返回 204；
- 拒绝来源的 preflight 仍返回 403；
- API token 的 Bearer / `X-Study-Agent-Token` 合同不变；
- `/health` 与静态资源公开边界不变；
- FastAPI 路由、响应 schema、SQLite schema、durable entity、Vite proxy、WorkspacePersistence v4、Learning / Evidence / Extension 行为和 committed learning truth 均未改变。

## 6. 必须保护的稳定闭环

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
| CORS 与 API gate | 真实全栈通过 | 单一 policy owner；合法来源 204/响应头，非法来源 403，token 401 行为不变 |
| 旧 News 路由退出 | 真实全栈通过 | 六条旧路径未注册并返回 404；现役 `/news/runs*` 与恢复闭环不变 |

继续保护：RestoreCard、LearningStrip、SourcesPanel、MemoryRun、ResearchRun、RAG query/write run、WorkspacePersistence v4 和学习结束 committed truth。

## 7. 验证证据

### 7.1 PR #110

- 有效红边界 commit：`4839ba42657e0475c8f0386226a490089f002cdc`；
- 有效红 CI：run `31005785577`；
- 代码基线 commit：`f1b7cacb106ef249ab68ab498ea395864a7636c1`；
- 代码基线 CI：run `31008156692`，结论 `success`；
- 最终 PR head：`9c326330d12fbaab8d5fbc8a283d668b82abc0e2`；
- 最终 head CI：run `31008811658`，结论 `success`；
- 功能 merge SHA：`6772b29e5a6457eecbc334e6bead7dfa1aa4e229`。

受控失败与审计修正：

- commit `072c871fe5afa4eebd614ed228824dec4b8924fd` / run `31005285033`：首版测试自身存在转义语法错误，不作为有效红边界证据；
- commit `4839ba42657e0475c8f0386226a490089f002cdc` / run `31005785577`：有效红边界证明旧 CSS 存在，同时发现源码扫描过宽；
- runs `31006158792`、`31006427898`：推动扫描器收窄为逐文件静态 class token；
- commit `c29aff1d896dfb09f0d671a4ddfe90be77d09a5e` / run `31006769176`：文件级证据证明 `WechatPanel` 仍真实使用三个旧类名，纠正“全部是死 CSS”的初始判断；
- commit `79b02d3c8ab716db4badb46ff64a09e776546bcf` / run `31007505420`：39/41 浏览器旅程通过；两项 bootstrap 因 `**/wechat*` 误拦截 `wechatLookup.css` 失败；
- commit `f1b7cacb106ef249ab68ab498ea395864a7636c1`：故障注入改为 fetch/xhr + 精确 pathname，随后 run `31008156692` 全绿。

### 7.2 PR #111

- 分支：`agent/cors-single-owner`；
- 代码基线 head：`4a7f47614d466ba18713536469b34bcf9611a075`；
- 代码基线 CI：run `31011592445`，结论 `success`；
- 最终 PR head：`1b10820574c73fec864ab44f0e81c7c86ef02c23`；
- 最终 head CI：run `31012164767`，结论 `success`；
- 功能 merge SHA：`6f743db0750e5cacf6370b2fee3cdd091b946f78`。

两轮基线均完整通过：

- 全量 pytest，包括新增 CORS policy 与单一 owner 边界；
- RAG K1 固定 corpus；
- Ruff；
- 项目打包；
- detect-secrets；
- expanded mypy baseline gate；
- 全量前端测试与 TypeScript / Vite production build；
- desktop、mobile、360×520 Golden Journeys；
- 真实 FastAPI + SQLite 浏览器门禁。

说明：raw expanded mypy 仍有既有存量错误；通过的是仓库既定 baseline gate，未宣称 raw mypy 全量清零。

### 7.3 PR #112

- 分支：`agent/remove-news-tombstones`；
- 有效红边界 commit：`84248b1cff7f45f8a1c34ed09f9c0540cf66f60f`；
- 有效红 CI：run `31113239279`，902 项通过、2 项按预期失败，证明旧路径仍注册；
- 首轮实现 head：`c908494620278bec292d5ea00b6a45234b44e8b1`；
- 首轮实现 CI：run `31113980495`，902 项通过、1 项失败，暴露兼容库存测试仍要求 tombstone 存在；
- 代码基线 head：`5dae5af86500f878a8fee173625a47e146fa8303`；
- 代码基线 CI：run `31114230217`，结论 `success`；
- 最终 PR head：`6976fde10d2b201e0ba0019bcbab96939cb272c6`；
- 最终 head CI：run `31116107948`，结论 `success`；
- 功能 merge SHA：`9482be8b5d73ba6a407a208c00af92ccc478ff96`。

代码基线与最终 head 均完整通过：

- 903 项 pytest；
- RAG K1 固定 corpus；
- Ruff、项目打包、detect-secrets；
- expanded mypy baseline gate；
- 全量前端测试与 TypeScript / Vite production build；
- desktop、mobile、360×520 Golden Journeys；
- 真实 FastAPI + SQLite 浏览器门禁。


### 7.4 PR #113 代码基线

- 分支：`agent/remove-legacy-news-models`；
- 有效红边界 commit：`b400b2db38393882c2db52aba38ee513ed9366d6`；
- 有效红 CI：run `31176698695`，905 项通过、1 项按预期失败；
- 红边界 offender 仅位于 `src/api/__init__.py`、`src/api/models/__init__.py`、`src/api/models/news.py` 与 `src/application/helpers.py`；
- 最终代码 head：`0d634dbcd0bd66bdab919efc9ba7cbbde69110cd`；
- 最终代码 CI：run `31177047560`，结论 `success`；
- 最终 PR head：`bc3c06f043eae5f195516741c88a45205e21864b`；
- 最终 PR CI：run `31177513884`，结论 `success`；
- 功能 merge SHA：`39e5efe91a75099b6cf5646aa9060d2945b5604c`。

最终代码基线完整通过：

- 全量 pytest，包括旧模型不得回流与现役 News 合同保护边界；
- RAG K1 固定 corpus；
- Ruff、项目打包、detect-secrets；
- expanded mypy baseline gate；
- 全量前端测试与 TypeScript / Vite production build；
- desktop、mobile、360×520 Golden Journeys；
- 真实 FastAPI + SQLite 浏览器门禁。

删除范围严格限定为 10 个旧阶段 Pydantic 模型、两层兼容 re-export 和无路由 owner 的 `news_result_payload`；没有删除或改写现役 durable NewsRun、NewsLookup、ResearchRun、WebLookupRun 合同。

## 8. 后续任务

### P2-C：兼容层退出

1. PR #112 已退出六条旧 News 410 tombstone，并由永久边界阻止旧路径回流；
2. PR #113 已退出 10 个旧 News 阶段模型、两层兼容导出和 `news_result_payload`，现役 durable / lookup / research 合同保持不变；
3. PR #114 已证明旧 `group / tools / timeline` drawer surface 无持久化或新 UI owner，并退出该兼容适配；
4. `group / tools / timeline` 继续作为实验能力 ID，由 ExtensionRuntime 的 group / tool / workflow controller 拥有，实验室入口仍默认休眠并按需加载；
5. P2-C 三个删除切片均保持 API、WorkspacePersistence、普通模式、Chromium Golden Journeys 与真实 FastAPI + SQLite 闭环不变，兼容层退出阶段完成。

### P2-D：源码学习与验证增强

- 增强 GitHub symbol mapping 与 CI association，但继续写入通用 EvidenceSnapshot；
- Firefox 抽样；
- WebKit 抽样；
- 至少一台实体手机验证输入法、滚动、drawer、实验室与恢复流程；
- Chromium 全量 Golden Journeys 与真实 FastAPI + SQLite 门禁继续作为主回归基线。

## 9. 阶段判断

P2-C 三个切片已完成代码与回归基线，兼容层退出阶段收口：

- 10 个旧 News 阶段 Pydantic 模型已从 owner 模块删除；
- `src/api/models/__init__.py` 与 `src/api/__init__.py` 不再提供这些兼容导出；
- 红边界发现的 `news_result_payload` / `_news_result_payload` 无路由 owner 残留已同步删除；
- `NewsRun* / NewsLookup* / ResearchRun* / WebLookupRun*` 继续受到永久测试保护；
- durable `/news/runs*`、SQLite NewsRun、恢复语义、前端和真实浏览器闭环均未回归；
- 旧 Extension capability drawer surface 已退出，`lab` 成为唯一实验 drawer；
- group / tool / workflow controller、恢复端口和按需加载继续由 ExtensionRuntime 拥有；
- 最终代码基线 `ffed392c8fccdf8aa93a4f2d57164a89199be726` / CI `31181998973` 完整通过；窄屏长 URL 门禁已改为直接验证换行与无横向溢出行为。

PR #114 状态同步 CI 通过后即可合并；合并后 P2-C 结束，进入 P2-D 源码学习与验证增强。

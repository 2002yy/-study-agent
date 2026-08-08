# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-08-08  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**P1 运行时 owner 与普通模式收口、P2-A 遗留样式 owner 清理、P2-B 平台配置治理、P2-C 兼容层退出均已完成；当前进入 P2-D 源码学习与验证增强。**  
> 当前切片：**P2-D-1 已进入 Draft PR #115：GitHub source search 增加确定性 lexical match → innermost symbol mapping，并把 commit-pinned GitHub Checks 关联到同一 EvidenceSnapshot；CI payload 必须与 snapshot SHA 精确一致。PR 当前 head `b1ae5623d716275b5f998e104b3b1bc5b218f1dd`，两次 GitHub Actions run `31192055532` / `31192056375` 均失败，因此本切片尚未收口、不得合并。**  
> 下一主线：**先修复 PR #115 CI，并在同一 head/同文件树上完成绿色验证；之后再进入 Firefox / WebKit 抽样与至少一台实体手机验证。**  
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

### 2.6 兼容层退出（已完成）

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
- 有效红边界 commit `4a3e6138f7dfafb9a834ad3a8fdb232bae9ab785`，CI run `31179197610`：274 项通过、2 项按预期失败，且“现役 controller 必须保留”边界通过；
- 实现后 run `31179428611` 发现旧 `useExtensionRuntimeBoundary.test.ts` 仍断言 `EXTENSION_DRAWERS`；同步改为 capability 合同；
- head `a8f2533d945d182ee545cac2ac41625b2b5547e4` / run `31179663893` 中 276 个 Vitest 已全部通过，但 TypeScript build 进一步抓到 reducer 测试仍把 `"group"` 当作 `DrawerId`；改为真实 `lab` surface，不使用 cast 绕过类型；
- Extension drawer 代码基线 head `c65189c9c38e9b09abd11803d875a10e22b47a58`，CI run `31179908482` 完整通过；
- 状态同步验证暴露 360×520 长 URL Golden Journey 对 `overflowWrap` computed-style 的脆弱依赖；同类失败在 CI `31180448052`、`31180866352` 与 `31181558554` 复现。没有放宽为空串，而是改为真实行为合同：长 URL 必须形成多个 line box、消息体不得横向 overflow、链接边界不得越出消息体；CSS owner 不变；
- 最终代码 head `ffed392c8fccdf8aa93a4f2d57164a89199be726`，CI run `31181998973` 完整通过，41/41 Golden Journeys 与真实 FastAPI + SQLite 门禁均绿色；
- 最终 PR head `8073da2adb033945d00d13e9db061ab9186b3d25`；同文件树状态同步 CI run `31182503935` 完整通过；功能 merge SHA `283c173e99f7a68985a536682155ce8948d54a70`；
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
- URL pathname 精确命中现役 API 路径；
- 不再以静态资源文件名包含 `wechat` 作为故障依据。

这样仍能验证隐藏实验能力失败时普通模式不受影响，同时不再污染 CSS / JS 模块加载。

## 5. P2-B 平台配置治理

### 5.1 单一 CORS policy owner

当前平台配置规则由 `src/api/cors.py` 单一拥有：

- 解析环境；
- 规范化 origins；
- 验证非法或危险组合；
- 生成 FastAPI CORS middleware 配置；
- 测试直接针对 policy owner，而不是复制一份规则。

`src/api/app.py` 只负责装配，不重新解释环境变量。

### 5.2 永久边界

- 生产环境不得回退到宽松 wildcard origin；
- `allow_credentials=True` 与 wildcard origin 不得组合；
- localhost / loopback 只允许在明确的本地开发环境中出现；
- 错误配置必须启动即失败，不允许静默降级；
- `.env.example`、启动脚本和测试不得成为第二套 CORS 真值 owner。

## 6. P2-C 兼容层退出

### 6.1 已完成退出

1. PR #112 已移除六条旧 News tombstone route；旧调用现在得到真正 404，而不是兼容 410；
2. PR #113 已退出 10 个旧 News 阶段模型、两层兼容导出和 `news_result_payload`，现役 durable / lookup / research 合同保持不变；
3. PR #114 已证明旧 `group / tools / timeline` drawer surface 无持久化或新 UI owner，并退出该兼容适配；
4. `group / tools / timeline` 继续作为实验能力 ID，由 ExtensionRuntime 的 group / tool / workflow controller 拥有，实验室入口仍默认休眠并按需加载；
5. P2-C 三个删除切片均保持 API、WorkspacePersistence、普通模式、Chromium Golden Journeys 与真实 FastAPI + SQLite 闭环不变，兼容层退出阶段完成。

## 7. P2-D：源码学习与验证增强

### 7.1 P2-D-1：GitHub symbol mapping + CI association（进行中）

Draft PR #115 已实现第一版：

- 对 GitHub source search 的宽 chunk 先做确定性 lexical match，优先把 identifier token 收窄到真实命中行；
- 将命中行映射到当前 snapshot 内**最内层**包含该位置的 parser-backed source symbol，不依赖 LLM 猜测；
- 无包含 symbol 时保留 path + line 的保守 fallback，不伪造 symbol；
- 复用现有 `RepositoryStructureIndex`、`evidence_for_range` 与 `pin_evidence_refs`，不新增第二套源码 parser；
- 将现有 `PaginatedGitHubChecksService` 的 commit-pinned checks 投影进源码搜索结果，不新增第二个 CI provider；
- CI payload 的 commit SHA 必须与 EvidenceSnapshot SHA 精确一致，避免“代码来自 A commit、CI 却来自 B commit”的伪关联；
- CI success / failure / pending / unavailable 与源码 evidence validity 分离：CI 失败不应让已经固定的源码证据本身失效；
- normal live snapshot path 自动带 CI；自定义 snapshotter 不应静默触发 live provider 调用，测试和特殊调用方需显式注入或请求 CI。

已增加的验证覆盖：

- identifier-token query → exact match line；
- 无 lexical hit → conservative chunk fallback；
- nested symbol → innermost containing symbol；
- 无 symbol → `None` fallback；
- exact-SHA CI enforcement；
- success / failure / pending 状态标准化；
- provider failure / no checks → unavailable；
- end-to-end source search symbol pinning；
- snapshot SHA 精确传给 CI service；
- CI failure 不覆盖 source evidence validity。

当前阻塞：

- PR #115 仍为 Draft；
- 当前 head：`b1ae5623d716275b5f998e104b3b1bc5b218f1dd`；
- GitHub Actions run `31192055532`、`31192056375` 均完成但结论为 failure；
- 因此上述实现目前只能视为 **attempted / partial**，不能写成 committed learning truth，也不能进入下一切片前宣称 P2-D-1 完成。

### 7.2 P2-D 后续切片

PR #115 绿色并合并后，按顺序推进：

1. Firefox 抽样；
2. WebKit 抽样；
3. 至少一台实体手机验证：输入法、滚动、drawer、实验室、恢复流程；
4. 验证结果继续回写现有 EvidenceSnapshot / 当前状态文档，不新建并列真值。

## 8. 当前缺口与执行顺序

### P0：先恢复 P2-D-1 绿色边界

1. 定位 PR #115 当前 GitHub Actions failure 的真实失败步骤；
2. 修复时不得放宽 exact-SHA、symbol owner 或 evidence-validity 边界来换绿；
3. 在同一实现文件树上完成完整 CI；
4. 只有 PR #115 合并后，才能把 P2-D-1 从 attempted / partial 改写为 committed。

### P1：跨浏览器与实体设备验证

- Firefox 抽样；
- WebKit 抽样；
- 实体手机窄屏、输入法、滚动、drawer、实验室与恢复；
- 对浏览器差异优先验证真实行为，不依赖脆弱 computed-style 字符串。

### P2：冻结项继续冻结

- Provider replay 扩展；
- 生产 claim UI；
- 群聊能力扩张；
- 新闻产品化；
- 可执行 agent。

这些能力只有在当前源码学习证据链和多端验证闭环稳定后才重新评估。

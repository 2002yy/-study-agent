# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-08-05  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**P1 运行时 owner 与普通模式收口已完成，转入独立、低耦合的 P2 清理与增强批次。**  
> 当前切片：**PR #109 已合并 `main`，P1-R6 单一“实验室”入口完成；功能 merge SHA `af45cc1cb162b1ad409d1b2cfec2ab29c1f5cb9b`。**  
> 下一主线：**P2-A 遗留产品面与无 owner 样式清理。**  
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

## 2. 当前总体进度

### 2.1 遗留产品面清理

- PR #97：联网研究产品表面集中化，merge SHA `3b1b9ef92c0496a659e2be3bf6075d529eb01826`；
- PR #98：主工作区遗留 NewsRun 状态清理，merge SHA `6b357bfe3b63d072f9374f19e149866171145b7a`；
- PR #99：前端兼容壳与无效设置合同清理，merge SHA `04770915e08528cb639edeba9839223072340f61`；
- PR #100：NewsWorkspace / NewsController 删除与 NewsRun 兼容边界，merge SHA `42ed5fdf01f25dd56f68215ac034f77bd117bb9d`。

旧 News 产品面已经不再拥有独立 runtime、drawer 或 durable truth。

### 2.2 EvidenceRuntime 收口

- PR #101：EvidenceRuntime 第一批 owner，merge SHA `a5db630c1758cbb5019b6fc035c90d26cf54ec05`；
- PR #102：Evidence recovery port 与源码证据 owner，merge SHA `d3da42dec0298138a48902cce860fc15f19eb808`；
- PR #103：单一 activeQuery 跨域 selector，merge SHA `22d3d0f562ed4a92b324c0f0d2c426332e8a2e47`。

EvidenceRuntime 已统一拥有 RAG、上传、联网研究、恢复和 Sources 数据加载。GitHub 源码学习继续落入通用 EvidenceSnapshot。

### 2.3 LearningSessionRuntime 收口

- PR #104：LearningSessionRuntime 第一批 owner，merge SHA `b98a777f98e309b41a964c45c1c54c5ca0a54386`；
- PR #105：LearningSessionRuntime chat/session owner，merge SHA `43f6cfbada931ccbf58712c995dbd087f7e19048`；
- PR #106：LearningSessionRuntime 会话派生 view model，merge SHA `761ea7634c97b71de7f40eed15ab0b52229631c1`。

LearningSessionRuntime 已统一拥有学习设置、ChatController、MemoryController、会话恢复、closure 和学习会话 view。WorkspaceView 不再现场推导 active session、summary、新会话确认或中断恢复动作。

### 2.4 ExtensionRuntime 与普通模式收口

- PR #107：ExtensionRuntime controller / recovery owner，merge SHA `bb89b062747f3bb32cffa85f32d76e25dd19dcd3`；
- PR #108：Extension view model 与扩展面板装载边界，merge SHA `914e548144657cedf88eb0d497dcca0ac6252c2f`；
- PR #109：普通模式与单一实验室入口，merge SHA `af45cc1cb162b1ad409d1b2cfec2ab29c1f5cb9b`。

ExtensionRuntime 已拥有 group、tool、workflow controller，恢复端口、按需加载、面板 view 和实验室当前能力选择。跨域组合层只消费窄 `ExtensionCoordinatorPort`。P1 运行时 owner 与普通模式收口已完成，当前没有待合并的功能 PR。

## 3. P1-R6 单一实验室入口

### 3.1 普通菜单

普通学习菜单只直接展示：

- 资料与来源；
- 学习成果；
- 设置；
- 一个明确标注为实验功能的“实验室”入口。

“群聊讨论 / 受控工具 / 开发者诊断”不再作为三个并列菜单项暴露。

### 3.2 实验室内部导航

打开实验室后再选择：

```text
实验室
├─ 群聊讨论
├─ 受控工具
└─ 开发者诊断
```

从具体能力返回实验室时，键盘焦点恢复到刚才选择的能力卡片。实验室卡片具备桌面、移动端和 360×520 窄屏下的触控尺寸、换行与焦点样式。

### 3.3 默认休眠与选择性加载

- 打开实验室首页时，`activeCapability = null`；
- 首页不请求 `/wechat`、`/tools` 或 `/workflows/runs`；
- 选择群聊时只加载 wechat；
- 选择受控工具时只加载 tools；
- 选择开发者诊断时只加载 workflows；
- 普通 drawer 不触发任何扩展 loader。

### 3.4 短期兼容

- 新 UI 只发出集中式 `LAB_DRAWER`；
- 旧 `group / tools / timeline` drawer ID 仍可被读取，作为恢复链接与旧调用的短期兼容 surface；
- 兼容 surface 直接映射到原能力，不经过实验室首页；
- 本批不修改 WorkspacePersistence schema v4、API、SQLite schema 或 durable entity。

## 4. 当前运行时架构

```text
EvidenceRuntime
LearningSessionRuntime
ExtensionRuntime
        ↓ 窄端口
WorkspaceCoordinator
        ↓ view model
WorkspaceView
```

### EvidenceRuntime

拥有 RAG、上传、ResearchRun、RagQueryRun、RagWriteRun、Sources 数据加载、EvidenceRecoveryPort 和给 Learning 使用的窄证据端口。

### LearningSessionRuntime

拥有 ChatController、MemoryController、学习设置、会话与消息、流式恢复、LearningClosure、LearningRecoveryPort、LearningArtifactPort 和会话派生 view。

### ExtensionRuntime

拥有 group、tool、workflow controller，扩展恢复、选择性加载、activeQuery 消费、实验室 surface / capability view 和跨域协调窄端口。

### WorkspaceCoordinator

只负责真正跨域的取消、清理和重置顺序，不拥有任何领域 controller 的第二份状态。

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

继续保护：RestoreCard、LearningStrip、SourcesPanel、MemoryRun、ResearchRun、RAG query/write run、WorkspacePersistence v4 和学习结束 committed truth。

## 6. PR #109 验证证据

- 首个永久红边界 commit：`dad38e425fe161ee83ab53e94b6d1d47ce438c7d`；
- 代码基线 commit：`53ddc3d25be6d68b5a80088ff421d7e569b064fb`；
- 代码基线 CI：run `31002902303`，结论 `success`；
- 最终 PR head：`68f6352bb1a0b0de7f9b7caddc773810cb8ba8d9`；
- 最终 head CI：run `31004145615`，结论 `success`；
- 功能 merge SHA：`af45cc1cb162b1ad409d1b2cfec2ab29c1f5cb9b`。

两轮绿色基线均通过：

- 全量 pytest；
- RAG K1 固定 corpus；
- Ruff；
- 项目打包；
- detect-secrets；
- expanded mypy baseline gate；
- 73 个前端测试文件、270 项测试；
- TypeScript / Vite production build；
- 41 条 desktop、mobile、360×520 Golden Journeys；
- 真实 FastAPI + SQLite 浏览器门禁。

说明：raw expanded mypy 仍有既有存量错误；baseline 为 `current=125, baseline=127, resolved=2`，未宣称 raw mypy 全量清零。

### 受控失败记录

- CI `31001393724`：永久红边界按预期失败；四项新断言证明旧 UI 仍直出三个实验入口，尚无实验室 panel、首页休眠或兼容 surface 合同。
- CI `31001749588`：实现与 TypeScript 基本成立；仅三项旧静态测试仍要求 `activeDrawer` 直接装载，并继续寻找旧菜单入口。
- CI `31002211520`：73 个前端文件、270 项测试与 build 已通过；浏览器失败来自两处旧入口旅程、专项测试误把实验室副标题识别为直接菜单项，以及一次窄屏长链接样式读取波动。
- commit `53ddc3d25be6d68b5a80088ff421d7e569b064fb` 更新真实浏览器合同并保持原窄屏断言不变，随后 41 条旅程与真实栈全部通过。
- CI `31003422141`：文档 head 的 73/270、build 与 40/41 浏览器旅程通过；唯一失败是窄屏长链接在 DOM / 样式恢复切换后立即读取 `getComputedStyle().overflowWrap` 偶发得到空字符串，几何边界仍正确，真实栈因浏览器 Gate 未继续。
- commit `c6244c41576fa2366074ff70c6670db7c48a1005` 在读取指标前等待同一严格样式合同达到 `anywhere` 或 `break-word`，保留后续几何与枚举双重断言；最终 run `31004145615` 完整通过。

这些修正没有放宽默认休眠、选择性加载、恢复、持久化、移动端或 committed learning truth 边界。

## 7. 后续任务

### P2-A：遗留产品面与样式清理

1. 盘点并删除 NewsWorkspace 退场后无 owner、无 DOM 命中的 CSS selector；
2. 为删除项增加静态引用检查和桌面 / 移动端视觉回归；
3. 不修改现有 Learning、Evidence 或 Extension 产品行为。

### P2-B：平台配置 owner

1. 将 CORS 配置统一到单一 owner；
2. 保留开发、测试和生产来源的显式合同；
3. 增加错误配置与重复配置边界测试。

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

P1 运行时 owner 与普通模式收口已经完成：

- 领域 controller 不再散落；
- 跨域组合只经过窄端口；
- WorkspaceView 只消费 view model；
- 普通学习入口稳定；
- 实验能力集中且默认休眠。

后续不再进行大规模运行时搬迁，转为独立、可验证、低耦合的 P2 清理与增强批次。
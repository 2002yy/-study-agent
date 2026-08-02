# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-08-03
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**仅检查和改进 Study Agent 本体的代码功能、核心学习流程与桌面/移动端体验。**  
> 冻结边界：**Provider replay 扩展、生产 claim producer / claim UI、生产 ChatTurn 接入、群聊能力扩张、新闻产品化与可执行 agent 均不是当前开发主线。**
> 当前切片：**P1-R1 联网研究阶段解释已实现，PR #96 的远程完整 CI 已通过；PR 仍为 Draft，等待用户决定是否合并。**

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
- 当前冻结横向功能扩张，以主学习闭环是否清晰、可恢复、可验证、可在窄屏操作为判断标准。

## 2. 当前核心功能基线

- 当前核心功能基线 merge SHA：`b4a996bbed74beca5a861490e39b4b67d4abc8b5`；
- PR #92：修复失败刷新恢复与长会话恢复入口，merge SHA `47d252e0bd33126022d76de324af8d67e62dac5e`，最终 CI #1714；
- PR #93：修复联网研究取消状态收口，merge SHA `b4a996bbed74beca5a861490e39b4b67d4abc8b5`，最终 CI #1731；
- 两批均只处理 Study Agent 核心流程，没有接入新的生产 Provider、claim UI 或可执行 agent。

## 3. 已验证的产品闭环

| 闭环 | 当前结论 | 真实证据边界 |
|---|---|---|
| 首次开始 | 真实全栈通过 | React -> FastAPI -> SQLite；无需先做配置决策 |
| 返回学习 | 可恢复并继续 | 恢复目标、上下文和下一步，继续后刷新仍一致 |
| 上传资料学习 | 真实全栈通过 | 文件合同、解析、document/revision、索引、EvidenceSnapshot、刷新恢复 |
| 联网研究 | 取消与恢复闭环通过 | 慢研究 -> 请求取消 -> durable `cancelled` -> 刷新 -> 同 run 从 checkpoint 重试完成 |
| 源码学习 | 展示与恢复可用 | symbol mapping 与 CI association 精度仍不足以证明稳定源码关系理解 |
| 理解验证 | 真实全栈通过 | 空泛“懂了”不提交；正确推理才进入 committed truth 和 transfer |
| 学习结束 | 真实全栈通过 | closure preview、确认写入、summary、刷新、归档并新建 |
| 中断续写 | 真实全栈通过 | partial 保存为 `interrupted`；刷新后同 turn 续写；前缀不重复；只提交一次 |
| 零 token 失败 | 真实全栈通过 | `failed` 刷新后仍可重新生成；retry child 完成后 parent `superseded` |
| 长会话恢复 | desktop / 390×844 / 360×520 通过 | 恢复卡位于当前 conversation viewport，不再落在历史顶部 |
| 窄屏复杂内容 | 360×520 通过 | 长中文、长 URL、宽代码、IME、真实滚动、回到最新与刷新恢复 |

## 4. 最近两批核心修复

### 4.1 失败刷新恢复与长会话入口

PR #92 修复两个 P0 恢复缺口：

- 最新 turn 为 `failed` 时，刷新后恢复为 retry-only 状态；
- 零 token 失败不显示“从断点继续”，不伪造部分回答；
- `interrupted` 仍保留同 turn 断点续写；
- 恢复卡移动到最新对话上下文附近并在 viewport 内保持可见；
- failed-before-reply 不显示“部分回答已保留/复制”；
- 360×520 首轮门禁发现恢复卡顶部越界约 21px，最终通过短屏紧凑布局修复，而不是放宽断言；
- 后端 `failed` / `interrupted` durable status 和 committed learning truth 均未改变。

### 4.2 联网研究取消状态收口

PR #93 修复 ResearchRun 两阶段取消在前端没有收口的问题：

- 服务端首次取消响应仍为 `running` 时，前端持续读取同一 durable run；
- 只有 run 离开 `running` 后才解除忙碌状态；
- 先发服务端取消请求，再中止浏览器中的旧执行请求；
- 取消期间 `useInChat=false`，已有来源不会自动进入下一轮聊天；
- 等待预算耗尽时保留 run ID，并提示刷新后继续查看或重试；
- 刷新可恢复 `cancelled`、查询尝试和已有 checkpoint；
- 同一查询从已取消 run 的 checkpoint 重试，不创建重复 ResearchRun；
- 新增 desktop 与 390×844 真实全栈旅程，不通过 `page.route` 伪造核心 ResearchRun API。

本批门禁连续发现并修复两个测试基础设施问题：

1. 静态 owner 测试只读取旧控制器入口，迁移为稳定 re-export 后需要同时审查入口与实现文件；
2. 新增 real-stack 文件最初被普通 fixture Playwright 项目误收录，最终加入统一 `REAL_STACK_TESTS` 排除清单，由专用真实全栈配置运行。

### 4.3 P1-R1 联网研究阶段解释（远程 CI 已通过）

当前活动分支 `codex/p1-r1-research-stage-explanations` 收口“工程状态不可理解”的一处核心语义：

- `partial` ResearchRun 保留查询、来源与 checkpoint，但不再自动作为下一轮聊天资料；学习者可显式选用，或重试补全；
- 聊天恢复卡与群聊研究面板明确说明部分结果、已保留的查询/来源和重试语义；
- Windows 真实全栈重置在释放缓存连接后再删除 SQLite 文件，desktop 与 390×844 可连续执行；
- 已通过前端 222 项单元测试、TypeScript/Vite production build，以及 ResearchRun 取消—刷新—同 run 重试的 desktop 与 390×844 真实全栈旅程；
- PR #96 的两项 GitHub Actions CI 已通过，覆盖全量 pytest、RAG K1、Ruff、打包、detect-secrets、mypy、前端构建与两类浏览器门禁；该 PR 仍为 Draft，未经用户确认不得合并。

## 5. 当前质量门禁

CI #1731 完整通过：

- 全量 pytest；
- RAG K1 固定 corpus 基线；
- Ruff、项目打包检查、detect-secrets；
- expanded mypy baseline；
- 前端单元测试、TypeScript 与 Vite production build；
- 38 条 Chromium fixture / narrow Golden Journeys；
- desktop 与 390×844 专用真实全栈浏览器门禁，包含新增 ResearchRun 取消旅程。

测试边界：

- 浏览器门禁替换外部模型、搜索或文件来源时，仍保留生产 route、application service、transaction 和 repository；
- real-stack 核心 API 不使用 `page.route` 伪造；
- 每个真实旅程使用隔离的临时 SQLite、RAG、memory 和输出目录；
- 失败必须暴露真实产品或测试建模问题，不通过降低断言强行变绿。

## 6. 当前真实指标

### RAG K1 固定回归

- 12 documents；30 retrieval cases / 26 answerable；10 answer-quality gold；
- source recall@K `0.923077`；nDCG `0.903600`；adaptive recall@K `0.942308`；
- multi-source recall@K `0.9`；stale / forbidden leakage `0`；
- deterministic answerable `26/26`；unanswerable block `4/4`。

这些数字只代表固定 corpus 回归合同，不代表真实模型最终回答质量。

### 成功体验证据

- 23 张已保留的真实 viewport PNG：desktop 1440×900 共 9 张、mobile 390×844 共 9 张、narrow 360×520 共 5 张；
- 360×520 对话可视高度 251px；
- 真实 wheel 滚动后距底部 700px；“回到最新”和刷新后均恢复到 0；
- 宽代码只在代码块内部横向滚动；长 URL 在消息边界内换行；
- 浏览器 composition 事件验证：组合期间 Enter 不提交，composition end 后只提交一次。

### 仍属冻结的评测能力

仓库中仍保留 record-only AnswerClaim real-provider replay 与方舟 smoke/full 运行合同，但：

- 实际 real-provider smoke / full artifact 均尚未执行；
- 不存在可报告的真实 claim coverage、unsupported-claim rate、citation alignment、latency、usage 或成本数字；
- 这些合同不是当前开发主线，不得推动生产 Provider、claim UI 或 ChatTurn 写入扩张。

## 7. 当前缺口

**P1：核心功能与体验**

1. 继续逐批检查首次学习、返回学习、上传资料、理解验证和学习结束的真实交互细节，优先修阻断和高频困惑；
2. 根据用户决定将 PR #96 继续保持 Draft、转 Ready 或合并；合并前不得扩大 P1-R1 范围；
3. 对实体安卓/iOS 输入法、软键盘安全区、触摸惯性和返回键做实机抽样；
4. 加强源码学习的 symbol mapping、CI association precision 与 partial-result 用户解释。

**P2：兼容性与维护**

1. 增加 Firefox / WebKit 兼容抽样；
2. 清理 README 中旧首页、Streamlit、群聊、新闻和当前 React 工作台之间的表述差异；
3. 继续统一 Golden Journey 的点击、决策、surface、恢复和耗时指标。

## 8. 执行规则

- 只从 Study Agent 核心学习流程出发选择下一批，不因为仓库已有实验合同就继续扩张；
- 优先级：阻断 -> 高频体验问题 -> 状态真值错误 -> 可维护性 -> 低频兼容性；
- 每批使用独立小分支 -> Draft PR -> 完整门禁 -> 全绿合并；
- 新功能或修复必须同时给出单元、真实全栈或人工验收边界；
- 不报告未实际运行的 Provider 指标，不把 deterministic / synthetic 结果冒充真实模型质量。

## 9. 文档规则

- 当前状态只更新本文件；
- `ARCHITECTURE_STATUS.md` 只维护稳定 owner / 边界；
- `STATE_MODEL.md` 只维护稳定数据模型；
- 不新增并列长期状态文档；代码、CI、分支和 PR 变化必须同步本文件。

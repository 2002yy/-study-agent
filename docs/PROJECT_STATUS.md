# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-07-27  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**学习真值、浏览器旅程、核心首屏和资料三层收口已进入 `main`；P0-A5 review-first 与 P0-A6 唯一 SessionNavigator 已在当前分支完成。**
> 当前代码切片：`codex/p0-a5-a6-review-session-owner`。

本文件只维护当前事实、指标、缺口、顺序和门禁。不得新增并列长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT 文档。

## 1. 产品边界

```text
当前目标 -> 教学/练习 -> 资料与证据 -> 理解验证
-> 已确认/未解决 -> 下一步 -> 整理与恢复
```

- RAG 服务于围绕自己的资料学习；Web Research 服务于需要外部事实的任务。
- GitHub 是源码学习的证据来源，不是第二个执行产品或顶级工作台。
- Memory 是连续性基础设施；Workflow 只属于高级诊断。
- React 是交互和可重建缓存；SQLite durable entities 是运行真值。
- planned / attempted / failed 不得覆盖 committed truth。
- 当前冻结横向扩展，以核心学习闭环是否真实可用为判断标准。

## 2. 已完成

- TaskContract、LearningClosureRun、ThreadSummaryState、结构化恢复卡；
- RAG K1a-K1e、EvidenceSnapshot、ResearchRun source truth；
- EvidenceTrail 普通/诊断分层；
- AnswerClaimSnapshot v1 与 record-only 离线评测；
- 生产路径学习验证 E2E；
- Chromium desktop / 390px 五类 Golden Journey；
- 核心首屏按需加载与隐藏功能错误隔离。

已合并：

- PR #61 `597006e99919ea7e5f5b02f01b1536b446da9a55`，CI #1317；
- PR #62 `fcfb9bc66750d10c822306fae735424e658b19ef`，CI #1340；
- PR #63 `f1b2a4f9d481a16e5c93e6ac8fb4c0f9ee2f45c2`，CI #1357；
- PR #64 `451bc4a78fc3eda6219083371591aa46c8e62900`，CI #1368；
- PR #65 `b700da1a2751769959ae1b41966f5da0a854162a`，CI #1389；
- PR #66 `b1ac5a841aab5948b4fee623aeaea1d87e1b8af9`，CI #1407；
- PR #67 `c19d5070b9bcf73ed46a81731bbeae842b757208`，CI #1416；
- PR #68 `4da85690043e9144b18dabaf0b4d2359c16eaeb8`，CI #1437；
- PR #69 `04ac7d59c2f7ed76eee7192c3500ebbb6bc6d286`，CI #1449；
- PR #70 `ccdea493d8d0119e9ba0b9c203a06b5f14de1229`，CI #1462；
- PR #71 `cca4bdfac775909956f90aeaddc5bcfc96597e12`，main CI #30263505859。

## 3. 当前真实指标

### RAG K1

- 12 documents；30 retrieval cases / 26 answerable；10 answer-quality gold；
- source recall@K 0.923077；nDCG 0.903600；adaptive recall@K 0.942308；
- multi-source recall@K 0.9；stale / forbidden leakage 0；
- deterministic answerable 26/26；unanswerable block 4/4。

这些是固定 corpus 回归合同，不代表真实模型最终质量。

### GitHub replay

- 15 repos；17 cases；15 Provider replay；partial rate 0.7647；
- symbol mapping P/R/F1 0.625 / 0.4545 / 0.5263；
- CI association P/R/F1 0.3529 / 1.0 / 0.5217。

G10-D 可执行代理继续冻结。

## 4. P0-A1 已完成：学习验证

真实 FastAPI -> policy ChatService -> TaskContract -> semantic/deterministic pedagogy -> SQLite -> SessionService 链已经验证：

- 正确且有推理的解释进入 committed truth；
- “懂了”、已知误解、semantic timeout、非法 evidence ref 不推进；
- interrupted continuation 与 failed retry 只提交一次；
- 刷新恢复与 SQLite 真值一致。

## 5. P0-A2 已完成：真实浏览器 Golden Journeys

| journey | clicks | decisions | surfaces | recovery | keyboard | refresh | overflow |
|---|---:|---:|---:|---:|---|---|---|
| first answer | 0 | 0 | 1 | 0 | pass | pass | none |
| returning learning | 1 | 1 | 1 | 1 | n/a | pass | none |
| chat 503 recovery | 1 | 0 | 1 | 1 | n/a | pass | none |
| material learning + adopted evidence | 3 | 1 | 1 | 0 | n/a | pass | none |
| web research recovery + adopted evidence | 2 | 0 | 1 | 1 | n/a | pass | none |
| source-code learning + adopted evidence | 2 | 0 | 1 | 0 | n/a | pass | none |

普通 EvidenceTrail 只显示 server-owned selected/adopted evidence；所有旅程刷新恢复，390px 无横向溢出。

## 6. P0-A3 已完成：核心首屏按需加载

- 干净首屏只请求 `/health`、`/sessions`、`/runtime/settings`；
- RAG、知识库、工具、workflow、memory、wechat 未打开时零请求；
- 对应抽屉打开后只加载自身数据；
- 隐藏接口模拟 503 时，desktop 和 390px 普通首屏不显示全局错误；
- core refresh 不清空 feature data，持久化 active run/session 恢复保留；
- PR #70 最终 CI #1462 全绿。

## 7. P0-A4 已完成：资料与来源三层收口

单一 Sources 抽屉内部现在分为：

1. **本次回答依据**：默认层，只读取当前回答的 server-owned EvidenceSnapshot；只显示 lifecycle `selected` 或 pedagogy 明确引用的证据；
2. **我的资料**：只显示知识库文档、active/superseded/excluded 状态、恢复、删除和重建；
3. **检索诊断**：显示 candidate/read/rejected/selected 生命周期、排序、相关度、命中词、评分明细、来源片段和模型上下文。

已验证边界：

- 前端没有根据检索排序自行产生 selected evidence；
- 手动 `ragSearch` 结果只进入诊断层；
- 默认层不含 candidate、score、context 或 document management；
- 没有 selected evidence 时显示明确空状态，不回退展示候选；
- 资料层不显示检索候选与分数；
- 诊断层包含完整证据生命周期和检索内部信息；
- desktop 与 390px 真实 Sources 抽屉 tab 切换、server-owned adopted evidence 和无横向溢出均通过。

### 门禁与修正

- CI #1473：后端/RAG/类型全绿；旧资料资格测试仍假设文档管理默认展开，新测试未 cleanup，浏览器未执行；只更新测试操作与隔离；
- CI #1477：所有组件、类型与构建全绿，原有 16 个浏览器用例通过；新增两项只因测试错误地在聊天页等待证据标题而失败；
- CI #1479：全部后端、RAG、Ruff、package、secrets、mypy、Vitest、Vite 和 18 个 desktop/mobile Chromium 用例全绿；
- 实现 head `8d8e25ddf80985a5dedd90d33f1bfc5ef62f1aa3`；
- PR #71 已合并，merge SHA `cca4bdfac775909956f90aeaddc5bcfc96597e12`；main CI #30263505859 全绿。

## 8. P0-A5 / P0-A6 已完成：学习结束 review-first + 唯一 SessionNavigator

分支：`codex/p0-a5-a6-review-session-owner`。

已实现：

1. 默认结束流程先展示本次确认、剩余缺口、建议下一步和确认后的保存影响；
2. 长期学习成果仍由冻结的 `LearningClosureRun` / `MemoryRun` 驱动，只有用户确认后才提交；
3. Memory target、append/replace、evidence refs 和 pending observation 只留在折叠的高级明细；
4. 提交完成态只保留一张学习者可理解的摘要卡，高级写入工作台不会自动展开；
5. “继续当前”只关闭成果抽屉，“归档并新建”明确归档旧会话后创建新会话；
6. `useSessionNavigator` 统一拥有搜索、分组、重命名、恢复确认和归档确认；
7. desktop sidebar 与移动抽屉都渲染同一 `SessionNavigator` / `SessionNavigatorBody`；
8. `SessionSidebar` 与 `SessionsPanel` 只保留薄兼容包装，不再拥有交互状态或 API 调用；
9. Playwright 测试依赖已进入项目 devDependencies，本地可显式使用系统 Chrome，CI 默认浏览器行为不变。

验证：

- 前端 Vitest：58 files / 203 tests 全绿；
- 后端学习闭环、会话导航与 summary status：21 tests 全绿；
- Vite production build 通过，保留既有单 chunk 大于 500 kB 警告；
- review -> confirm -> archive/new 在 desktop Chromium 与 390px mobile Chromium 全绿；
- 共享 SessionNavigator 的 desktop sidebar 与 mobile drawer 搜索旅程全绿；
- 两条浏览器旅程均无横向溢出。

## 9. 后续顺序

1. P0-A7 `ux/onboarding-settings-progressive-disclosure`：新手与设置渐进披露；
2. P0-A8 `a11y/focus-feedback-responsive`：焦点、复制、上传、触控、软键盘和溢出。

## 10. 审计完成标准

- 学习真值门禁成立；五类 Golden Journey 在 desktop 和 390px 全部通过；
- first answer 无强制配置；学习恢复、资料学习、联网研究不超过两层 surface；
- 刷新、网络失败和 stream interruption 有明确恢复路径；
- 首屏不依赖隐藏实验模块；普通证据层只显示 adopted evidence；
- 默认结束流程不要求理解 Memory 文件；桌面/移动使用同一会话 owner；
- 键盘、焦点、复制、上传和窄屏问题有自动回归；全量 CI 通过。

## 11. 审计期间冻结

真实 Provider claim replay、生产 claim producer、claim UI、Streamlit 清理、RAG-K1f、RAG-K2、自适应 LearningPlan、G10-D 可执行代理继续冻结。

## 12. 当前执行状态

- 当前分支：`codex/p0-a5-a6-review-session-owner`；
- 基线：PR #71 merge SHA `cca4bdfac775909956f90aeaddc5bcfc96597e12`，main CI #30263505859 全绿；
- 当前阶段：P0-A5 review-first 与 P0-A6 SessionNavigator single owner 已完成并通过本地门禁；
- 下一动作：进入 P0-A7 新手与设置渐进披露；提交前再运行完整 browser suite；
- 合并策略：独立小分支 -> Draft PR -> 完整门禁 -> 全绿合并。

## 13. 文档规则

- 当前状态只更新本文件；status-only 更新留在 active branch；
- `ARCHITECTURE_STATUS.md` 只维护稳定 owner/边界；`STATE_MODEL.md` 只维护稳定数据模型；
- 不新增并列长期状态文档；代码、CI、分支和 PR 变化必须同步本文件。

# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-07-28  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**P0-A1–P0-A6 已完成并进入 `main`；当前执行 P0-A7 新手与设置渐进披露。**  
> 当前代码切片：`ux/onboarding-settings-progressive-disclosure`。

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

## 2. 已完成主链

- TaskContract、LearningClosureRun、ThreadSummaryState、结构化恢复卡；
- RAG K1a-K1e、EvidenceSnapshot、ResearchRun source truth；
- AnswerClaimSnapshot v1 与 record-only 离线评测；
- 生产路径学习验证 E2E；
- desktop / 390px 五类 Golden Journey；
- 核心首屏按需加载与隐藏功能错误隔离；
- 资料与来源三层收口；
- 学习结束 review-first；
- desktop / mobile SessionNavigator 单一交互 owner。

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
- PR #71 `cca4bdfac775909956f90aeaddc5bcfc96597e12`，CI #1481；
- PR #72 `3796bfe3bbc7c83feac9eeb9f195803a5ed57228`，最终 CI #1496。

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

## 4. P0-A1–P0-A4 已完成

- 真实 FastAPI -> ChatService -> TaskContract -> pedagogy -> SQLite -> SessionService 学习真值链已验证；
- 正确解释进入 committed truth，“懂了”、误解、semantic timeout 和非法 evidence ref 不推进；
- 首次问答、返回学习、503 恢复、资料学习、联网研究和源码学习在 desktop / 390px 全部通过；
- 首屏只依赖 `/health`、`/sessions`、`/runtime/settings`；隐藏模块按需加载；
- Sources 抽屉分为“本次回答依据 / 我的资料 / 检索诊断”，普通层只显示 adopted evidence。

## 5. P0-A5 / P0-A6 已完成

PR #72 在用户提交 `fae13fc90345a9147a3f08b9c8f156dc43300ab9` 基础上完成审计修正：

- closure 默认层的“本次确认 / 还需继续”优先读取 committed structured state，不把模型生成的 `progress` 候选直接包装成 committed truth；
- 建议下一步与保存范围继续读取冻结候选和 linked MemoryRun；
- Memory target、append/replace、refs、confidence 和 pending observation 留在高级明细；
- desktop sidebar 与 mobile drawer 共享一个 SessionNavigator interaction store；
- query、rename、group 和 archive-confirm state 不再分叉；
- CI #1492 只暴露测试未 cleanup；修复测试隔离后，CI #1494 与最终 CI #1496 全绿；
- 58 files / 205 Vitest、全部 desktop/390px Playwright journeys、pytest、RAG K1、Ruff、package、secrets、mypy、TypeScript 与 Vite build 全部通过。

## 6. 当前任务：P0-A7 新手与设置渐进披露

### 已确认问题

1. 新会话恢复卡当前同时展示快速问答、系统学习、联网研究、项目推进和上传资料五个等权入口；
2. 输入框本身已能承接快速问答，额外模式选择增加首次回答前的认知负担；
3. 普通设置当前暴露角色、强制角色、本会话提示词、完整角色提示词、模型档位、上下文深度和检索算法；
4. 普通用户需要的是学习方式、资料使用、外部数据/隐私和互动氛围，而不是内部运行参数。

### 本切片范围

#### 首次打开

- 输入框保持视觉和交互主入口，用户直接输入即可获得回答；
- 恢复卡不再展示“快速问答”按钮；
- 默认只保留两个轻量快捷入口：**系统学习**、**上传资料**；
- 联网研究和项目推进继续由 TaskContract 根据输入自动识别；
- 为需要显式控制的用户，在次级“更多开始方式”中保留联网研究和项目推进；
- 不增加新的模式栏、顶级页面或首次配置向导。

#### 普通设置

默认只展示：

1. 学习方式；
2. 回答时是否使用我的资料；
3. 外部数据与隐私策略；
4. 互动氛围；
5. 保存为后续新会话默认值。

进入“高级设置”后才展示：

- 角色选择与强制保持角色；
- 本会话微调提示；
- 角色说明和完整提示词；
- 模型档位；
- 上下文深度；
- 检索方式、候选数、回答引用数和最低相关度。

### 边界

- 不改 TaskContract 分类、ChatService 路由或运行设置 API；
- 不删除任何高级能力，只调整默认可见层级；
- 已保存设置和恢复语义保持兼容；
- 不在本切片修改 SlideOver focus trap、复制失败反馈、上传校验或软键盘行为，这些属于 P0-A8。

### 门禁

- Vitest 验证新用户默认层只有系统学习和上传资料，直接输入无需模式决策；
- Vitest 验证联网研究/项目推进只在次级展开层；
- Vitest 验证普通设置不含角色、提示词、模型、上下文和检索参数，高级设置展开后全部可达；
- Playwright desktop / 390px 验证首次回答 0 配置决策、快捷入口、设置展开和无横向溢出；
- 原有 closure、session、evidence、lazy-load 和 Golden Journey 浏览器用例继续通过；
- pytest、RAG K1、Ruff、package、detect-secrets、mypy、Vitest、TypeScript 和 Vite 全绿。

## 7. 后续顺序

1. P0-A8 `a11y/focus-feedback-responsive`：焦点、复制、上传、触控、软键盘和溢出；
2. 审计完成后根据真实结果重新排序冻结任务，不自动沿用旧计划。

## 8. 审计完成标准

- 学习真值门禁成立；核心旅程在 desktop 和 390px 全部通过；
- first answer 无强制配置；学习恢复、资料学习、联网研究不超过两层 surface；
- 刷新、网络失败和 stream interruption 有明确恢复路径；
- 首屏不依赖隐藏实验模块；普通证据层只显示 adopted evidence；
- 默认结束流程不要求理解 Memory 文件；桌面/移动使用同一会话 owner；
- 普通首次入口和设置不要求理解内部模式、Provider 或检索参数；
- 键盘、焦点、复制、上传和窄屏问题有自动回归；全量 CI 通过。

## 9. 审计期间冻结

真实 Provider claim replay、生产 claim producer、claim UI、Streamlit 清理、RAG-K1f、RAG-K2、自适应 LearningPlan、G10-D 可执行代理继续冻结。

## 10. 当前执行状态

- 当前分支：`ux/onboarding-settings-progressive-disclosure`；
- 基线：PR #72 merge SHA `3796bfe3bbc7c83feac9eeb9f195803a5ed57228`；
- 当前阶段：P0-A7 范围已锁定，准备修改 RestoreCard 与 SettingsPanel；
- 下一动作：实现组件分层、组件测试和 desktop/390px 浏览器门禁，建立 Draft PR；
- 合并策略：独立小分支 -> Draft PR -> 完整门禁 -> 全绿合并。

## 11. 文档规则

- 当前状态只更新本文件；status-only 更新留在 active branch；
- `ARCHITECTURE_STATUS.md` 只维护稳定 owner/边界；`STATE_MODEL.md` 只维护稳定数据模型；
- 不新增并列长期状态文档；代码、CI、分支和 PR 变化必须同步本文件。

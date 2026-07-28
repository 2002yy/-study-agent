# Study Agent 当前状态

> **唯一进度入口**  
> 更新：2026-07-28  
> 产品定义：**Study Agent 是长期保持“正在学什么、已经确认什么、还不会什么、下一步是什么”的个人学习工作台。**  
> 当前主线：**P0-A1–P0-A7 已进入 `main`；P0-A8 已完成实现与实现-head 全量门禁，正在通过 PR #74 做最终状态同步与合并收口。**  
> 当前代码切片：`a11y/focus-feedback-responsive`；Draft PR #74。

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
- desktop / mobile SessionNavigator 单一交互 owner；
- 新手入口与设置渐进披露；
- SlideOver 键盘焦点闭环、复制结果反馈、上传前置合同和窄屏/软键盘体验门禁。

已进入 `main`：

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
- PR #72 `3796bfe3bbc7c83feac9eeb9f195803a5ed57228`，最终 CI #1496；
- PR #73 `676fe23a0f26d500712b71c6e175d99d953f1e80`，最终 CI #1520。

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
- 58 files / 205 Vitest、全部 desktop/390px Playwright journeys、pytest、RAG K1、Ruff、package、secrets、mypy、TypeScript 与 Vite build 全部通过。

## 6. P0-A7 已完成：新手与设置渐进披露

- 输入框继续承担默认直接问答，首次回答不要求先选模式；
- 新会话默认只显示“系统学习 / 上传资料”，联网研究和项目推进进入次级展开；
- 普通设置只显示学习方式、互动氛围、资料使用、联网/上下文隐私和默认值保存；
- 角色、强制角色、本会话微调、完整提示词、模型档位、上下文深度和检索参数进入高级设置；
- 未修改 TaskContract、ChatService 路由、设置 API 或恢复语义；
- CI #1512 只暴露测试适配问题；修复 cleanup、隐藏/可见断言和旧文案后，CI #1518 与最终 CI #1520 全绿；
- 59 files / 208 Vitest、TypeScript、Vite build 和 26 个 Playwright 用例全部通过；
- `progressive_onboarding` 在 desktop / 390px 均为 0 必需点击、0 配置决策、1 个 product surface、无横向溢出；
- `progressive_settings` 在 desktop / 390px 均为 3 次点击、0 配置决策、2 个 product surface、无横向溢出。

## 7. P0-A8 已完成实现：焦点、反馈与窄屏体验

PR #74 在分支 `a11y/focus-feedback-responsive` 完成 P0-A8。实现 head `e3eb406c2e1c65da244dc797c212171a34fcb7fc` 的 CI #1544 已完整全绿。

### P0-A8.1 焦点与键盘

- `SlideOver` 打开后聚焦唯一关闭按钮；遮罩与关闭按钮使用不同可访问名称；
- Tab 从最后一个可交互元素回到第一个，Shift+Tab 反向循环，焦点不会逃出 dialog；
- 保留 Escape 关闭、背景滚动锁定和关闭后焦点返回原触发控件；
- Vitest 与 desktop / 390px Playwright 均覆盖 keyboard-only 路径。

### P0-A8.2 复制反馈

- 回答正文、中断回答、已采用证据和证据诊断四类复制入口均显示 success / failure 状态；
- Clipboard API 不可用或拒绝时，不再静默吞错；
- 可见按钮文案与 `aria-live` 状态同时反馈，且不暴露浏览器内部异常文本。

### P0-A8.3 上传约束与提示

- 前端单一合同与服务端当前约束一致：`.md`、`.markdown`、`.txt`、`.pdf`、`.docx`；
- 单文件上限 10 MiB，单批次上限 25 MiB；空文件、不支持类型、超限和混合无效批次在网络请求前整体拒绝；
- 文件选择器 `accept`、入口说明、前置校验和错误文案共用同一合同；
- 服务端继续负责 MIME、文件签名、UTF-8 和 DOCX 结构等权威校验，前端不伪装后端成功。

### P0-A8.4 触控、软键盘与窄屏

- 关键移动端交互目标达到至少 44px；
- 学习缺口、下一步、错误、会话、来源和上传说明允许换行，不再以单行 ellipsis 丢失关键内容；
- 动态 viewport、安全区、抽屉和 composer 布局加固；
- 390×520 模拟输入聚焦/软键盘收缩后，输入框与发送按钮仍在 viewport 内且可操作；
- desktop / 390px 所有新增与既有旅程均通过横向溢出检查。

### P0-A8 门禁结果

- CI #1538 暴露 SlideOver 两个关闭入口同名的真实可访问性歧义，产品代码修正为唯一关闭控件名称；
- CI #1542 已通过后端和 62 files / 217 Vitest、TypeScript、Vite build，并通过 32/34 浏览器用例；剩余 2 项仅为 Playwright 模糊定位同时命中背景按钮；
- CI #1544 在精确定位修正后完整全绿；
- pytest、RAG K1、Ruff、package、detect-secrets、expanded mypy、62 files / 217 Vitest、TypeScript、Vite build 和 34/34 desktop / 390px Playwright 全部通过；
- 新增浏览器门禁覆盖 SlideOver 焦点循环、无效上传不发请求、Clipboard 拒绝反馈、390×520 composer 可达、44px 触控目标和无横向溢出；
- 未修改学习真值、TaskContract、RAG 排序、Provider 行为、服务端上传策略或顶级产品表面。

## 8. P0-A8 完成后的独立评估

P0-A8 全绿并合并后，**先暂停新增功能**，立即进行一次独立的功能评估与使用体验评估。不得直接恢复全部旧计划，也不得边评估边扩展功能。

### 功能评估

1. 按核心学习闭环逐项核验：开始任务、持续学习、资料学习、联网研究、源码学习、理解验证、学习结束、刷新恢复、失败恢复；
2. 核对每项能力的生产 owner、持久化真值、失败边界与自动测试覆盖；
3. 区分“存在”“可用”“稳定”“达到产品目标”，不能只以接口或按钮存在判定完成；
4. 输出 P0 / P1 / P2 功能缺口、重复能力、无 owner 能力和应继续冻结的能力。

### 使用体验评估

1. 复测 desktop 与 390px 核心 Golden Journeys；
2. 记录必需点击、必需决策、产品 surface、恢复点击、键盘可达性、横向溢出和关键文本完整性；
3. 检查首次进入、返回学习、资料与证据、结束学习、会话导航、设置和错误恢复的认知负担；
4. 结合浏览器 trace、截图、视频和人工试玩，识别“功能正确但难以理解或难以推进”的问题。

### 评估后的决策

评估完成并写回本文件后，才决定下一批功能。首轮候选仅包括：

1. 是否仍存在阻断普通学习闭环的 P0 缺口；
2. 是否开始真实 Provider AnswerClaim replay；
3. 是否推进生产 claim producer，或先做 RAG-K1f / K2；
4. 是否继续保持自适应 LearningPlan 与可执行代理冻结。

## 9. 审计完成标准

- 学习真值门禁成立；核心旅程在 desktop 和 390px 全部通过；
- first answer 无强制配置；学习恢复、资料学习、联网研究不超过两层 surface；
- 刷新、网络失败和 stream interruption 有明确恢复路径；
- 首屏不依赖隐藏实验模块；普通证据层只显示 adopted evidence；
- 默认结束流程不要求理解 Memory 文件；桌面/移动使用同一会话 owner；
- 普通首次入口和设置不要求理解内部模式、Provider 或检索参数；
- 键盘、焦点、复制、上传和窄屏问题有自动回归；全量 CI 通过。

## 10. 审计期间冻结

真实 Provider claim replay、生产 claim producer、claim UI、Streamlit 清理、RAG-K1f、RAG-K2、自适应 LearningPlan、G10-D 可执行代理继续冻结。

## 11. 当前执行状态

- 当前分支：`a11y/focus-feedback-responsive`；Draft PR #74；
- 基线：PR #73 merge SHA `676fe23a0f26d500712b71c6e175d99d953f1e80`；
- P0-A8 实现 head：`e3eb406c2e1c65da244dc797c212171a34fcb7fc`；实现 CI #1544 完整全绿；
- 当前阶段：状态文档已同步 P0-A8 实现事实，等待本次 status-sync commit 的最终 head 完整 CI；
- 收口动作：最终 head CI 全绿 -> PR #74 转 Ready -> 按最新 head squash merge；
- PR #74 合并后：先做独立功能评估与使用体验评估，再决定下一批功能；
- 合并策略：独立小分支 -> Draft PR -> 完整门禁 -> 全绿合并。

## 12. 文档规则

- 当前状态只更新本文件；status-only 更新留在 active branch；
- `ARCHITECTURE_STATUS.md` 只维护稳定 owner/边界；`STATE_MODEL.md` 只维护稳定数据模型；
- 不新增并列长期状态文档；代码、CI、分支和 PR 变化必须同步本文件。

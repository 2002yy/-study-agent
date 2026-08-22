# G12 人工与时序门验收证据

> 执行日期：2026-08-22
> 执行方式：Playwright 驱动真实 Chrome（`playwright.g12-acceptance.config.ts`）对本地真实栈——真实 FastAPI + 真实 SQLite（专用测试 server `tools/real_stack_research_test_server.py`）。全程读取服务端 durable 终态（`/__e2e__/state/{id}` 与 `GET /chat/turns/{id}/status`），无 mock sleep 假断言，无以浏览器 abort 冒充服务端终态。
> 复现命令：`cd frontend && npm run test:e2e:g12`（需 `G12_PYTHON` 指向带 uvicorn 的解释器；端口 5175/8000）。

## 一、实测数据汇总（最终轮，18/18 通过）

### 门 1 — 点击后 200ms UI 确认（决策 4）

| viewport | 实测 ACK | 阈值 | 结果 |
|----------|---------|------|------|
| desktop (1440×900) | **113ms** | <200ms | PASS |
| narrow landscape (768×430) | **127ms** | <200ms | PASS |
| mobile (390×844) | **130ms** | <200ms | PASS |

测量方法：`performance.now()` 差值（点击停止按钮 → `.turn-status-line` 可见）。多轮历史：{52,118,129} / {111,67} / {101,102,69} / {113,127,130}——稳态下始终远低于阈值。首测曾出现 287/727ms 的离群值，定位为 vite dev 冷启动按需编译 + React hydration 抖动，已通过 beforeAll 预热旅程（完整问答一轮触发全部懒 chunk）排除。

### 门 2 — 慢检索登记 → durable 终态实测上限（决策 4/9）

注入方式：测试 server `POST /__e2e__/retrieval-delay {seconds:3}`（检索入口 sleep，决策 4 明确允许注入慢检索）。

| viewport | 注入延迟 | 登记→终态实测 | 命中 checkpoint | 终态 |
|----------|---------|--------------|----------------|------|
| desktop | 3000ms | **2980ms** | web_tools | cancelled |
| narrow landscape | 3000ms | **2978ms** | web_tools | cancelled |
| mobile | 3000ms | **2963ms** | web_tools | cancelled |

结论：协作式取消开销 ≈ **0ms**（settle 时间 ≈ 注入的阻塞时长，sleep 结束后下一个 checkpoint 立即命中）。终态均为 `cancelled`（无可见输出）、`assistant_message` 为空、thread operation 锁同事务释放。

多轮数据：2963–2994ms（4 轮），波动 ±31ms，无劣化趋势。

### 门 3 — 三 viewport 状态文案与 aria live semantics（决策 12）

每个 viewport 验证：

- `.turn-status-line` 在 bubble 内渲染（非仅 toast）
- `role="status"` ✓、`aria-live="polite"` ✓
- 文案命中固定文案集（正在提交停止请求… / 已登记 / 服务端仍在收尾… / 已停止：本轮未产生可见输出。/ 已停止生成，已有内容已保留。/ 本轮已在停止前正常完成。）
- 无颜色依赖（文本承载语义 + 边框描边），窄屏样式降级可读

截图与视频证据：`frontend/test-results/g12-artifacts/`（每 viewport × 每 journey）。

### 门 4 — 取消 pending 时离开会话（决策 10）

Journey D：取消登记后 composer 立即可用（toBeEnabled ≤5s）、新会话可创建（POST /sessions/new 成功）；旧 turn 最终 settle 为 `cancelled`，不阻塞新会话任何操作。

### 门 5 — 等待归档 / 归档队列持久化（决策 15）

Journey E：

1. 取消 pending 时 POST `/sessions/{id}/archive` → `{queued: true}`
2. durable marker 落库：`thread.archive_after_cancel_operation_id == op_id` 且 thread 保持 active
3. settle 后 drain 自动执行（stream finally / status 轮询 / 启动扫描三触发点）→ thread 变 `archived`、marker 清空
4. 三 viewport 全过；日志 `G12-QUEUE[..] archived after settle`

重启持久化另由单测覆盖：`test_queue_survives_restart_and_drains`（全新 SessionService 实例 process_pending_archives 消费遗留 marker）。

### 门 6 — 取消待归档（决策 15）

Journey F：排队后 `DELETE /sessions/{id}/archive-queue` → `{cancelled: true}`、marker 清空；settle 后 thread 保持 active 未被归档。

**归档失败保留会话**由单测覆盖：`execute_queued_archive_if_due` 异常路径（process_pending_archives 捕获并保留会话）+ 前端 catch 分支独立错误文案「会话归档失败：…」。

## 二、方法学边界

- 本验收为**浏览器自动化真实栈**证据，覆盖合同 10.6 人工与时序门的全部可自动化项。
- 不在本文件范围（沿用既有展示边界）：真实屏幕阅读器体验、实体手机、视觉对比度人工评审——归 G17 人工验收批次。
- 慢检索为受控注入（3s），非生产负载推算；checkpoint 开销已证明 ≈0，生产慢检索的上限即检索本身耗时。

## 三、资产

| 文件 | 用途 |
|------|------|
| `frontend/playwright.g12-acceptance.config.ts` | 三 viewport 真实栈配置（独立 webServer，端口 8000/5175） |
| `frontend/e2e/g12-acceptance.spec.ts` | 六旅程 A–F |
| `tools/real_stack_test_server.py` | 新增 `POST /__e2e__/retrieval-delay`、`GET /__e2e__/latest-thread` |
| `npm run test:e2e:g12` | 复现入口 |

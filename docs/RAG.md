# RAG / User Material Evidence

> RAG 服务于**用户自己的资料与项目材料**。它是 Evidence Provider，不是全局 truth owner。当前进度看 [`PROJECT_STATUS.md`](PROJECT_STATUS.md)。

## 1. 适用范围

RAG 适合：

- 用户上传的教材、笔记、项目文档；
- 从用户资料中定位定义、约束、历史决定；
- 给 LearningClaim 提供 project-decision / user-material evidence；
- 帮助恢复学习 context。

RAG 不应被当成“外部世界最新事实”的默认来源；外部规范/最新事实使用权威 Web research。

## 2. Provider ≠ truth domain

```text
Provider: GitHub | RAG | Web
Truth domain: implementation | project_decision | external_fact
```

RAG 可以承载 project decision，也可能承载旧实现说明。系统必须先判断资料的时间和语义范围，再决定能否支撑当前 Claim。

## 3. 引用原则

Committed evidence 需要可定位 provenance。检索 query、embedding score、rank、chunk score 是 retrieval metadata，不自动成为 durable SourceEvidence identity。

## 4. 冲突处理

- RAG 正式设计文档 vs 当前源码：不是简单“谁更可信”，而是 design vs implementation；应显示 divergence；
- 两份同一时期正式项目文档冲突：进入 EvidenceConflict；
- 旧文档 vs 新文档：保留时间语义；不得静默用 latest-write-wins 改历史 Claim；
- provider unavailable：只代表当前无法验证，不代表结论为假。

## 5. 与 LearningClaim

RAG 结果先是 Evidence Candidate；只有经过收敛、且真正支撑 Claim 时才进入 committed EvidenceSet。没有可靠 Primary Evidence 时只能形成 Hypothesis。

## 6. Context 预算

避免把整份资料或大量近似 chunks 塞给模型。优先直接相关、可定位、互补的 evidence；重复候选应在收敛阶段删除。

## 7. 与 Memory

RAG source 与 memory summary 分离：资料 evidence 可以支撑 Claim；conversation/memory summary 只提供背景，不能自行证明 Claim 或用户 mastery。

## 8. ChatTurn-owned cooperative cancellation

Chat pre-answer 的只读检索由当前 `turn_id + operation_id` 拥有。它不新增 LocalRagRun；取消真值写入 ChatTurn。

每个可能耗时或产生副作用的边界都必须检查同一 cooperative cancellation check：

1. query plan 后、读取索引前；
2. 每个 base/facet/adaptive search 前后；
3. lexical/vector/backend-vector 与 rerank 阶段之间；
4. 候选合并/过滤后、构造 Evidence units 前；
5. 发送任何模型/provider 调用前；
6. 写 ChatTurn、引用、LearningTruth 或 completed 前。

取消异常必须穿透 retrieval 的 broad exception boundary；不得被降级成普通“检索失败”后继续生成。已找到但未采用的 chunks 只保留 stage、query-plan 摘要、计时和数量，不保留正文，不进入模型、引用、LearningTruth 或自动 retry reuse。

interrupted continuation 只复用同 Turn 已持久化且已采用的 RAG snapshot；cancelled 重发、retry 和 regenerate 都重新检索。cooperative cancellation 不承诺强杀同步 provider，但 operation fence 必须保证其自然返回后结果被丢弃且没有后续副作用。

## 9. Embedding 与外发边界

- `private_query` 可以组合当前问题、学习目标和缺口，只允许本地 retrieval 使用；
- `question_only` / `recent_chat` 下，即使未来明确允许外部 query embedding，也最多发送当前原始问题；
- 未建立文档级云处理授权前，用户文档 chunks 不得进入任何可能离机的 embedding provider；`allow_local_evidence` 不构成全量文档授权；
- 被 policy 阻止时，本地解析、lexical index 和本地 vector 阶段可继续，remote embedding stage 记录 `blocked_by_policy`；UI 不得静默 fallback 后仍称“增强语义”；
- query embedding 的实际调用归 ChatTurn `external_calls`；document embedding 归现有 RagWriteRun stage，不新增审计 run；
- audit 只记录 purpose/provider/data categories/count/result，不记录 query 或文档正文。

当前窄止血实现尚无文档级云处理授权入口，因此 external embedding 没有生产 bypass：Chroma 配置到非本地 provider 时，query/document embedding 都在 client/provider 调用前 `blocked_by_policy`。document write 仍提交本地 index，并由现有 RagWriteRun vector stage 记录 provider、documents/chunks 和结果；未来授权入口必须另行 Grill，不能复用环境变量。

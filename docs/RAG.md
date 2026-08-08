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

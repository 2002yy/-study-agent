# 项目上下文

## 项目结构

```
study-agent/                  # 仓库根
├── src/                      # Python backend
│   ├── api/                  # REST routes（learning_closure / learning-resume / revalidate …）
│   ├── application/          # services（freshness / resume / closure / revalidation …）
│   ├── domain/               # durable truth models（claim / revision / evidence / goal …）
│   ├── web/                  # tree-sitter backends / structure quality / gateways
│   └── tests/                # pytest（159 文件）
├── frontend/                 # React 19（vite + vitest + playwright e2e）
│   ├── src/                  # components / features（learning / evidence / learning-memory …）
│   └── e2e/                  # golden-journeys / complex-content（5 项目 51 测试）
├── docs/                     # PROJECT_STATUS.md（唯一进度 owner）/ TESTING / ARCHITECTURE / TECH_STACK …
└── memory/                   # 运行时记忆文件（本目录 6 个同步清单）
```

## 关键原则

- `docs/PROJECT_STATUS.md` 是唯一进度/执行顺序 owner，不得新增并列 ROADMAP 文档；
- P2-D 迁移禁令仍有效：AnswerClaimV1 不是 LearningClaim、legacy confirmed_points 不升级、retrieval score 不入 SourceEvidence 等；
- 合同冻结 ≠ 功能已上线：执行顺序必须按 PROJECT_STATUS 推进。

## 当前架构要点

- durable learning truth：Goal / ClaimRevision / SourceEvidence / UnderstandingEvidence / Hypothesis / NextStep（schema v18）；
- freshness 为 on-demand derived 状态（不新增表）；revalidation 走同 lineage 新 Revision；
- 前端 LearningPanel/Strip/EvidenceTrail 呈现 resume 上下文；Playwright 5 项目（desktop/mobile/narrow chromium + firefox + webkit）。

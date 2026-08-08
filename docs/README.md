# Study Agent 文档索引与治理

> 更新：2026-08-08
>
> **唯一进度入口：[`PROJECT_STATUS.md`](PROJECT_STATUS.md)。** 本目录不再允许第二份长期 STATUS / ROADMAP / NEXT_PHASE / AUDIT 与其并列。

## 1. 文档所有权

| 文档 | 唯一职责 | 是否可声明“当前阶段” |
|---|---|---|
| `PROJECT_STATUS.md` | 当前事实、可复核证据、缺口、执行顺序 | **是，唯一** |
| `ARCHITECTURE.md` | 当前 runtime、owner、数据/工具边界 | 否 |
| `../domain_models.md` | 稳定领域对象、关系、生命周期 | 否 |
| `../state_invariants.md` | 必须永远成立的硬约束 | 否 |
| `STATE_MODEL.md` | durable / ephemeral / derived state 所有权 | 否 |
| 专项文档 | 对应子系统合同与实现说明 | 否 |
| `archive/` | 历史方案、旧 roadmap、旧架构快照 | **禁止** |

## 2. 当前核心文档

- [`PROJECT_STATUS.md`](PROJECT_STATUS.md)：当前 P2-D 进度。
- [`ARCHITECTURE.md`](ARCHITECTURE.md)：React + FastAPI + SQLite 当前架构。
- [`../domain_models.md`](../domain_models.md)：LearningTopic / Goal / Claim / Revision / Evidence / Hypothesis / NextStep 等稳定语义。
- [`../state_invariants.md`](../state_invariants.md)：学习真值、证据、Persona、多 provider、恢复等不变量。
- [`STATE_MODEL.md`](STATE_MODEL.md)：状态所有权与持久化边界。

## 3. 专项文档

| 文档 | 范围 |
|---|---|
| `RAG.md` | 用户资料检索、RAG evidence provider、引用与冲突边界 |
| `MEMORY_SYSTEM.md` | 长期记忆与 committed learning truth 的边界 |
| `CONTEXT_TIERS.md` | prompt/context 分层与预算优先级 |
| `MODEL_ROUTING.md` | provider/model 路由，不拥有学习真值 |
| `PERFORMANCE.md` | cache、延迟、预算、P2-D source/CI 缓存合同 |
| `TESTING.md` | runtime + learning truth 的验收策略 |
| `SECURITY.md` | 安全边界 |
| `TECH_STACK.md` | 技术栈参考 |
| `WEB_SEARCH_SETUP.md` | Web Search 配置 |
| `WEB_SEARCH_IMPLEMENTATION_NOTES.md` | Web Search 实现备注 |
| `NEWS_PIPELINE.md` | durable News workflow 专项参考；**不是独立产品面声明** |
| `ANSWER_CLAIM_PROVIDER_REPLAY.md` | Provider replay 专项实验参考；当前处于冻结边界 |
| `INTERVIEW_NOTES.md` | 面试/项目表达材料，不是架构 owner |

## 4. 历史入口

以下旧文件保留原路径作为兼容指针，完整历史正文移入 [`archive/`](archive/)：

- `AGENT_LONG_TERM_ROADMAP.md`
- `ARCHITECTURE_STATUS.md`
- `NEXT_PHASE_PLAN.md`
- `STUDY_AGENT_OPTIMIZATION_ROADMAP.md`
- `WEB_AGENT_REDIRECT_PLAN.md`
- `API_FRONTEND_MIGRATION.md`

仓库根目录的旧 `ARCHITECTURE_V2.md`、`PROJECT_PLAN.md`、`FUTURE.md`、`migration_plan.md`、旧 README/PRD 等也只保留兼容指针，历史正文位于 `docs/archive/root/`。

## 5. 阅读顺序

### 想知道项目现在怎样

```text
README.md
→ docs/PROJECT_STATUS.md
→ docs/ARCHITECTURE.md
```

### 想继续 P2-D 源码学习设计/实现

```text
domain_models.md
→ state_invariants.md
→ docs/STATE_MODEL.md
→ docs/ARCHITECTURE.md
→ docs/TESTING.md
```

### 想查历史为什么这么设计

```text
docs/archive/
→ git history / PR / CI evidence
```

## 6. 永久治理规则

- 进度事实只写 `PROJECT_STATUS.md`。
- 设计决策固定后，写入稳定 semantic docs，不复制到多个 roadmap。
- 专项文档如需提当前状态，只链接 `PROJECT_STATUS.md`，不维护自己的“当前下一步”。
- 历史方案必须保留时间语义；不得把旧 planned 文本重新包装成 current truth。
- 文档与代码冲突时，先区分：implementation truth、project decision、external fact；不得简单按“哪个文件更新”投票。

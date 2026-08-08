# Performance & Cache Contracts

> 性能优化不能改变 truth semantics。

## 1. P2-D Source cache

```text
repository + exact commit
→ SourceSnapshot
→ RepositoryStructureIndex
→ deterministic symbol mapping
```

同一 exact commit 的 snapshot / structure index 应强缓存并复用；普通 query 不重复重建同一源码事实。

## 2. CI Observation cache

CI 是时间变化的 ValidationObservation：

- 与 SourceSnapshot cache 分离；
- 使用短 TTL（第一版可采用约 10 分钟级默认值，具体值属于配置而非领域真值）；
- 支持显式 refresh/retry；
- 普通源码搜索不应因 CI refresh 阻塞；
- CI provider failure 返回 unavailable，不使 SourceEvidence 失败；
- 当前 P2-D-1 不持久化完整 CI history。

## 3. Request context budget

优先保留：Current Goal → committed truth → prerequisite evidence → directly relevant evidence。先裁弱候选、重复 chunks、旧对话、Persona 装饰。

## 4. Evidence bound

每个 Claim 1 Primary + 0–4 Supporting 本身也是性能边界；如果一个 Claim 需要十几份证据，优先拆 Claim 而不是扩大 context。

## 5. UI 性能

Evidence 三级渐进披露，普通学习界面不预渲染全部 SHA/CI/revision details。移动端优先保持输入、滚动、drawer、恢复路径稳定。

## 6. Measurement

性能优化必须同时观察：首 token/首结果延迟、provider 调用数、cache hit、上下文体积、失败降级，以及是否破坏 exact-source / owner / recovery invariant。

# Model Routing

> 模型路由只决定“由哪个 provider/model 执行什么任务”，不拥有学习真值。

## 1. 路由职责

允许路由影响：

- 成本/延迟；
- 上下文容量；
- 是否支持 vision/tool/schema；
- 教学表达质量；
- 某类任务的执行模型。

禁止路由影响：

- Claim 是否为真；
- Evidence 是否有效；
- 用户是否 confirmed；
- source freshness；
- durable Goal / NextStep history。

## 2. Truth boundary

```text
Model/Provider
   ↓ proposes / explains / extracts
Application truth owner
   ↓ validates / commits
Learning domain state
```

更换模型不得导致“同一已提交 Claim 因 Persona/模型不同而变成另一套真值”。

## 3. 多角色

Persona 可以选择不同模型或教学策略，但所有角色读取同一 LearningClaim / Evidence / Understanding state。Persona 不能自行放宽 pass 标准。

## 4. Provider failure

模型/provider 失败只说明本次执行失败或 unavailable，不得自动使已有 SourceEvidence/Claim invalid。Retry/fallback 产生的结果仍需经过同一领域提交规则。

## 5. External evidence provider

GitHub / RAG / Web 与 LLM provider 是不同概念：前者提供 evidence，后者负责生成/分析。任何 LLM 都不能凭自己的 confidence 替代 evidence provenance。

## 6. 配置治理

模型/provider 配置必须由单一配置 owner 解析和验证；UI、脚本与 runtime 不维护互相漂移的第二套默认规则。

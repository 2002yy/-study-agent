# AnswerClaim real-provider replay contract

> **文档类别：稳定技术合同，不是当前进度入口。**  
> 当前是否已经执行真实 replay、采用哪个模型、得到什么指标，统一查看 [`PROJECT_STATUS.md`](PROJECT_STATUS.md)。

## 1. Purpose

确定性 gold producer 只能证明 AnswerClaim evaluator 会正确评分，不能代表真实模型能够稳定输出完整、可引用的结构化主张。

本合同把已有 K1e real-provider replay 分成两个明确阶段：

```text
fixed K1 answer cases + production local retrieval
-> one real Provider call per case
-> Provider-authored answer / assertions / cited_sources
-> immutable raw replay report
-> offline AnswerClaim adapter
-> strict AnswerClaimSnapshotV1 validation
-> record-only quality report
```

第二阶段不会再次调用模型，也不会从自然语言回答推断主张。

## 2. Input contract

离线评测只接受同时满足以下条件的 K1e 报告：

- `replay_kind == real_provider`；
- `status == completed`；
- 完整 10 条固定 gold case，而不是挑选后的子集；
- `completed_cases == cases`，且 `failed_cases` 为空；
- 包含 corpus、prompt-template、Provider profile、model name 和 endpoint fingerprint；
- 每个 case 都包含 Provider 原生返回并由 K1e parser 记录的：
  - `answer`；
  - `refused`；
  - `assertions[].text`；
  - `assertions[].cited_sources`。

原始 API key 和 raw endpoint 不进入任何报告。

## 3. Adapter boundary

`RecordedProviderAnswerClaimProducer` 只做结构适配：

- 每条 Provider assertion 变成一个 `factual / asserted / provider_structured` claim；
- claim ID 由最终回答 hash 与 claim text 确定生成；
- `cited_sources` 变成 `direct_support` claim-evidence links；
- 引用只能指向该固定 case 已知的 evidence IDs；
- Provider 最终回答保留原始换行，用于稳定 `answer_hash`。

以下行为明确禁止：

- 从完整自然语言答案重新抽取或补写 claims；
- 根据 gold expected claims 修正 Provider 输出；
- 为缺失引用猜测 evidence；
- 让第二个模型充当 judge 或 claim extractor；
- 把 replay 结果写入 ChatTurn、SQLite 或 committed learning truth。

未知 evidence、重复 claim、空最终答案或其他 schema 错误会使该 case 无质量分；不得伪造补齐。

## 4. Metrics

离线报告复用 `src/rag/answer_claim_eval.py`，记录：

- schema parse rate；
- answerability accuracy；
- claim precision / recall / F1；
- claim kind accuracy；
- claim coverage；
- unsupported claim rate；
- claim-evidence link precision / recall / F1；
- refusal leakage；
- forbidden-claim leakage。

同时保留原 K1e answer-quality、latency、token usage 和 Provider identity，便于同一次 run 内联合分析。

费用只接受操作者显式提供的人民币金额，不从 token 数量猜测：

```text
cost.currency = CNY
cost.amount = operator supplied value or null
```

## 5. Local offline evaluation

已有完整 K1e 报告时运行：

```bash
python tools/run_answer_claim_provider_replay.py \
  --provider-report output/rag-provider-replay.json \
  --output output/answer-claim-provider-replay.json \
  --run-label stability-run-1
```

记录已确认账单金额时可追加：

```bash
--cost-cny 1.25
```

该命令不需要 Provider key，也不发起网络请求。

## 6. Manual real-provider workflow

`.github/workflows/rag-provider-replay.yml` 仍是唯一手动真实运行入口。操作者需要明确选择：

- Provider profile；
- model profile；
- exact model name；
- 可选 base URL override；
- 可选、已核实的 CNY cost。

workflow 依次：

1. 运行 K1e real-provider replay；
2. 运行离线 AnswerClaim replay；
3. 校验 real-provider provenance 与 record-only 边界；
4. 上传两个 JSON artifact；
5. 任一阶段失败则整次 workflow 失败。

普通 PR CI 不使用 Provider secret，只运行 synthetic in-memory contract tests。

## 7. Decision gate

一次真实 run 只能说明该 Provider/model/语料/prompt fingerprint 下的观察结果。至少要比较：

- claim coverage 与 unsupported-claim rate；
- citation/link alignment；
- unanswerable refusal leakage；
- 多次运行稳定性；
- latency、usage 与已核实成本。

在真实 artifact 被审查并回写 `PROJECT_STATUS.md` 前：

- 不解冻生产 claim producer；
- 不新增 claim UI；
- 不把 AnswerClaim 接入生产 ChatTurn；
- 不修改 committed learning truth；
- 不因为 deterministic self-test 为 1.0 就宣称真实模型质量达标。

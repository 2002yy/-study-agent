from pathlib import Path

path = Path("docs/PROJECT_STATUS.md")
lines = path.read_text(encoding="utf-8").splitlines()

replacements = {
    "- **Remote CI / current branch gate：**": "- **Remote CI / current branch gate：**PR #143 final head `ab4924b1a66e15ad3a9bcdefd47af227e15f3bda` 已合并为 `main@f3f17824c132e2a88caf4dac4a9d6eae78e35910`，exact-main CI [#33947613290](https://github.com/2002yy/study-agent/actions/runs/33947613290) `push / completed / success`。Draft PR #142 当前 safe-classification clean code commit 为 `3d04bfd4909d2c5a2c2a35f04e082794b9d50326`；为绕过 GitHub Actions bot-push 递归抑制，使用一次 create/delete trigger 得到 exact evidence head `7582824558bdddae4e4498b647876299de42a793`，`3d04bfd… -> 758282…` 为 2 个 trigger commits 且 **0 changed files**。该 exact head 的 push CI [#34127107622](https://github.com/2002yy/study-agent/actions/runs/34127107622) 与 PR CI [#34127112379](https://github.com/2002yy/study-agent/actions/runs/34127112379) 均 `completed / success`；full pytest **1715/1715**，RAG K1、Ruff、package helper、detect-secrets、expanded mypy baseline、frontend tests/build、browser Golden Journeys 与 real-stack browser gates 全绿；safe-classification 聚焦集 **26/26**。",
    "- **Runtime status：**": "- **Runtime status：**首次真实 live 12（head `cd32c209…`，run [#33979582319](https://github.com/2002yy/study-agent/actions/runs/33979582319)）结果为 **0 reviewable answers / 0 completed runs / 10 failed / 2 partial / protocol probes 6/6**。live13（head `a7ada7e…`，run [#34117726273](https://github.com/2002yy/study-agent/actions/runs/34117726273)）先确认 assessor 为 compact-code failure、reader 为 gateway negative result 而非 exception。随后 exact head `758282…` 的同两例 safe-classification diagnostic [#34127107728](https://github.com/2002yy/study-agent/actions/runs/34127107728) `completed / success`，业务结果仍为 **0/2 cases with successful reads**：`academic_primary` 两次 assessor failure 均为 `compact_code_duplicate` / `CompactAssessmentGainSignalDuplicateError`，另有一次既有 `APITimeoutError`，因此 **0 read attempts**；`unanswerable_unverifiable` 同样有两次 `compact_code_duplicate`，但一次 assessor 成功排出 2 个候选，随后 **2/2 reads = gateway_negative_result**，不是 exception 或 empty-content，且底层未提供可归一化的 canonical provider code，所以 `provider_code_counts` 为空。artifact 继续不保存 prompt、raw response、page body、query text、candidate identity 或 failure detail。",
    "- **GO / NO-GO：**": "- **GO / NO-GO：**RQCE-P0、P1-A0、A1–A4/B1–B5 + Hardening + P1-C 子批 1/2/3 + active steering + failure-state Batch A/B/C + PR #143 answer/claim binding = **REMOTE GO / DELIVERED**。PR #142 qualification infrastructure = **GO / CLOSED at `c3d3576c…`**；safe-classification code/diagnostic/CI = **REMOTE GATES GREEN at exact evidence head `758282…`**；pre-read 业务门仍为 **NOT GO / 0 OF 2 DIAGNOSTIC CASES SUCCESSFULLY READ / LIVE 12 FAILED**，default activation = **FROZEN**；RQCE-P2 = **NOT STARTED**。workflow success、分类成功与 read attempts 均不能替代成功读取门；formal live 12 在该 exact head 的 run [#34127107653](https://github.com/2002yy/study-agent/actions/runs/34127107653) 仍为 `skipped`。",
    "- **唯一下一步：**": "- **唯一下一步：**保持 `ca2`、模型、prompt、token/timeout、untouched manifest/rubric/Evidence Gate、预算、2-candidate window、候选/读取调度与 default activation 全部不变，只修已定位 owner。**Assessor owner：**稳定 expanded domain 的 `_enum_tuple()` 已对重复 gain signal 做 order-preserving dedupe，而 compact `_compact_codes()` 当前把同一语义重复视为 fatal；下一窄修复只对齐这两个 parser 的集合语义，重复合法 code 去重，未知/畸形 code、coverage/order/domain 继续 fail closed，且不处理本轮独立出现的 `APITimeoutError`。**Reader owner：**`GeneralWebGateway.read()` 当前把 `ArticleReadResult.reason` 仅放入 negative result 的 `error` 字段，没有 bounded `error_code`；下一窄修复只在该 gateway boundary 提供受限 canonical failure code（未知仍归 `other`，不保存 raw reason/detail），不得改变 reader backend、fallback、retry、timeout 或业务终态。完成聚焦门与 exact-head push/PR CI 后重跑同两例 diagnostic；只有两例均产生真实成功读取才允许 untouched live 12。",
}

seen = {prefix: 0 for prefix in replacements}
for index, line in enumerate(lines):
    for prefix, replacement in replacements.items():
        if line.startswith(prefix):
            seen[prefix] += 1
            lines[index] = replacement

bad = {prefix: count for prefix, count in seen.items() if count != 1}
if bad:
    raise SystemExit(f"status patch prefix count mismatch: {bad}")

path.write_text("\n".join(lines) + "\n", encoding="utf-8")

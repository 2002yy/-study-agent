from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs" / "PROJECT_STATUS.md"


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return source.replace(old, new, 1)


def main() -> None:
    source = PATH.read_text(encoding="utf-8")

    source = replace_once(
        source,
        "> 当前切片：**Draft PR #113 已退出 10 个无生产 owner 的旧 News 阶段 Pydantic 模型、两层兼容导出和无路由 owner 的 `news_result_payload`；最终代码 head `0d634dbcd0bd66bdab919efc9ba7cbbde69110cd`，CI run `31177047560` 完整通过。**  \n",
        "> 当前切片：**PR #113 已 squash 合并 `main`；最终 head `bc3c06f043eae5f195516741c88a45205e21864b` 的 CI run `31177513884` 完整通过，功能 merge SHA `39e5efe91a75099b6cf5646aa9060d2945b5604c`。**  \n",
        "header current slice",
    )

    source = replace_once(
        source,
        "- 最终代码 head `0d634dbcd0bd66bdab919efc9ba7cbbde69110cd`，CI run `31177047560` 完整通过；\n- `NewsRun* / NewsLookup* / ResearchRun* / WebLookupRun*` 现役合同、durable `/news/runs*`、SQLite NewsRun 与恢复语义保持不变。\n",
        "- 最终代码 head `0d634dbcd0bd66bdab919efc9ba7cbbde69110cd`，CI run `31177047560` 完整通过；\n- 最终 PR head `bc3c06f043eae5f195516741c88a45205e21864b`，CI run `31177513884` 完整通过；\n- 功能 merge SHA `39e5efe91a75099b6cf5646aa9060d2945b5604c`；\n- `NewsRun* / NewsLookup* / ResearchRun* / WebLookupRun*` 现役合同、durable `/news/runs*`、SQLite NewsRun 与恢复语义保持不变。\n",
        "section 2.6 merge facts",
    )

    source = replace_once(
        source,
        "- 最终代码 head：`0d634dbcd0bd66bdab919efc9ba7cbbde69110cd`；\n- 最终代码 CI：run `31177047560`，结论 `success`。\n",
        "- 最终代码 head：`0d634dbcd0bd66bdab919efc9ba7cbbde69110cd`；\n- 最终代码 CI：run `31177047560`，结论 `success`；\n- 最终 PR head：`bc3c06f043eae5f195516741c88a45205e21864b`；\n- 最终 PR CI：run `31177513884`，结论 `success`；\n- 功能 merge SHA：`39e5efe91a75099b6cf5646aa9060d2945b5604c`。\n",
        "section 7.4 merge facts",
    )

    source = replace_once(
        source,
        "当前待合并功能 PR 为 #113；状态文档最终 CI 通过后即可合并，随后进入 `group / tools / timeline` adapter owner 审计。\n",
        "PR #113 已合并 `main`；P2-C 第二切片完成，当前进入第三切片：`group / tools / timeline` adapter owner、恢复、持久化与选择性加载边界审计。\n",
        "stage judgment",
    )

    PATH.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()

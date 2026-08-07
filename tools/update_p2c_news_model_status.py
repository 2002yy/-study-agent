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
        "> 更新：2026-08-06  \n",
        "> 更新：2026-08-07  \n",
        "date",
    )
    source = replace_once(
        source,
        "> 当前切片：**PR #112 已 squash 合并 `main`；最终 head `6976fde10d2b201e0ba0019bcbab96939cb272c6` 的 CI run `31116107948` 完整通过，功能 merge SHA `9482be8b5d73ba6a407a208c00af92ccc478ff96`。**  \n",
        "> 当前切片：**Draft PR #113 已退出 10 个无生产 owner 的旧 News 阶段 Pydantic 模型、两层兼容导出和无路由 owner 的 `news_result_payload`；最终代码 head `0d634dbcd0bd66bdab919efc9ba7cbbde69110cd`，CI run `31177047560` 完整通过。**  \n",
        "current slice",
    )
    source = replace_once(
        source,
        "> 下一主线：**P2-C 第二切片审计并退出无 owner 的旧 News Pydantic 类型与 `src.api` 兼容导出；随后再处理旧 `group / tools / timeline` adapter。**  \n",
        "> 下一主线：**P2-C 第三切片盘点并退出无 owner 的旧 `group / tools / timeline` 新 UI adapter；只在实验室现役恢复与调用链证明无依赖后删除。**  \n",
        "next line",
    )

    old_progress = "- 旧 News Pydantic 类型与 `src.api` 导出暂时保留，等待下一独立切片证明 owner 后退出。\n"
    new_progress = """- PR #113：旧 News 阶段模型与兼容导出退出；\n- 有效红边界 commit `b400b2db38393882c2db52aba38ee513ed9366d6`，CI run `31176698695`：905 项通过、1 项按预期失败；\n- 红边界额外发现 `src/application/helpers.py::news_result_payload` 仍引用 `NewsSearchResponse`，确认其已无路由 owner 后同步退出；\n- 最终代码 head `0d634dbcd0bd66bdab919efc9ba7cbbde69110cd`，CI run `31177047560` 完整通过；\n- `NewsRun* / NewsLookup* / ResearchRun* / WebLookupRun*` 现役合同、durable `/news/runs*`、SQLite NewsRun 与恢复语义保持不变。\n"""
    source = replace_once(source, old_progress, new_progress, "progress section")

    validation_marker = "\n## 8. 后续任务\n"
    validation = """
### 7.4 PR #113 代码基线

- 分支：`agent/remove-legacy-news-models`；
- 有效红边界 commit：`b400b2db38393882c2db52aba38ee513ed9366d6`；
- 有效红 CI：run `31176698695`，905 项通过、1 项按预期失败；
- 红边界 offender 仅位于 `src/api/__init__.py`、`src/api/models/__init__.py`、`src/api/models/news.py` 与 `src/application/helpers.py`；
- 最终代码 head：`0d634dbcd0bd66bdab919efc9ba7cbbde69110cd`；
- 最终代码 CI：run `31177047560`，结论 `success`。

最终代码基线完整通过：

- 全量 pytest，包括旧模型不得回流与现役 News 合同保护边界；
- RAG K1 固定 corpus；
- Ruff、项目打包、detect-secrets；
- expanded mypy baseline gate；
- 全量前端测试与 TypeScript / Vite production build；
- desktop、mobile、360×520 Golden Journeys；
- 真实 FastAPI + SQLite 浏览器门禁。

删除范围严格限定为 10 个旧阶段 Pydantic 模型、两层兼容 re-export 和无路由 owner 的 `news_result_payload`；没有删除或改写现役 durable NewsRun、NewsLookup、ResearchRun、WebLookupRun 合同。
"""
    if validation_marker not in source:
        raise RuntimeError("validation marker missing")
    source = source.replace(validation_marker, "\n" + validation + validation_marker, 1)

    start = source.index("### P2-C：兼容层退出\n")
    end = source.index("### P2-D：源码学习与验证增强\n", start)
    p2c = """### P2-C：兼容层退出

1. PR #112 已退出六条旧 News 410 tombstone，并由永久边界阻止旧路径回流；
2. PR #113 已退出 10 个旧 News 阶段模型、两层兼容导出和 `news_result_payload`，现役 durable / lookup / research 合同保持不变；
3. 下一切片盘点旧 `group / tools / timeline` 新 UI adapter 的恢复、持久化和调用来源；
4. 只有在实验室入口、ExtensionRuntime 恢复和选择性加载均证明无依赖后，才删除无 owner adapter；
5. 每个删除切片继续保持 API、持久化、普通模式和真实浏览器闭环不变。

"""
    source = source[:start] + p2c + source[end:]

    stage = source.index("## 9. 阶段判断\n")
    source = source[:stage] + """## 9. 阶段判断

P2-C 第二切片已完成代码与回归基线：

- 10 个旧 News 阶段 Pydantic 模型已从 owner 模块删除；
- `src/api/models/__init__.py` 与 `src/api/__init__.py` 不再提供这些兼容导出；
- 红边界发现的 `news_result_payload` / `_news_result_payload` 无路由 owner 残留已同步删除；
- `NewsRun* / NewsLookup* / ResearchRun* / WebLookupRun*` 继续受到永久测试保护；
- durable `/news/runs*`、SQLite NewsRun、恢复语义、前端和真实浏览器闭环均未回归。

当前待合并功能 PR 为 #113；状态文档最终 CI 通过后即可合并，随后进入 `group / tools / timeline` adapter owner 审计。
"""

    PATH.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()

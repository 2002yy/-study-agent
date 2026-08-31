# Failure-State Writer Inventory (Batch B input)

Static scan of production writers that must be canonicalized in Batch B.
Batch A only reports; none of these are modified here.

## src\api\routes\chat_routes.py

- `src\api\routes\chat_routes.py:165: type(exc).__name__: {"message": str(exc), "error_type": type(exc).__name__},`
- `src\api\routes\chat_routes.py:260: type(exc).__name__: {"message": str(exc), "error_type": type(exc).__name__},`

## src\api\routes\wechat_routes.py

- `src\api\routes\wechat_routes.py:177: type(exc).__name__: "error", {"message": str(exc), "error_type": type(exc).__name__}`

## src\application\active_research_runtime.py

- `src\application\active_research_runtime.py:236: stop_reason writer: stop_reason="",`
- `src\application\active_research_runtime.py:323: RuntimeFailure writer: failures=(*cursor.failures, RuntimeFailure(code=code, phase=phase, item_id=item_id)),`
- `src\application\active_research_runtime.py:623: error_code writer: error_code=outcome.reason if outcome.status == "unavailable" else "",`
- `src\application\active_research_runtime.py:883: type(exc).__name__: "error": type(exc).__name__,`
- `src\application\active_research_runtime.py:903: error_code writer: error_code="" if ok else _bounded_text(raw_read.get("error") or "read_failed", 200),`
- `src\application\active_research_runtime.py:1160: type(exc).__name__: _append_failure(type(exc).__name__, cursor.phase)`

## src\application\github_snapshot_service.py

- `src\application\github_snapshot_service.py:255: type(exc).__name__: "error": f"{type(exc).__name__}: {exc}",`

## src\application\learning_freshness.py

- `src\application\learning_freshness.py:170: type(exc).__name__: message = f"blob_read_failed: {type(exc).__name__}: {exc}"`
- `src\application\learning_freshness.py:235: type(exc).__name__: "error": f"{type(exc).__name__}: {exc}",`

## src\application\learning_resume.py

- `src\application\learning_resume.py:217: type(exc).__name__: "unavailable_reason": f"{type(exc).__name__}: {exc}",`

## src\application\learning_revalidation.py

- `src\application\learning_revalidation.py:126: type(exc).__name__: return f"unavailable: {type(exc).__name__}: {exc}"`

## src\application\web_lookup_service.py

- `src\application\web_lookup_service.py:743: stop_reason writer: stop_reason="chat_tool_loop_failed",`
- `src\application\web_lookup_service.py:1098: type(exc).__name__: "error": f"{type(exc).__name__}: {exc}",`
- `src\application\web_lookup_service.py:1101: type(exc).__name__: f"source read failed ({url}): {type(exc).__name__}: {exc}"`
- `src\application\web_lookup_service.py:1597: type(exc).__name__: "error": f"{type(exc).__name__}: {exc}",`

## src\evals\research_quality_semantic_projector.py

- `src\evals\research_quality_semantic_projector.py:196: type(exc).__name__: "error_type": type(exc).__name__,`
- `src\evals\research_quality_semantic_projector.py:398: type(exc).__name__: error_type = type(exc).__name__`

## src\infrastructure\sqlite\database.py

- `src\infrastructure\sqlite\database.py:403: stop_reason writer: stop_reason = 'legacy_run_interrupted',`

## src\llm_client.py

- `src\llm_client.py:626: type(exc).__name__: result = {"error": f"{type(exc).__name__}: {exc}"}`

## src\news\article_fetcher.py

- `src\news\article_fetcher.py:367: type(exc).__name__: reason=f"exception:{type(exc).__name__}:{exc}",`

## src\news\search_sources\searxng_source.py

- `src\news\search_sources\searxng_source.py:201: type(exc).__name__: _LAST_SEARXNG_ERROR = f"{type(exc).__name__}: {exc}"`

## src\pedagogy\evaluation.py

- `src\pedagogy\evaluation.py:231: type(exc).__name__: reasons=(f"semantic_evaluator_failed:{type(exc).__name__}",),`

## src\rag\answer_claim_eval.py

- `src\rag\answer_claim_eval.py:265: type(exc).__name__: parse_error=f"{type(exc).__name__}: {exc}",`
- `src\rag\answer_claim_eval.py:457: type(exc).__name__: parse_error=f"producer_failed:{type(exc).__name__}",`

## src\rag\provider_replay.py

- `src\rag\provider_replay.py:206: type(exc).__name__: parse_error=f"{type(exc).__name__}: {exc}",`
- `src\rag\provider_replay.py:280: type(exc).__name__: "error_type": type(exc).__name__,`

## src\repositories\web_lookup_repository.py

- `src\repositories\web_lookup_repository.py:632: stop_reason writer: stop_reason = 'user_cancelled', completed_at = ?,`
- `src\repositories\web_lookup_repository.py:670: stop_reason writer: research_context = ?, stop_reason = 'user_cancelled',`

## src\tools\persistent_web_agent.py

- `src\tools\persistent_web_agent.py:169: type(exc).__name__: f"ResearchRun create failed: {type(exc).__name__}: {exc}"`
- `src\tools\persistent_web_agent.py:235: type(exc).__name__: "error": f"{type(exc).__name__}: {exc}",`
- `src\tools\persistent_web_agent.py:330: type(exc).__name__: error = f"{type(exc).__name__}: {exc}"`
- `src\tools\persistent_web_agent.py:423: type(exc).__name__: error = f"{type(exc).__name__}: {exc}"`
- `src\tools\persistent_web_agent.py:424: type(exc).__name__: cancelled = "ResearchCancelled" in type(exc).__name__ or (`
- `src\tools\persistent_web_agent.py:455: type(exc).__name__: return f"ResearchRun persistence failed: {type(exc).__name__}: {exc}"`

## src\tools\web_agent.py

- `src\tools\web_agent.py:386: type(exc).__name__: return WebToolTrace(error=f"{type(exc).__name__}: {exc}")`

## src\web\github_change_impact.py

- `src\web\github_change_impact.py:216: type(exc).__name__: "error": f"{type(exc).__name__}: {exc}",`

## src\web\github_freshness.py

- `src\web\github_freshness.py:38: type(exc).__name__: return f"{type(exc).__name__}: {exc}"`

## src\web\github_history.py

- `src\web\github_history.py:63: type(exc).__name__: return None, f"{type(exc).__name__}: {exc}"`
- `src\web\github_history.py:239: type(exc).__name__: return None, f"{type(exc).__name__}: {exc}"`
- `src\web\github_history.py:270: type(exc).__name__: error=f"{type(exc).__name__}: {exc}",`
- `src\web\github_history.py:516: type(exc).__name__: "error": f"{type(exc).__name__}: {exc}",`
- `src\web\github_history.py:639: type(exc).__name__: "error": f"{type(exc).__name__}: {exc}",`

## src\web\github_paginated_base.py

- `src\web\github_paginated_base.py:156: stop_reason writer: stop_reason = "provider_exhausted"`
- `src\web\github_paginated_base.py:166: stop_reason writer: stop_reason = "request_budget_exhausted"`
- `src\web\github_paginated_base.py:182: type(exc).__name__: _provider_error(operation, f"{type(exc).__name__}: {exc}")`
- `src\web\github_paginated_base.py:184: stop_reason writer: stop_reason = "provider_error"`
- `src\web\github_paginated_base.py:191: stop_reason writer: stop_reason = "provider_error"`
- `src\web\github_paginated_base.py:239: stop_reason writer: stop_reason = "item_budget_reached"`
- `src\web\github_paginated_base.py:246: stop_reason writer: stop_reason = "provider_exhausted"`
- `src\web\github_paginated_base.py:252: stop_reason writer: stop_reason = "provider_error"`
- `src\web\github_paginated_base.py:255: stop_reason writer: stop_reason = "page_budget_exhausted"`
- `src\web\github_paginated_base.py:338: stop_reason writer: stop_reason = "provider_exhausted"`
- `src\web\github_paginated_base.py:360: stop_reason writer: stop_reason = "page_budget_exhausted"`
- `src\web\github_paginated_base.py:367: stop_reason writer: stop_reason = "provider_error"`
- `src\web\github_paginated_base.py:373: stop_reason writer: stop_reason = "request_budget_exhausted"`
- `src\web\github_paginated_base.py:390: type(exc).__name__: _provider_error(operation, f"{type(exc).__name__}: {exc}")`
- `src\web\github_paginated_base.py:392: stop_reason writer: stop_reason = "provider_error"`
- `src\web\github_paginated_base.py:400: stop_reason writer: stop_reason = "provider_error"`
- `src\web\github_paginated_base.py:420: stop_reason writer: stop_reason = "item_budget_reached"`
- `src\web\github_paginated_base.py:422: stop_reason writer: stop_reason = "provider_exhausted"`

## src\web\github_provider_pagination.py

- `src\web\github_provider_pagination.py:133: stop_reason writer: stop_reason = "provider_exhausted"`
- `src\web\github_provider_pagination.py:155: stop_reason writer: stop_reason = "item_budget_reached"`
- `src\web\github_provider_pagination.py:159: stop_reason writer: stop_reason = "provider_exhausted"`
- `src\web\github_provider_pagination.py:164: stop_reason writer: stop_reason = "page_budget_exhausted"`

## src\web\github_reader.py

- `src\web\github_reader.py:233: type(exc).__name__: "error": f"{type(exc).__name__}: {exc}",`
- `src\web\github_reader.py:294: type(exc).__name__: "error": f"{type(exc).__name__}: {exc}",`

## src\web\github_snapshot.py

- `src\web\github_snapshot.py:293: type(exc).__name__: "error": f"{type(exc).__name__}: {exc}",`
- `src\web\github_snapshot.py:377: type(exc).__name__: "error": f"{type(exc).__name__}: {exc}",`

## src\web\github_work_items.py

- `src\web\github_work_items.py:253: type(exc).__name__: return None, _provider_error(operation, f"{type(exc).__name__}: {exc}")`
- `src\web\github_work_items.py:378: type(exc).__name__: "error": f"{type(exc).__name__}: {exc}",`
- `src\web\github_work_items.py:1155: type(exc).__name__: "error": f"{type(exc).__name__}: {exc}",`

## src\web\lsp_adapter.py

- `src\web\lsp_adapter.py:112: type(exc).__name__: error=f"{type(exc).__name__}: {exc}",`

## src\web\provider_health.py

- `src\web\provider_health.py:50: type(exc).__name__: return False, f"{type(exc).__name__}: {exc}"`

## src\web\research\candidate_pool.py

- `src\web\research\candidate_pool.py:160: type(exc).__name__: provider_errors = (f"search_exception:{type(exc).__name__}",)`

## src\web\research\model_gateway.py

- `src\web\research\model_gateway.py:389: type(exc).__name__: error_type = type(exc).__name__`

## src\web\research\provider_search.py

- `src\web\research\provider_search.py:362: type(exc).__name__: name = type(exc).__name__.casefold()`

## src\web\research\runtime.py

- `src\web\research\runtime.py:148: error_code writer: error_code=_optional_text(data.get("error_code"), 200),`
- `src\web\research\runtime.py:249: error_code writer: error_code=_optional_text(data.get("error_code"), 200),`
- `src\web\research\runtime.py:359: RuntimeFailure writer: return RuntimeFailure(`
- `src\web\research\runtime.py:732: RuntimeFailure writer: failure = RuntimeFailure(`
- `src\web\research\runtime.py:770: RuntimeFailure writer: failure = RuntimeFailure(`

## src\web\tool_gateway.py

- `src\web\tool_gateway.py:449: type(exc).__name__: return [], f"bing_rss:{type(exc).__name__}:{exc}"`
- `src\web\tool_gateway.py:492: type(exc).__name__: return [], f"duckduckgo_html:{type(exc).__name__}:{exc}"`

## src\web\tree_sitter_backend\__init__.py

- `src\web\tree_sitter_backend\__init__.py:58: type(exc).__name__: parse_error=f"{type(exc).__name__}: {exc}",`

## src\wechat_service.py

- `src\wechat_service.py:373: type(exc).__name__: data={"error_type": type(exc).__name__},`
- `src\wechat_service.py:403: type(exc).__name__: data={"error_type": type(exc).__name__},`


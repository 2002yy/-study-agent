# Testing

## Test Suite

Current verified baseline:

| Check | Status | Evidence |
|---|---|---|
| pytest | Passed | 136 test files / 888 tests passed locally on 2026-08-03 |
| Ruff | Passed | `python -m ruff check src tests tools` clean locally on 2026-08-03 |
| Package helper | Passed | `python tools/package_project_helper.py . <temp.zip> 0` passed locally on 2026-08-03 |
| mypy | Baseline gate passed | 125 current findings <= 127 baseline on 2026-08-03 |
| detect-secrets | CI hard gate configured | Workflow parses scan JSON and fails when `results` contains any unallowlisted finding; local tracked-file scan was empty on 2026-06-07 |
| Frontend build | Passed | `npm ci && npm run build` under `frontend/` locally on 2026-06-07 |
| GitHub Actions | Recent main runs passing | Latest 6 CI runs on `main` were `success` when checked on 2026-06-03 |

### Categories

| Area | File | Tests |
|---|---|---|
| **Packaging guards** | `test_packaging_guards.py` | 29 |
| **Performance budget** | `test_performance_budget.py` | 15 |
| **News service** | `test_wechat_service_news_flow.py` | 7 |
| **News URL safety** | `test_url_normalizer.py`, `test_link_resolver.py` | 29 |
| **News pipeline trace / audit** | `test_news_pipeline_trace.py`, `test_news_audit.py` | 6 |
| **Feed registry / health** | `test_feed_registry.py`, `test_feed_diagnostics.py` | 9 |
| **RAG MVP** | `test_rag.py` | 26 |
| **RAG evaluation** | `test_rag_eval.py` | 8 |
| **RAG vector backends** | `test_rag_backends.py` | 12 |
| **Controlled local knowledge tool** | `test_local_knowledge_tool.py` | 7 |
| **Evaluation quality gates** | `test_eval_quality_gates.py` | 17 |
| **FastAPI service endpoints** | `test_api.py` | 48 |
| **Workflow / tool registry** | `test_workflow_tool_registry.py` | 4 |
| **Architecture flows** | `test_architecture_flows.py` | 20 |
| **WeChat decoupling** | `test_wechat_decoupling.py` | 3 |
| Various unit tests | (spread across test directory) | — |

### Test Characteristics

- **Self-contained**: Tests use `monkeypatch` for LLM calls, file I/O isolation
- **Source-code checks**: Many tests verify source code patterns (e.g., "no direct file open in flush path")
- **Pure function tests**: Business logic is tested below the presentation layer
- **State machine tests**: Durable news, group, learning, and recovery transitions
- **Version sync guard**: Runtime version asserted across 3 files (mode_manager, YAML, memory view)

### Key Patterns

**Source-code assertions** for behavioral invariants:

```python
def test_flush_uses_safe_writer():
    block = text[block_start:block_end]
    assert "safe_write_text(current_file, existing + chunk)" in block
    assert "with current_file.open(" not in block
```

## CI Pipeline

`.github/workflows/ci.yml` runs on every push and pull request:

| Step | Action | Gate |
|---|---|---|
| Install deps | `pip install -r requirements.txt -r requirements-dev.txt` | — |
| Lint | `ruff check .` | Hard |
| Test | `pytest` | Hard |
| Package check | `python tools/package_project_helper.py` | Hard |
| Secret scan | `detect-secrets` | Hard gate for any unallowlisted finding |
| Type check | `mypy --explicit-package-bases src/` | Soft (continue-on-error) |
| Frontend build | `npm ci && npm run build` in `frontend/` | Hard |

## Running Tests

```bash
python -m pytest             # current baseline: 888 passed
pytest tests/ -v             # Verbose
pytest tests/ --cov=src      # Coverage
python -m ruff check .       # Linting
python -m mypy --explicit-package-bases src   # Type check; CI currently runs it as a soft check
```

Tracked-file secret scan used for local verification:

```bash
detect-secrets scan --disable-plugin KeywordDetector --exclude-files '.*\.(pyc|jpg|png|zip)$' .github README.md docs src tests tools config templates roles changelog assets frontend .env.example
npm --prefix frontend ci
npm --prefix frontend run build
```

The intentional Basic Auth-shaped URL fixture in `tests/test_url_normalizer.py` is marked with an inline allowlist comment. The CI workflow parses the scan JSON and fails if any file has non-empty `results`, so the gate no longer depends on a version-specific field such as `is_secret` or `is_verified`.

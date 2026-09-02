from pathlib import Path
import re

catalog = Path("src/web/research/failure_contracts.py")
text = catalog.read_text(encoding="utf-8")
old = '        "search_candidates_only",\n        "empty",\n        "candidates_only",\n        "chat_tool_loop_failed",'
new = '        "search_candidates_only",\n        "no_tool_calls",\n        "insufficient_valid_sources",\n        "sources_read",\n        "sources_partially_read",\n        "source_reading_failed",\n        "chat_tool_loop_failed",'
if text.count(old) != 1:
    raise SystemExit(f"expected one frozenset stop catalog block, found {text.count(old)}")
catalog.write_text(text.replace(old, new, 1), encoding="utf-8")

repository = Path("src/repositories/web_lookup_repository.py")
text = repository.read_text(encoding="utf-8")
old = (
    '            raise ValueError(\n'
    '                "Follow-up child requires create_request_id, parent_run_id and owner_thread_id"\n'
    '            )\n'
    '        context = _with_operation('
)
new = (
    '            raise ValueError(\n'
    '                "Follow-up child requires create_request_id, parent_run_id and owner_thread_id"\n'
    '            )\n'
    '        stop_reason = _validated_stop_reason(run.stop_reason)\n'
    '        context = _with_operation('
)
if text.count(old) != 1:
    raise SystemExit(f"expected one create_child anchor, found {text.count(old)}")
repository.write_text(text.replace(old, new, 1), encoding="utf-8")

script = Path(".github/tmp_batch_c_repair.py")
source = script.read_text(encoding="utf-8")
pattern = re.compile(
    r'replace_once\(\n'
    r'    "src/repositories/web_lookup_repository\.py",\n'
    r'    "        context = _with_operation.*?\n'
    r'\)\n'
    r'(?=replace_once\(\n'
    r'    "src/repositories/web_lookup_repository\.py",\n'
    r'    "                        child\.provider_status)',
    flags=re.DOTALL,
)
source, count = pattern.subn("", source, count=1)
if count != 1:
    raise SystemExit(f"expected one ambiguous repair-script block, found {count}")
script.write_text(source, encoding="utf-8")

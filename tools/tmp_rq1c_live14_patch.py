from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected one anchor in {path}, found {count}: {old[:100]!r}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


candidate = "src/web/research/candidate_assessment.py"
replace_once(
    candidate,
    'class CompactAssessmentCodeError(ValueError):\n'
    '    """Compact response contains an unknown or malformed enum code."""\n',
    'class CompactAssessmentCodeError(ValueError):\n'
    '    """Compact response contains an unknown or malformed enum code."""\n\n\n'
    'class CompactAssessmentRelevanceCodeError(CompactAssessmentCodeError):\n'
    '    """Compact relevance code is unknown or malformed."""\n\n\n'
    'class CompactAssessmentSourceRoleCodeError(CompactAssessmentCodeError):\n'
    '    """Compact source-role code is unknown or malformed."""\n\n\n'
    'class CompactAssessmentGainSignalCodeError(CompactAssessmentCodeError):\n'
    '    """Compact gain-signal code is unknown or malformed."""\n\n\n'
    'class CompactAssessmentGainSignalDuplicateError(CompactAssessmentCodeError):\n'
    '    """Compact gain-signal list repeats a decoded semantic value."""\n',
)
replace_once(
    candidate,
    '                "relevance": _compact_code(\n'
    '                    raw.get("r"), CANDIDATE_ASSESSMENT_RELEVANCE_CODES, "relevance"\n'
    '                ),',
    '                "relevance": _compact_code(\n'
    '                    raw.get("r"),\n'
    '                    CANDIDATE_ASSESSMENT_RELEVANCE_CODES,\n'
    '                    "relevance",\n'
    '                    CompactAssessmentRelevanceCodeError,\n'
    '                ),',
)
replace_once(
    candidate,
    '                "source_role": _compact_code(\n'
    '                    raw.get("s"),\n'
    '                    CANDIDATE_ASSESSMENT_SOURCE_ROLE_CODES,\n'
    '                    "source role",\n'
    '                ),',
    '                "source_role": _compact_code(\n'
    '                    raw.get("s"),\n'
    '                    CANDIDATE_ASSESSMENT_SOURCE_ROLE_CODES,\n'
    '                    "source role",\n'
    '                    CompactAssessmentSourceRoleCodeError,\n'
    '                ),',
)
replace_once(
    candidate,
    'def _compact_code(value: Any, codes: Mapping[int, str], label: str) -> str:\n'
    '    if isinstance(value, bool) or not isinstance(value, int) or value not in codes:\n'
    '        raise CompactAssessmentCodeError(f"compact {label} code invalid")\n'
    '    return codes[value]\n\n\n'
    'def _compact_codes(value: Any, codes: Mapping[int, str]) -> list[str]:\n'
    '    if not isinstance(value, list):\n'
    '        raise CompactAssessmentCodeError("compact gain signal codes invalid")\n'
    '    result: list[str] = []\n'
    '    for item in value:\n'
    '        decoded = _compact_code(item, codes, "gain signal")\n'
    '        if decoded in result:\n'
    '            raise CompactAssessmentCodeError("compact gain signal codes duplicate")\n'
    '        result.append(decoded)\n'
    '    return result\n',
    'def _compact_code(\n'
    '    value: Any,\n'
    '    codes: Mapping[int, str],\n'
    '    label: str,\n'
    '    error_type: type[CompactAssessmentCodeError] = CompactAssessmentCodeError,\n'
    ') -> str:\n'
    '    if isinstance(value, bool) or not isinstance(value, int) or value not in codes:\n'
    '        raise error_type(f"compact {label} code invalid")\n'
    '    return codes[value]\n\n\n'
    'def _compact_codes(value: Any, codes: Mapping[int, str]) -> list[str]:\n'
    '    if not isinstance(value, list):\n'
    '        raise CompactAssessmentGainSignalCodeError("compact gain signal codes invalid")\n'
    '    result: list[str] = []\n'
    '    for item in value:\n'
    '        decoded = _compact_code(\n'
    '            item,\n'
    '            codes,\n'
    '            "gain signal",\n'
    '            CompactAssessmentGainSignalCodeError,\n'
    '        )\n'
    '        if decoded in result:\n'
    '            raise CompactAssessmentGainSignalDuplicateError(\n'
    '                "compact gain signal codes duplicate"\n'
    '            )\n'
    '        result.append(decoded)\n'
    '    return result\n',
)
replace_once(
    candidate,
    '    "CompactAssessmentCoverageError",\n'
    '    "CompactAssessmentCodeError",\n'
    '    "CompactAssessmentDomainError",\n',
    '    "CompactAssessmentCoverageError",\n'
    '    "CompactAssessmentCodeError",\n'
    '    "CompactAssessmentDomainError",\n'
    '    "CompactAssessmentGainSignalCodeError",\n'
    '    "CompactAssessmentGainSignalDuplicateError",\n'
    '    "CompactAssessmentRelevanceCodeError",\n'
    '    "CompactAssessmentSourceRoleCodeError",\n',
)

candidate_test = "tests/test_research_candidate_assessment.py"
replace_once(
    candidate_test,
    '    CompactAssessmentCodeError,\n    build_candidate_assessment_request,\n',
    '    CompactAssessmentCodeError,\n'
    '    CompactAssessmentGainSignalCodeError,\n'
    '    CompactAssessmentGainSignalDuplicateError,\n'
    '    CompactAssessmentRelevanceCodeError,\n'
    '    CompactAssessmentSourceRoleCodeError,\n'
    '    build_candidate_assessment_request,\n',
)
replace_once(
    candidate_test,
    'def test_compact_parser_classifies_unknown_enum_code() -> None:\n'
    '    candidate = _candidate("a")\n'
    '    request = build_candidate_assessment_request((candidate,), claim=_claim())\n\n'
    '    with pytest.raises(CompactAssessmentCodeError):\n'
    '        parse_compact_candidate_assessment_response(\n'
    '            {\n'
    '                "v": CANDIDATE_ASSESSMENT_WIRE_SCHEMA_VERSION,\n'
    '                "a": [{"i": 0, "r": 99, "rc": 0.8, "s": 1, "sc": 0.9, "g": [0]}],\n'
    '            },\n'
    '            request=request,\n'
    '            cluster_assignments={"a": _assignment("a")},\n'
    '        )\n',
    '@pytest.mark.parametrize(\n'
    '    ("field", "value", "error_type"),\n'
    '    [\n'
    '        ("r", 99, CompactAssessmentRelevanceCodeError),\n'
    '        ("s", 99, CompactAssessmentSourceRoleCodeError),\n'
    '        ("g", [99], CompactAssessmentGainSignalCodeError),\n'
    '        ("g", [0, 0], CompactAssessmentGainSignalDuplicateError),\n'
    '    ],\n'
    ')\n'
    'def test_compact_parser_classifies_code_failure_domain(\n'
    '    field: str,\n'
    '    value: object,\n'
    '    error_type: type[CompactAssessmentCodeError],\n'
    ') -> None:\n'
    '    candidate = _candidate("a")\n'
    '    request = build_candidate_assessment_request((candidate,), claim=_claim())\n'
    '    row = {"i": 0, "r": 0, "rc": 0.8, "s": 1, "sc": 0.9, "g": [0]}\n'
    '    row[field] = value\n\n'
    '    with pytest.raises(error_type):\n'
    '        parse_compact_candidate_assessment_response(\n'
    '            {"v": CANDIDATE_ASSESSMENT_WIRE_SCHEMA_VERSION, "a": [row]},\n'
    '            request=request,\n'
    '            cluster_assignments={"a": _assignment("a")},\n'
    '        )\n\n\n'
    'def test_compact_code_subclasses_preserve_fail_closed_base_contract() -> None:\n'
    '    assert issubclass(CompactAssessmentRelevanceCodeError, CompactAssessmentCodeError)\n'
    '    assert issubclass(CompactAssessmentSourceRoleCodeError, CompactAssessmentCodeError)\n'
    '    assert issubclass(CompactAssessmentGainSignalCodeError, CompactAssessmentCodeError)\n'
    '    assert issubclass(CompactAssessmentGainSignalDuplicateError, CompactAssessmentCodeError)\n',
)

diagnostic = "tools/run_rq1c_preread_diagnostic.py"
replace_once(
    diagnostic,
    'from src.repositories.web_lookup_repository import WebLookupRepository  # noqa: E402\n'
    'from tools.rq1c_git_identity import exact_checkout_git_sha  # noqa: E402\n',
    'from src.repositories.web_lookup_repository import WebLookupRepository  # noqa: E402\n'
    'from src.web.research.active_adapter import ActiveResearchGateway  # noqa: E402\n'
    'from src.web.research_gateway import ResearchWebGateway  # noqa: E402\n'
    'from tools.rq1c_git_identity import exact_checkout_git_sha  # noqa: E402\n',
)
replace_once(
    diagnostic,
    'DEFAULT_OUTPUT = REPO_ROOT / "output" / "rq1c-preread-starvation-diagnostic.json"\n',
    'DEFAULT_OUTPUT = REPO_ROOT / "output" / "rq1c-preread-starvation-diagnostic.json"\n'
    '_ASSESSOR_FAILURE_CATEGORY_BY_TYPE = {\n'
    '    "CompactAssessmentRelevanceCodeError": "compact_code_relevance",\n'
    '    "CompactAssessmentSourceRoleCodeError": "compact_code_source_role",\n'
    '    "CompactAssessmentGainSignalCodeError": "compact_code_gain_signal",\n'
    '    "CompactAssessmentGainSignalDuplicateError": "compact_code_duplicate",\n'
    '    "CompactAssessmentCodeError": "compact_code_other",\n'
    '    "CompactAssessmentDomainError": "expanded_domain",\n'
    '}\n'
    '_CANONICAL_READER_PROVIDER_CODES = frozenset(\n'
    '    {\n'
    '        "blocked",\n'
    '        "fetch_failed",\n'
    '        "http_error",\n'
    '        "http_status",\n'
    '        "invalid_url",\n'
    '        "not_found",\n'
    '        "page_read_failed",\n'
    '        "provider_failed",\n'
    '        "timeout",\n'
    '        "unsupported",\n'
    '    }\n'
    ')\n',
)
replace_once(
    diagnostic,
    'def _model_call_rows(runtime: Mapping[str, Any]) -> list[dict[str, Any]]:\n',
    'def _canonical_provider_code(value: Any) -> str:\n'
    '    label = _bounded(value, 80).casefold().replace("-", "_")\n'
    '    if not label:\n'
    '        return ""\n'
    '    return label if label in _CANONICAL_READER_PROVIDER_CODES else "other"\n\n\n'
    'class _DiagnosticReadGateway:\n'
    '    """Observe safe failure classes while preserving the production read result."""\n\n'
    '    def __init__(self, inner: Any | None = None) -> None:\n'
    '        self._inner = inner if inner is not None else ResearchWebGateway()\n'
    '        self._failure_category_counts: dict[str, int] = {}\n'
    '        self._provider_code_counts: dict[str, int] = {}\n\n'
    '    @staticmethod\n'
    '    def _increment(bucket: dict[str, int], key: str) -> None:\n'
    '        bucket[key] = bucket.get(key, 0) + 1\n\n'
    '    def read(self, url: str, *, max_chars: int = 6000) -> Any:\n'
    '        try:\n'
    '            result = self._inner.read(url, max_chars=max_chars)\n'
    '        except Exception:\n'
    '            self._increment(self._failure_category_counts, "exception")\n'
    '            raise\n'
    '        if not isinstance(result, Mapping):\n'
    '            return result\n'
    '        content = str(result.get("content") or result.get("readme") or "")\n'
    '        if result.get("ok") is True:\n'
    '            if not content.strip():\n'
    '                self._increment(self._failure_category_counts, "empty_content")\n'
    '        else:\n'
    '            self._increment(self._failure_category_counts, "gateway_negative_result")\n'
    '            provider_code = _canonical_provider_code(result.get("error_code"))\n'
    '            if provider_code:\n'
    '                self._increment(self._provider_code_counts, provider_code)\n'
    '        return result\n\n'
    '    def summary(self) -> dict[str, Any]:\n'
    '        return {\n'
    '            "failure_category_counts": dict(sorted(self._failure_category_counts.items())),\n'
    '            "provider_code_counts": dict(sorted(self._provider_code_counts.items())),\n'
    '            "stores_candidate_identity": False,\n'
    '            "stores_failure_detail": False,\n'
    '            "stores_page_content": False,\n'
    '        }\n\n\n'
    'def _assessor_failure_summary(model_calls: list[dict[str, Any]]) -> dict[str, Any]:\n'
    '    counts: dict[str, int] = {}\n'
    '    for row in model_calls:\n'
    '        if row.get("purpose") != "research_candidate_assessment":\n'
    '            continue\n'
    '        category = _ASSESSOR_FAILURE_CATEGORY_BY_TYPE.get(str(row.get("error_type") or ""))\n'
    '        if category:\n'
    '            counts[category] = counts.get(category, 0) + 1\n'
    '    return {\n'
    '        "failure_category_counts": dict(sorted(counts.items())),\n'
    '        "stores_candidate_identity": False,\n'
    '        "stores_failure_detail": False,\n'
    '    }\n\n\n'
    'def _model_call_rows(runtime: Mapping[str, Any]) -> list[dict[str, Any]]:\n',
)
replace_once(
    diagnostic,
    '    service: ClaimEngineDispatchWebLookupService,\n    reference_date: str,\n',
    '    reference_date: str,\n',
)
replace_once(
    diagnostic,
    '    error_type = ""\n'
    '    try:\n'
    '        completed = service.execute(run.id, raise_on_error=False)\n',
    '    diagnostic_reader = _DiagnosticReadGateway()\n'
    '    service = ClaimEngineDispatchWebLookupService(\n'
    '        repository,\n'
    '        active_gateway_factory=lambda: ActiveResearchGateway(read_gateway=diagnostic_reader),\n'
    '    )\n'
    '    error_type = ""\n'
    '    try:\n'
    '        completed = service.execute(run.id, raise_on_error=False)\n',
)
replace_once(
    diagnostic,
    '            "assessment_summary": _assessment_summary(context),\n'
    '            "read_failure_summary": _read_failure_summary(runtime),\n',
    '            "assessment_summary": _assessment_summary(context),\n'
    '            "assessor_failure_summary": _assessor_failure_summary(model_calls),\n'
    '            "read_failure_summary": _read_failure_summary(runtime),\n'
    '            "reader_failure_classification": diagnostic_reader.summary(),\n',
)
replace_once(
    diagnostic,
    '        service = ClaimEngineDispatchWebLookupService(repository)\n'
    '        for case in cases:\n'
    '            record = _run_case(\n'
    '                case=case,\n'
    '                repository=repository,\n'
    '                service=service,\n'
    '                reference_date=reference_date,\n'
    '            )\n',
    '        for case in cases:\n'
    '            record = _run_case(\n'
    '                case=case,\n'
    '                repository=repository,\n'
    '                reference_date=reference_date,\n'
    '            )\n',
)
replace_once(
    diagnostic,
    '                        "model_calls": record["runtime"]["model_call_count"],\n'
    '                        "reads": record["runtime"]["read_count"],\n',
    '                        "model_calls": record["runtime"]["model_call_count"],\n'
    '                        "reads": record["runtime"]["read_count"],\n'
    '                        "assessor_failure_categories": record["runtime"][\n'
    '                            "assessor_failure_summary"\n'
    '                        ]["failure_category_counts"],\n'
    '                        "reader_failure_categories": record["runtime"][\n'
    '                            "reader_failure_classification"\n'
    '                        ]["failure_category_counts"],\n'
    '                        "reader_provider_codes": record["runtime"][\n'
    '                            "reader_failure_classification"\n'
    '                        ]["provider_code_counts"],\n',
)

diagnostic_test = "tests/test_rq1c_preread_diagnostic.py"
replace_once(
    diagnostic_test,
    'from __future__ import annotations\n\n'
    'from tools.run_rq1c_preread_diagnostic import (\n'
    '    _assessment_summary,\n'
    '    _read_failure_summary,\n'
    ')\n',
    'from __future__ import annotations\n\n'
    'import pytest\n\n'
    'from tools.run_rq1c_preread_diagnostic import (\n'
    '    _DiagnosticReadGateway,\n'
    '    _assessment_summary,\n'
    '    _assessor_failure_summary,\n'
    '    _read_failure_summary,\n'
    ')\n',
)
test_path = Path(diagnostic_test)
test_path.write_text(
    test_path.read_text(encoding="utf-8")
    + '''


def test_assessor_failure_summary_splits_safe_compact_domains() -> None:
    summary = _assessor_failure_summary(
        [
            {"purpose": "research_candidate_assessment", "error_type": "CompactAssessmentRelevanceCodeError"},
            {"purpose": "research_candidate_assessment", "error_type": "CompactAssessmentSourceRoleCodeError"},
            {"purpose": "research_candidate_assessment", "error_type": "CompactAssessmentGainSignalCodeError"},
            {"purpose": "research_candidate_assessment", "error_type": "CompactAssessmentGainSignalDuplicateError"},
            {"purpose": "research_candidate_assessment", "error_type": "CompactAssessmentDomainError"},
            {"purpose": "research_candidate_assessment", "error_type": "TimeoutError"},
            {"purpose": "research_evidence_extraction", "error_type": "CompactAssessmentRelevanceCodeError"},
        ]
    )
    assert summary == {
        "failure_category_counts": {
            "compact_code_duplicate": 1,
            "compact_code_gain_signal": 1,
            "compact_code_relevance": 1,
            "compact_code_source_role": 1,
            "expanded_domain": 1,
        },
        "stores_candidate_identity": False,
        "stores_failure_detail": False,
    }


class _ReaderStub:
    def read(self, url: str, *, max_chars: int = 6000):
        del max_chars
        if url.endswith("exception"):
            raise TimeoutError("private timeout detail")
        if url.endswith("empty"):
            return {"ok": True, "content": "   ", "url": "private-empty"}
        if url.endswith("known-negative"):
            return {
                "ok": False,
                "error": "private upstream detail",
                "error_code": "timeout",
                "url": "private-known",
            }
        return {
            "ok": False,
            "error": "private upstream detail",
            "error_code": "private-upstream-code",
            "url": "private-unknown",
        }


def test_diagnostic_reader_classifies_failures_without_storing_content_or_identity() -> None:
    reader = _DiagnosticReadGateway(_ReaderStub())
    with pytest.raises(TimeoutError):
        reader.read("https://secret.example/exception")
    assert reader.read("https://secret.example/empty")["ok"] is True
    assert reader.read("https://secret.example/known-negative")["ok"] is False
    assert reader.read("https://secret.example/unknown-negative")["ok"] is False
    summary = reader.summary()
    assert summary == {
        "failure_category_counts": {
            "empty_content": 1,
            "exception": 1,
            "gateway_negative_result": 2,
        },
        "provider_code_counts": {"other": 1, "timeout": 1},
        "stores_candidate_identity": False,
        "stores_failure_detail": False,
        "stores_page_content": False,
    }
    serialized = str(summary)
    assert "secret.example" not in serialized
    assert "private upstream detail" not in serialized
    assert "private-upstream-code" not in serialized
''',
    encoding="utf-8",
)

from pathlib import Path
import re


CI_WORKFLOW = Path(".github/workflows/ci.yml")
AUDIT_HASH = "27" * 32


def _exclude_lines_pattern() -> re.Pattern[str]:
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    match = re.search(r"--exclude-lines '([^']+)'", text)
    assert match is not None, "CI detect-secrets --exclude-lines pattern is missing"
    return re.compile(match.group(1))


def test_ci_detect_secrets_allows_only_named_research_audit_hashes() -> None:
    pattern = _exclude_lines_pattern()

    for field in (
        "fingerprint_sha256",
        "observation_sha256",
        "input_sha256",
        "response_sha256",
        "content_sha256",
    ):
        assert pattern.search(f'"{field}": "{AUDIT_HASH}"') is not None


def test_ci_detect_secrets_does_not_allow_arbitrary_sha256_fields() -> None:
    pattern = _exclude_lines_pattern()

    assert pattern.search(f'"arbitrary_sha256": "{AUDIT_HASH}"') is None
    assert pattern.search(f'"api_key": "{AUDIT_HASH}"') is None
    assert pattern.search(f'"token": "{AUDIT_HASH}"') is None


def test_ci_detect_secrets_audit_hash_allowlist_requires_64_lowercase_hex() -> None:
    pattern = _exclude_lines_pattern()

    assert pattern.search('"input_sha256": "abc123"') is None
    assert pattern.search(f'"response_sha256": "{AUDIT_HASH.upper()}"') is None

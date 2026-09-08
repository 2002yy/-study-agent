from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "rq1c-product-api-qualification.yml"


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_product_api_workflow_requires_explicit_real_provider_trigger() -> None:
    text = _workflow_text()

    assert "github.event.head_commit.message == 'rq1c-product-api-live12'" in text
    assert "github.event_name == 'workflow_dispatch'" in text
    assert "- deepseek" in text
    assert "- openai" in text
    assert "- openrouter" in text
    assert "- siliconflow" in text
    assert "\n          - local\n" not in text
    assert "LLM_PROVIDER_PROFILE: local" not in text


def test_product_api_workflow_fails_closed_without_api_secret_or_https_endpoint() -> None:
    text = _workflow_text()

    assert "secrets.RQ1C_PRODUCT_API_KEY" in text
    assert "missing.append('RQ1C_PRODUCT_API_KEY')" in text
    assert "refusing local fallback and making zero model calls" in text
    assert "product API base_url must be an absolute https URL" in text
    assert "local/loopback provider is forbidden" in text


def test_product_api_secret_is_not_exposed_to_checkout_or_dependency_install() -> None:
    text = _workflow_text()
    configure = text.index("- name: Configure selected product provider without fallback")
    checkout = text.index("- name: Check out exact product qualification head")
    install = text.index("- name: Install Study Agent dependencies")
    secret = text.index("RQ1C_PRODUCT_API_KEY: ${{ secrets.RQ1C_PRODUCT_API_KEY }}")
    clear = text.index("- name: Clear product API credentials before evidence processing")
    protocol = text.index("- name: Run deterministic protocol probes bound to product runtime artifact")

    assert checkout < install < configure <= secret
    assert clear < protocol
    assert text.count("secrets.RQ1C_PRODUCT_API_KEY") == 1
    assert 'echo "${prefix}_API_KEY=" >> "$GITHUB_ENV"' in text


def test_product_api_config_failure_produces_sanitized_evidence() -> None:
    text = _workflow_text()

    assert "output.mkdir(exist_ok=True)" in text
    assert "rq1c-product-api-config.json" in text
    assert "'configuration_complete': not missing and not errors" in text
    assert "'secret_value_stored': False" in text
    assert "'api_key_present': bool(api_key)" in text
    assert "missing.append('RQ1C_PRODUCT_PROVIDER_PROFILE')" in text
    assert "missing.append('RQ1C_PRODUCT_DEFAULT_MODEL_PROFILE')" in text
    assert "missing.append('RQ1C_PRODUCT_BASE_URL')" in text
    assert "missing.append('RQ1C_PRODUCT_FLASH_MODEL')" in text
    assert "missing.append('RQ1C_PRODUCT_PRO_MODEL')" in text


def test_product_api_workflow_keeps_product_deadlines_and_disables_hosted_cpu_exemption() -> None:
    text = _workflow_text()

    assert "RQ1C_HOSTED_CPU_WALLCLOCK_EXEMPT: 'false'" in text
    assert "'product_soft_timeout_seconds': 45" in text
    assert "'product_hard_timeout_seconds': 60" in text
    assert "product API qualification must not use hosted-CPU exemption" in text
    assert "LLM_MAX_RETRIES: '0'" in text
    assert "product qualification requires provider-hidden retries disabled" in text


def test_product_api_workflow_reuses_frozen_runtime_and_protocol_runners() -> None:
    text = _workflow_text()

    assert "python tools/run_rq1c_bounded_qualification.py" in text
    assert "python tools/run_rq1c_protocol_probes.py" in text
    assert "RQ1C_BOUNDED_QUALIFICATION_RUNTIME.json" in text
    assert "RQ1C_BOUNDED_PROTOCOL_PROBES.json" in text
    assert "rubric_loaded_by_runtime': False" in text

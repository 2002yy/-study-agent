from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.run_rq1c_protocol_probes import REQUIRED_PROBES, run_protocol_probes


def test_deterministic_protocol_runner_exercises_all_required_probes(tmp_path: Path) -> None:
    runtime_path = tmp_path / "runtime.json"
    output_path = tmp_path / "protocol.json"
    runtime_path.write_text(
        json.dumps(
            {
                "schema_version": "rq1c-bounded-qualification-runtime-v1",
                "cases": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    artifact = run_protocol_probes(
        runtime_path=runtime_path,
        output_path=output_path,
    )

    assert tuple(probe["id"] for probe in artifact["probes"]) == REQUIRED_PROBES
    assert all(probe["status"] == "pass" for probe in artifact["probes"])
    assert artifact["summary"] == {
        "probe_count": 6,
        "passed": 6,
        "failed": [],
    }
    assert artifact["runtime_artifact_sha256"] == hashlib.sha256(
        runtime_path.read_bytes()
    ).hexdigest()
    assert artifact["leakage_contract"] == {
        "stores_generated_query_text": False,
        "stores_page_bodies": False,
        "stores_raw_provider_errors": False,
    }
    serialized = output_path.read_text(encoding="utf-8")
    assert "private provider detail" not in serialized
    assert "private reader detail" not in serialized
    assert "query_text" not in serialized
    assert "page_body" not in serialized


def test_protocol_runner_rejects_non_rq1c_runtime_artifact(tmp_path: Path) -> None:
    runtime_path = tmp_path / "runtime.json"
    runtime_path.write_text('{"schema_version":"wrong"}\n', encoding="utf-8")

    try:
        run_protocol_probes(
            runtime_path=runtime_path,
            output_path=tmp_path / "protocol.json",
        )
    except ValueError as exc:
        assert "require an RQ1-C runtime artifact" in str(exc)
    else:
        raise AssertionError("invalid runtime artifact must be rejected")

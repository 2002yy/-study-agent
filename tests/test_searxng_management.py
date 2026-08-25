from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "infra" / "searxng" / "compose.yml"
SETTINGS = ROOT / "infra" / "searxng" / "settings.yml"
MANAGER = ROOT / "tools" / "manage-searxng.ps1"


def test_compose_pins_image_and_loopback_without_public_stack():
    text = COMPOSE.read_text(encoding="utf-8")

    assert "searxng/searxng@sha256:" in text
    assert "searxng/searxng:latest" not in text
    assert '127.0.0.1:${SEARXNG_HOST_PORT:-8080}:8080' in text
    assert "SEARXNG_SECRET: ${SEARXNG_SECRET:?" in text
    assert "valkey" not in text.lower()
    assert "image-proxy" not in text.lower()


def test_settings_enable_json_but_keep_private_instance_features_off():
    text = SETTINGS.read_text(encoding="utf-8")

    assert "use_default_settings: true" in text
    assert "- json" in text
    assert "limiter: false" in text
    assert "public_instance: false" in text
    assert "image_proxy: false" in text
    assert "overridden-by-SEARXNG_SECRET" in text


def test_manager_has_candidate_backup_switch_and_guarded_retention_contract():
    text = MANAGER.read_text(encoding="utf-8")

    assert '18080' in text
    assert 'Copy-Item -LiteralPath $mount.Source -Destination $backupPath' in text
    assert 'Test-SearXNGSearch 18080' in text
    assert '@("rename", $ActiveContainerName, $retainedName)' in text
    assert 'Write-Warning "新 active 失败；旧容器已自动回滚到 8080"' in text
    assert 'TotalDays -lt 7' in text
    assert 'if (-not $ConfirmRemoval)' in text
    assert 'docker.io/searxng/searxng@sha256:' in text
    assert 'searxng/searxng:latest' not in text


def test_manager_never_rotates_existing_secret_or_opens_lan():
    text = MANAGER.read_text(encoding="utf-8")

    assert "脚本不会自动轮换已有 secret" in text
    assert '"http://127.0.0.1:$HostPort/"' in text
    assert 'ExpectedPort' in text
    assert 'HostIp -ne "127.0.0.1"' in text
    assert "0.0.0.0:$HostPort" not in text

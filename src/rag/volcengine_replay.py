from __future__ import annotations

import hashlib
import os

from src.rag.provider_replay import OpenAICompatibleReplayProvider

VOLCENGINE_ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"


class VolcengineArkReplayProvider(OpenAICompatibleReplayProvider):
    """Replay-only Ark adapter using the OpenAI-compatible Chat API.

    This deliberately does not register Volcengine in the production chat owner.
    P0-E3 must measure compatibility and quality before that wider surface is
    considered.
    """

    def __init__(
        self,
        *,
        model_profile: str = "pro",
        temperature: float = 0.0,
        max_tokens: int = 700,
        timeout: float = 60.0,
        api_key: str | None = None,
        base_url: str | None = None,
        model_name: str | None = None,
    ) -> None:
        from openai import OpenAI

        resolved_key = _first_value(
            api_key,
            os.getenv("VOLCENGINE_API_KEY"),
            os.getenv("ARK_API_KEY"),
        )
        resolved_base_url = _single_line(
            _first_value(
                base_url,
                os.getenv("VOLCENGINE_BASE_URL"),
                os.getenv("ARK_BASE_URL"),
                VOLCENGINE_ARK_BASE_URL,
            ),
            "Volcengine base URL",
        ).rstrip("/")
        profile = str(model_profile or "pro").strip().lower()
        if profile not in {"flash", "pro"}:
            raise RuntimeError(f"Unsupported model profile: {profile}")
        model_env_suffix = "MODEL_PRO_NAME" if profile == "pro" else "MODEL_FLASH_NAME"
        resolved_model = _single_line(
            _first_value(
                model_name,
                os.getenv(f"VOLCENGINE_{model_env_suffix}"),
                os.getenv(f"ARK_{model_env_suffix}"),
                os.getenv(model_env_suffix),
            ),
            "Volcengine model or endpoint ID",
        )
        if not resolved_key:
            raise RuntimeError("VOLCENGINE_API_KEY or ARK_API_KEY is missing.")

        self.provider_profile = "volcengine"
        self.model_profile = profile
        self.model_name = resolved_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.endpoint_fingerprint = hashlib.sha256(
            resolved_base_url.encode("utf-8")
        ).hexdigest()[:16]
        self._client = OpenAI(
            api_key=resolved_key,
            base_url=resolved_base_url,
            timeout=timeout,
            max_retries=2,
        )


def _first_value(*values: str | None) -> str:
    for value in values:
        normalized = str(value or "").strip()
        if normalized:
            return normalized
    return ""


def _single_line(value: str, label: str) -> str:
    if not value:
        raise RuntimeError(f"{label} is missing.")
    if "\n" in value or "\r" in value:
        raise RuntimeError(f"{label} must be a single line.")
    return value

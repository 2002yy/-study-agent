from __future__ import annotations

from src.application.runtime_repository import (
    get_learner_model_service,
    get_learning_resume_service,
)


def test_learning_resume_service_factory_exposes_cache_reset() -> None:
    assert callable(get_learning_resume_service.cache_clear)


def test_learner_model_service_factory_exposes_cache_reset() -> None:
    assert callable(get_learner_model_service.cache_clear)

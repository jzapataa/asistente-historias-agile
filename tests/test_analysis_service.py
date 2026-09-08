from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.domain.analysis import AnalysisDraft, EstimationReadiness, StoryInput
from src.providers.gemini import ProviderUnavailableError
from src.services.analysis_service import AnalysisService, AnalysisServiceError


class StubProvider:
    def __init__(self, draft: AnalysisDraft) -> None:
        self.draft = draft

    def analyze(self, story: StoryInput) -> AnalysisDraft:
        return self.draft


class FailingProvider:
    def analyze(self, story: StoryInput) -> AnalysisDraft:
        raise ProviderUnavailableError()


def test_story_input_requires_meaningful_description() -> None:
    with pytest.raises(ValidationError):
        StoryInput(description="demasiado corta")


def test_story_input_rejects_description_over_limit() -> None:
    with pytest.raises(ValidationError):
        StoryInput(description="x" * 12_001)


def test_service_returns_policy_checked_result(story, ready_draft) -> None:
    service = AnalysisService(StubProvider(ready_draft))

    result = service.analyze(story)

    assert result.estimation_readiness is EstimationReadiness.READY
    assert result.estimate is not None


def test_service_hides_provider_details_from_caller(story) -> None:
    service = AnalysisService(FailingProvider())

    with pytest.raises(AnalysisServiceError) as exc_info:
        service.analyze(story)

    assert "Gemini no está disponible" in exc_info.value.user_message

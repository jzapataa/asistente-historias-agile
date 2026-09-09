"""Application service coordinating provider output and domain policy."""

from __future__ import annotations

from typing import Protocol

from src.domain.analysis import AnalysisDraft, AnalysisResult, StoryInput
from src.domain.estimation import apply_estimation_policy
from src.providers.gemini import ProviderError


class AnalysisProvider(Protocol):
    def analyze(self, story: StoryInput) -> AnalysisDraft: ...


class AnalysisServiceError(RuntimeError):
    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


class AnalysisService:
    def __init__(self, provider: AnalysisProvider) -> None:
        self._provider = provider

    def analyze(self, story: StoryInput) -> AnalysisResult:
        try:
            draft = self._provider.analyze(story)
        except ProviderError as exc:
            raise AnalysisServiceError(exc.user_message) from None

        return apply_estimation_policy(draft)

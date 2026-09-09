"""Deterministic estimation policy applied after the LLM response."""

from __future__ import annotations

from src.domain.analysis import (
    AnalysisDraft,
    AnalysisResult,
    Confidence,
    EstimationReadiness,
)


def apply_estimation_policy(draft: AnalysisDraft) -> AnalysisResult:
    """Enforce estimation safety independently from the model's raw output.

    Rules:
    - Any blocking gap forces NOT_READY and removes hours.
    - A model-declared NOT_READY always removes hours.
    - Missing estimate data cannot be promoted to an estimable state.
    - Non-blocking assumptions, missing information, or LOW confidence downgrade
      READY to READY_WITH_RESERVATIONS instead of suppressing an otherwise valid range.
    - READY_WITH_RESERVATIONS is always normalized to MEDIUM confidence.
    - READY can only survive with HIGH or MEDIUM confidence and no non-blocking
      uncertainty that requires reservations.
    """

    data = draft.model_dump()

    if (
        draft.blocking_gaps
        or draft.estimation_readiness is EstimationReadiness.NOT_READY
        or draft.estimate is None
    ):
        data["estimation_readiness"] = EstimationReadiness.NOT_READY
        data["estimate"] = None
        data["confidence"] = Confidence.LOW
        return AnalysisResult.model_validate(data)

    if draft.estimation_readiness is EstimationReadiness.READY and (
        draft.assumptions
        or draft.missing_information
        or draft.confidence is Confidence.LOW
    ):
        data["estimation_readiness"] = EstimationReadiness.READY_WITH_RESERVATIONS

    if data["estimation_readiness"] is EstimationReadiness.READY_WITH_RESERVATIONS:
        data["confidence"] = Confidence.MEDIUM

    return AnalysisResult.model_validate(data)

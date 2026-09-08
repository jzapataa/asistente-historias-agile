"""Deterministic estimation policy applied after the LLM response."""

from __future__ import annotations

from src.domain.analysis import (
    AnalysisDraft,
    AnalysisResult,
    Confidence,
    EstimationReadiness,
)


def apply_estimation_policy(draft: AnalysisDraft) -> AnalysisResult:
    """Enforce safety rules independently from the model's requested output.

    Rules:
    - Any blocking gap forces NOT_READY and removes hours.
    - A model-declared NOT_READY always removes hours.
    - Missing estimate data cannot be promoted to a ready state.
    - Non-blocking assumptions or missing information downgrade READY to
      READY_WITH_RESERVATIONS.
    - READY_WITH_RESERVATIONS cannot keep HIGH confidence.
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
        draft.assumptions or draft.missing_information
    ):
        data["estimation_readiness"] = EstimationReadiness.READY_WITH_RESERVATIONS

    if (
        data["estimation_readiness"] is EstimationReadiness.READY_WITH_RESERVATIONS
        and data["confidence"] is Confidence.HIGH
    ):
        data["confidence"] = Confidence.MEDIUM

    return AnalysisResult.model_validate(data)

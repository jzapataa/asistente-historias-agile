from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.domain.analysis import (
    AnalysisDraft,
    Confidence,
    EstimateRange,
    EstimationReadiness,
)
from src.domain.estimation import apply_estimation_policy


def test_not_ready_never_exposes_hours(ready_draft: AnalysisDraft) -> None:
    unsafe = ready_draft.model_copy(
        update={"estimation_readiness": EstimationReadiness.NOT_READY}
    )

    result = apply_estimation_policy(unsafe)

    assert result.estimation_readiness is EstimationReadiness.NOT_READY
    assert result.estimate is None
    assert result.confidence is Confidence.LOW


def test_blocking_gap_forces_not_ready(ready_draft: AnalysisDraft) -> None:
    unsafe = ready_draft.model_copy(
        update={"blocking_gaps": ["No se conoce quién puede exportar datos."]}
    )

    result = apply_estimation_policy(unsafe)

    assert result.estimation_readiness is EstimationReadiness.NOT_READY
    assert result.estimate is None


def test_missing_estimate_forces_not_ready(ready_draft: AnalysisDraft) -> None:
    unsafe = ready_draft.model_copy(update={"estimate": None})

    result = apply_estimation_policy(unsafe)

    assert result.estimation_readiness is EstimationReadiness.NOT_READY
    assert result.estimate is None


def test_low_confidence_ready_forces_not_ready(ready_draft: AnalysisDraft) -> None:
    unsafe = ready_draft.model_copy(update={"confidence": Confidence.LOW})

    result = apply_estimation_policy(unsafe)

    assert result.estimation_readiness is EstimationReadiness.NOT_READY
    assert result.estimate is None
    assert result.confidence is Confidence.LOW


def test_low_confidence_reservations_force_not_ready(ready_draft: AnalysisDraft) -> None:
    unsafe = ready_draft.model_copy(
        update={
            "estimation_readiness": EstimationReadiness.READY_WITH_RESERVATIONS,
            "confidence": Confidence.LOW,
            "assumptions": ["El volumen será moderado."],
        }
    )

    result = apply_estimation_policy(unsafe)

    assert result.estimation_readiness is EstimationReadiness.NOT_READY
    assert result.estimate is None
    assert result.confidence is Confidence.LOW


def test_assumptions_downgrade_ready_to_reservations(ready_draft: AnalysisDraft) -> None:
    draft = ready_draft.model_copy(
        update={
            "assumptions": ["Se reutiliza el sistema de permisos actual."],
            "confidence": Confidence.HIGH,
        }
    )

    result = apply_estimation_policy(draft)

    assert result.estimation_readiness is EstimationReadiness.READY_WITH_RESERVATIONS
    assert result.estimate is not None
    assert result.confidence is Confidence.MEDIUM


def test_estimate_range_requires_monotonic_hours() -> None:
    with pytest.raises(ValidationError):
        EstimateRange(
            optimistic_hours=10,
            realistic_hours=8,
            pessimistic_hours=20,
        )


def test_ready_with_reservations_cannot_keep_high_confidence(ready_draft) -> None:
    draft = ready_draft.model_copy(
        update={
            "estimation_readiness": EstimationReadiness.READY_WITH_RESERVATIONS,
            "confidence": Confidence.HIGH,
            "assumptions": ["El volumen será moderado."],
        }
    )

    result = apply_estimation_policy(draft)

    assert result.estimation_readiness is EstimationReadiness.READY_WITH_RESERVATIONS
    assert result.confidence is Confidence.MEDIUM

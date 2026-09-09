from __future__ import annotations

import pytest

from src.domain.analysis import (
    AnalysisDraft,
    Confidence,
    EstimateRange,
    EstimationReadiness,
    StoryInput,
)


@pytest.fixture
def story() -> StoryInput:
    return StoryInput(
        title="Exportar solicitudes",
        description="Como gestor quiero exportar el listado de solicitudes a Excel.",
        acceptance_criteria="Respeta filtros y permisos del usuario.",
        technical_context="Spring Boot, Angular y PostgreSQL.",
    )


@pytest.fixture
def ready_draft() -> AnalysisDraft:
    return AnalysisDraft(
        summary="Permitir exportar las solicitudes visibles.",
        real_request="Añadir una exportación respetando filtros y permisos.",
        impacted_areas=["Frontend", "Backend"],
        provided_facts=["La exportación debe respetar filtros."],
        inferred_points=[],
        assumptions=[],
        missing_information=[],
        blocking_gaps=[],
        functional_questions=[],
        technical_questions=[],
        data_questions=[],
        integration_questions=[],
        risks=["Volumen de datos desconocido."],
        technical_breakdown=["Crear endpoint de exportación.", "Añadir acción en UI."],
        estimation_readiness=EstimationReadiness.READY,
        estimate=EstimateRange(
            optimistic_hours=6,
            realistic_hours=10,
            pessimistic_hours=16,
        ),
        confidence=Confidence.MEDIUM,
        recommendation="Validar el rango con el equipo durante refinement.",
    )

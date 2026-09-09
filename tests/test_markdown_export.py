from __future__ import annotations

from src.domain.estimation import apply_estimation_policy
from src.presentation.markdown import build_analysis_markdown, build_export_filename


def test_markdown_export_contains_core_sections(story, ready_draft) -> None:
    result = apply_estimation_policy(ready_draft)

    report = build_analysis_markdown(story, result)

    assert "# Análisis de historia de Jira" in report
    assert "**Estimation readiness:** READY" in report
    assert "## Dudas para refinement" in report
    assert "- Realista: 10 h" in report
    assert result.recommendation in report


def test_markdown_export_hides_hours_when_not_ready(story, ready_draft) -> None:
    draft = ready_draft.model_copy(
        update={"blocking_gaps": ["No se conoce el formato de salida requerido."]}
    )
    result = apply_estimation_policy(draft)

    report = build_analysis_markdown(story, result)

    assert "**Estimation readiness:** NOT_READY" in report
    assert "No se muestran horas" in report
    assert "Realista:" not in report


def test_export_filename_is_safe_and_readable() -> None:
    assert build_export_filename("Exportación: Solicitudes / Gestión") == (
        "exportacion-solicitudes-gestion-analysis.md"
    )
    assert build_export_filename(None) == "jira-story-analysis.md"

"""Markdown export helpers for the Streamlit presentation layer."""

from __future__ import annotations

import re
import unicodedata

from src.domain.analysis import AnalysisResult, StoryInput


def build_analysis_markdown(story: StoryInput, result: AnalysisResult) -> str:
    """Build a portable Markdown report for Jira, Confluence or team chat."""

    lines: list[str] = [
        "# Análisis de historia de Jira",
        "",
        f"**Título:** {story.title or 'Sin título informado'}",
        f"**Tipo:** {story.task_type.value}",
        f"**Estimation readiness:** {result.estimation_readiness.value}",
        f"**Confianza:** {result.confidence.value}",
        "",
        "> La IA ayuda a preparar una estimación; no sustituye el criterio del equipo.",
        "",
        "## Resumen",
        result.summary,
        "",
        "## Lo que se pide realmente",
        result.real_request,
        "",
        "## Áreas impactadas",
    ]
    lines.extend(_markdown_list(result.impacted_areas))

    _append_section(lines, "Hechos proporcionados", result.provided_facts)
    _append_section(lines, "Inferencias", result.inferred_points)
    _append_section(lines, "Supuestos", result.assumptions)
    _append_section(lines, "Información faltante", result.missing_information)
    _append_section(lines, "Gaps bloqueantes", result.blocking_gaps)

    lines.extend(["", "## Dudas para refinement"])
    _append_subsection(lines, "Funcionales", result.functional_questions)
    _append_subsection(lines, "Técnicas", result.technical_questions)
    _append_subsection(lines, "Datos", result.data_questions)
    _append_subsection(lines, "Integraciones", result.integration_questions)

    _append_section(lines, "Riesgos", result.risks)
    _append_section(lines, "Desglose técnico preliminar", result.technical_breakdown)

    lines.extend(["", "## Estimación preliminar"])
    if result.estimate is None:
        lines.append(
            "No se muestran horas porque la historia todavía no es suficientemente estimable."
        )
    else:
        lines.extend(
            [
                f"- Optimista: {result.estimate.optimistic_hours:g} h",
                f"- Realista: {result.estimate.realistic_hours:g} h",
                f"- Pesimista: {result.estimate.pessimistic_hours:g} h",
                f"- Confianza: {result.confidence.value}",
            ]
        )

    lines.extend(["", "## Recomendación", result.recommendation, ""])
    return "\n".join(lines)


def build_export_filename(title: str | None) -> str:
    """Create a safe, predictable filename without external slugify dependencies."""

    if not title:
        return "jira-story-analysis.md"

    normalized = unicodedata.normalize("NFKD", title)
    ascii_title = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title).strip("-")[:60]
    return f"{slug or 'jira-story'}-analysis.md"


def _markdown_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- Sin elementos relevantes."]


def _append_section(lines: list[str], title: str, items: list[str]) -> None:
    lines.extend(["", f"## {title}"])
    lines.extend(_markdown_list(items))


def _append_subsection(lines: list[str], title: str, items: list[str]) -> None:
    lines.extend(["", f"### {title}"])
    lines.extend(_markdown_list(items))

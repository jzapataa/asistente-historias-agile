"""Streamlit entry point for Jira Story Analyzer V1 core."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError
import streamlit as st

from src.config import ConfigurationError, Settings
from src.domain.analysis import AnalysisResult, EstimationReadiness, StoryInput, TaskType
from src.providers.gemini import GeminiProvider
from src.services.analysis_service import AnalysisService, AnalysisServiceError


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


st.set_page_config(
    page_title="Jira Story Analyzer",
    page_icon="🧠",
    layout="wide",
)


@st.cache_resource
def build_service(api_key: str, model_name: str, timeout_seconds: int) -> AnalysisService:
    provider = GeminiProvider(
        api_key=api_key,
        model_name=model_name,
        timeout_seconds=timeout_seconds,
    )
    return AnalysisService(provider)


def read_streamlit_secrets() -> dict[str, Any]:
    """Read Streamlit secrets without requiring a secrets.toml file locally."""

    try:
        return dict(st.secrets)
    except Exception as exc:
        logger.info("Streamlit secrets not available type=%s", type(exc).__name__)
        return {}


def render_analysis(result: AnalysisResult) -> None:
    st.subheader("Análisis")

    readiness_labels = {
        EstimationReadiness.READY: "✅ READY",
        EstimationReadiness.READY_WITH_RESERVATIONS: "⚠️ READY WITH RESERVATIONS",
        EstimationReadiness.NOT_READY: "⛔ NOT READY",
    }
    st.markdown(f"### {readiness_labels[result.estimation_readiness]}")
    st.caption(
        "La estimación es orientativa y debe validarse con el equipo antes de comprometer esfuerzo."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Resumen")
        st.write(result.summary)
    with col2:
        st.markdown("#### Lo que se pide realmente")
        st.write(result.real_request)

    st.markdown("#### Áreas impactadas")
    st.write(", ".join(result.impacted_areas) if result.impacted_areas else "No identificadas")

    context_col1, context_col2 = st.columns(2)
    with context_col1:
        _render_list("Hechos proporcionados", result.provided_facts)
        _render_list("Inferencias", result.inferred_points)
    with context_col2:
        _render_list("Supuestos", result.assumptions)
        _render_list("Información faltante", result.missing_information)

    _render_list("Gaps bloqueantes", result.blocking_gaps)

    st.markdown("#### Dudas para refinement")
    q1, q2 = st.columns(2)
    with q1:
        _render_list("Funcionales", result.functional_questions)
        _render_list("Datos", result.data_questions)
    with q2:
        _render_list("Técnicas", result.technical_questions)
        _render_list("Integraciones", result.integration_questions)

    _render_list("Riesgos", result.risks)
    _render_list("Desglose técnico preliminar", result.technical_breakdown)

    st.markdown("#### Estimación preliminar")
    if result.estimate is None:
        st.info(
            "No se muestran horas porque la historia todavía no es suficientemente estimable."
        )
    else:
        e1, e2, e3 = st.columns(3)
        e1.metric("Optimista", f"{result.estimate.optimistic_hours:g} h")
        e2.metric("Realista", f"{result.estimate.realistic_hours:g} h")
        e3.metric("Pesimista", f"{result.estimate.pessimistic_hours:g} h")
        st.caption(f"Confianza de la estimación: {result.confidence.value}")

    st.markdown("#### Recomendación")
    st.write(result.recommendation)


def _render_list(title: str, items: list[str]) -> None:
    st.markdown(f"**{title}**")
    if not items:
        st.caption("Sin elementos relevantes.")
        return
    for item in items:
        st.markdown(f"- {item}")


st.title("🧠 Jira Story Analyzer")
st.write(
    "Analiza una historia antes del refinement: alcance, gaps, riesgos, desglose técnico "
    "y si existe suficiente información para estimarla."
)
st.caption(
    "Privacidad: el contenido se envía a Gemini para generar el análisis y esta aplicación "
    "no lo persiste en una base de datos."
)

try:
    settings = Settings.from_sources(read_streamlit_secrets())
except ConfigurationError as exc:
    st.error(str(exc))
    st.stop()

service = build_service(
    settings.api_key,
    settings.model_name,
    settings.request_timeout_seconds,
)

with st.form("jira_story_form"):
    st.subheader("Datos de la historia")

    title = st.text_input(
        "Título (opcional)",
        max_chars=250,
        placeholder="Ej: Exportar listado de solicitudes a Excel",
    )
    description = st.text_area(
        "Descripción",
        height=180,
        max_chars=12_000,
        placeholder=(
            "Ej: Como gestor quiero exportar el listado de solicitudes para revisarlas offline..."
        ),
    )
    acceptance_criteria = st.text_area(
        "Criterios de aceptación (opcional)",
        height=120,
        max_chars=8_000,
        placeholder="Ej: Respeta filtros, exporta columnas visibles, exige perfil autorizado...",
    )
    technical_context = st.text_area(
        "Contexto técnico (opcional)",
        height=100,
        max_chars=6_000,
        placeholder="Ej: Java 21, Spring Boot, Angular, PostgreSQL, REST...",
    )
    task_type = st.selectbox("Tipo de tarea", [item.value for item in TaskType])

    submitted = st.form_submit_button("Analizar historia", type="primary")

if submitted:
    try:
        story = StoryInput(
            title=title,
            description=description,
            acceptance_criteria=acceptance_criteria,
            technical_context=technical_context,
            task_type=task_type,
        )
    except ValidationError:
        st.warning(
            "Revisa los datos de entrada. La descripción es obligatoria y debe tener "
            "al menos 20 caracteres."
        )
    else:
        try:
            with st.spinner("Analizando historia..."):
                result = service.analyze(story)
        except AnalysisServiceError as exc:
            st.error(exc.user_message)
        except Exception as exc:
            logger.error("Unexpected analysis error type=%s", type(exc).__name__)
            st.error("Ha ocurrido un error inesperado al analizar la historia.")
        else:
            render_analysis(result)

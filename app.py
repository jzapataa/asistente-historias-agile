"""Streamlit entry point for Jira Story Analyzer."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError
import streamlit as st

from src.config import ConfigurationError, Settings
from src.domain.analysis import AnalysisResult, Confidence, EstimationReadiness, StoryInput, TaskType
from src.presentation.markdown import build_analysis_markdown, build_export_filename
from src.providers.gemini import GeminiProvider
from src.services.analysis_service import AnalysisService, AnalysisServiceError


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Jira Story Analyzer", page_icon="🧠", layout="wide")

st.markdown(
    """
    <style>
    .block-container {max-width: 1120px; padding-top: 2.2rem; padding-bottom: 4rem;}
    .hero {padding: 1.4rem 1.5rem; border: 1px solid rgba(128,128,128,.22); border-radius: 16px; margin-bottom: 1rem;}
    .hero-kicker {font-size: .82rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; opacity: .68;}
    .hero h1 {margin: .25rem 0 .4rem 0; font-size: 2.25rem;}
    .hero p {margin: 0; font-size: 1.03rem; opacity: .8;}
    </style>
    """,
    unsafe_allow_html=True,
)

EXAMPLE_STORY = {
    "story_title": "Exportar listado de solicitudes a Excel",
    "story_description": (
        "Como gestor quiero exportar a Excel el listado de solicitudes que estoy viendo "
        "para poder revisarlo y compartirlo fuera de la aplicación."
    ),
    "story_acceptance_criteria": (
        "La exportación debe respetar los filtros activos, incluir las columnas visibles "
        "y estar disponible únicamente para usuarios con permiso de gestión."
    ),
    "story_technical_context": "Frontend Angular, backend Spring Boot y API REST existente.",
    "story_task_type": TaskType.NEW_FEATURE.value,
}

FORM_DEFAULTS = {
    "story_title": "",
    "story_description": "",
    "story_acceptance_criteria": "",
    "story_technical_context": "",
    "story_task_type": TaskType.UNKNOWN.value,
}


@st.cache_resource
def build_service(api_key: str, model_name: str, timeout_seconds: int) -> AnalysisService:
    return AnalysisService(
        GeminiProvider(api_key=api_key, model_name=model_name, timeout_seconds=timeout_seconds)
    )


def read_streamlit_secrets() -> dict[str, Any]:
    try:
        return dict(st.secrets)
    except Exception as exc:
        logger.info("Streamlit secrets not available type=%s", type(exc).__name__)
        return {}


def initialise_state() -> None:
    for key, value in FORM_DEFAULTS.items():
        st.session_state.setdefault(key, value)


def load_example() -> None:
    st.session_state.update(EXAMPLE_STORY)
    st.session_state.pop("last_analysis", None)
    st.session_state.pop("last_story", None)


def clear_workspace() -> None:
    st.session_state.update(FORM_DEFAULTS)
    st.session_state.pop("last_analysis", None)
    st.session_state.pop("last_story", None)


def render_list(title: str, items: list[str], *, empty: str = "Sin elementos relevantes.") -> None:
    st.markdown(f"**{title}**")
    if not items:
        st.caption(empty)
        return
    for item in items:
        st.markdown(f"- {item}")


def render_readiness(result: AnalysisResult) -> None:
    views = {
        EstimationReadiness.READY: (
            "Lista para estimar",
            "La historia tiene definición suficiente para discutir un rango preliminar con el equipo.",
            "green",
            ":material/check_circle:",
        ),
        EstimationReadiness.READY_WITH_RESERVATIONS: (
            "Estimable con reservas",
            "Existe un rango defendible, pero hay supuestos o información pendiente que puede moverlo.",
            "orange",
            ":material/warning:",
        ),
        EstimationReadiness.NOT_READY: (
            "No estimable todavía",
            "Falta información que puede cambiar materialmente el alcance o el esfuerzo. No se muestran horas.",
            "red",
            ":material/block:",
        ),
    }
    label, explanation, color, icon = views[result.estimation_readiness]
    with st.container(border=True):
        st.badge(label, icon=icon, color=color)
        st.markdown(f"### {label}")
        st.write(explanation)
        st.caption("La IA prepara la estimación; la decisión final sigue siendo del equipo.")


def render_analysis(story: StoryInput, result: AnalysisResult) -> None:
    st.divider()
    st.markdown("## Resultado del análisis")
    st.caption(f"Último análisis: {story.title or 'Historia sin título'}")

    render_readiness(result)

    summary_col, request_col = st.columns(2, gap="large")
    with summary_col:
        with st.container(border=True):
            st.markdown("#### Resumen")
            st.write(result.summary)
    with request_col:
        with st.container(border=True):
            st.markdown("#### Lo que se pide realmente")
            st.write(result.real_request)

    if result.impacted_areas:
        st.markdown("**Áreas impactadas**")
        with st.container(horizontal=True, wrap=True):
            for area in result.impacted_areas:
                st.badge(area, color="gray")

    overview_tab, questions_tab, plan_tab, estimate_tab = st.tabs(
        ["Contexto", "Dudas y riesgos", "Plan técnico", "Estimación"]
    )

    with overview_tab:
        c1, c2 = st.columns(2, gap="large")
        with c1:
            render_list("Hechos proporcionados", result.provided_facts)
            render_list("Inferencias", result.inferred_points)
        with c2:
            render_list("Supuestos", result.assumptions)
            render_list("Información faltante", result.missing_information)

    with questions_tab:
        if result.blocking_gaps:
            st.error("Hay gaps bloqueantes que conviene resolver antes de cerrar una estimación.")
            render_list("Gaps bloqueantes", result.blocking_gaps)
        q1, q2 = st.columns(2, gap="large")
        with q1:
            render_list("Dudas funcionales", result.functional_questions)
            render_list("Dudas sobre datos", result.data_questions)
        with q2:
            render_list("Dudas técnicas", result.technical_questions)
            render_list("Dudas de integraciones", result.integration_questions)
        st.markdown("---")
        render_list("Riesgos", result.risks)

    with plan_tab:
        render_list("Desglose técnico preliminar", result.technical_breakdown)
        st.info(result.recommendation)

    with estimate_tab:
        if result.estimate is None:
            st.info("No se muestran horas hasta resolver los gaps que impiden defender un rango.")
        else:
            e1, e2, e3 = st.columns(3)
            e1.metric("Optimista", f"{result.estimate.optimistic_hours:g} h")
            e2.metric("Realista", f"{result.estimate.realistic_hours:g} h")
            e3.metric("Pesimista", f"{result.estimate.pessimistic_hours:g} h")
            confidence_color = {
                Confidence.HIGH: "green",
                Confidence.MEDIUM: "orange",
                Confidence.LOW: "red",
            }[result.confidence]
            st.badge(f"Confianza {result.confidence.value}", color=confidence_color)
            st.caption("Rango orientativo para refinement; no es un compromiso de entrega.")

    markdown_report = build_analysis_markdown(story, result)
    st.markdown("### Compartir resultado")
    action_col, info_col = st.columns([1, 2], gap="large")
    with action_col:
        st.download_button(
            "Descargar Markdown",
            data=markdown_report,
            file_name=build_export_filename(story.title),
            mime="text/markdown",
            icon=":material/download:",
            on_click="ignore",
            width="stretch",
        )
    with info_col:
        st.caption("El Markdown está preparado para pegarlo en Jira, Confluence o un chat de equipo.")
    with st.expander("Ver Markdown para copiar"):
        st.code(markdown_report, language="markdown")


initialise_state()

st.markdown(
    """
    <div class="hero">
      <div class="hero-kicker">AI · SOFTWARE DELIVERY</div>
      <h1>🧠 Jira Story Analyzer</h1>
      <p>Convierte una historia en alcance, dudas, riesgos y un criterio explícito sobre si ya se puede estimar.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

value_cols = st.columns(3)
value_cols[0].markdown("**1. Entiende el alcance**")
value_cols[0].caption("Qué se pide realmente y qué áreas puede tocar.")
value_cols[1].markdown("**2. Encuentra los gaps**")
value_cols[1].caption("Dudas y riesgos que pueden cambiar el esfuerzo.")
value_cols[2].markdown("**3. Decide si estimar**")
value_cols[2].caption("READY, reservas o NOT_READY antes de enseñar horas.")

try:
    settings = Settings.from_sources(read_streamlit_secrets())
except ConfigurationError as exc:
    st.error(str(exc))
    st.stop()

service = build_service(settings.api_key, settings.model_name, settings.request_timeout_seconds)

st.markdown("## Analiza una historia")
st.caption("Pega la información que ya tengas. No hace falta completar campos que todavía no conoces.")
button_col, clear_col, spacer = st.columns([1, 1, 3])
button_col.button("Usar ejemplo", icon=":material/lightbulb:", on_click=load_example, key="load_example")
clear_col.button("Limpiar", icon=":material/delete:", on_click=clear_workspace, key="clear_workspace")

with st.form("jira_story_form", border=True):
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.text_input(
            "Título (opcional)",
            key="story_title",
            max_chars=250,
            placeholder="Ej: Exportar listado de solicitudes a Excel",
        )
        st.text_area(
            "Descripción",
            key="story_description",
            height=190,
            max_chars=12_000,
            placeholder="Qué necesita el usuario y para qué...",
        )
        st.text_area(
            "Criterios de aceptación (opcional)",
            key="story_acceptance_criteria",
            height=130,
            max_chars=8_000,
            placeholder="Comportamiento esperado, permisos, filtros, validaciones...",
        )
    with right:
        task_values = [item.value for item in TaskType]
        st.selectbox("Tipo de tarea", task_values, key="story_task_type")
        st.text_area(
            "Contexto técnico (opcional)",
            key="story_technical_context",
            height=160,
            max_chars=6_000,
            placeholder="Stack, servicios implicados, restricciones conocidas...",
        )
        st.caption("Consejo: informa solo de lo que sabes. Los huecos también son parte del análisis.")

    submitted = st.form_submit_button(
        "Analizar historia",
        type="primary",
        icon=":material/auto_awesome:",
        width="stretch",
    )

if submitted:
    try:
        story = StoryInput(
            title=st.session_state.story_title,
            description=st.session_state.story_description,
            acceptance_criteria=st.session_state.story_acceptance_criteria,
            technical_context=st.session_state.story_technical_context,
            task_type=st.session_state.story_task_type,
        )
    except ValidationError:
        st.warning("La descripción es obligatoria y debe tener al menos 20 caracteres.")
    else:
        try:
            with st.spinner("Analizando alcance, gaps y estimabilidad..."):
                result = service.analyze(story)
        except AnalysisServiceError as exc:
            st.error(exc.user_message)
        except Exception as exc:
            logger.error("Unexpected analysis error type=%s", type(exc).__name__)
            st.error("Ha ocurrido un error inesperado al analizar la historia.")
        else:
            st.session_state.last_story = story.model_dump(mode="json")
            st.session_state.last_analysis = result.model_dump(mode="json")

if "last_story" in st.session_state and "last_analysis" in st.session_state:
    render_analysis(
        StoryInput.model_validate(st.session_state.last_story),
        AnalysisResult.model_validate(st.session_state.last_analysis),
    )

st.divider()
with st.expander("Privacidad y límites"):
    st.markdown(
        "- El contenido se envía a Gemini para generar el análisis.\n"
        "- La aplicación no guarda las historias en una base de datos.\n"
        "- El último resultado vive únicamente en la sesión actual de Streamlit.\n"
        "- Las estimaciones son orientativas y deben validarse con el equipo."
    )

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
import streamlit as st

# =========================
# Configuración de página
# =========================

st.set_page_config(
    page_title="Asistente de Historias de Jira",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 Asistente de Historias de Jira")
st.markdown(
    "Pega una historia de Jira y te ayudaré a analizarla: resumen, dudas, riesgos, "
    "desglose técnico y estimación preliminar."
)

# =========================
# Sidebar
# =========================

with st.sidebar:
    st.header("Configuración")

    temperature = st.slider(
        "Temperatura",
        min_value=0.0,
        max_value=1.0,
        value=0.2,
        step=0.1,
        help="Para análisis técnico y estimaciones conviene usar valores bajos."
    )

    model_name = st.selectbox(
        "Modelo",
        ["gemini-2.5-flash-lite", "gemini-2.5-flash"]
    )

    st.divider()

    st.markdown("### Modo de análisis")
    modo = st.selectbox(
        "Tipo de respuesta",
        [
            "Análisis completo",
            "Solo dudas",
            "Solo desglose técnico",
            "Estimación preliminar"
        ]
    )

# =========================
# Modelo
# =========================

chat_model = ChatGoogleGenerativeAI(
    model=model_name,
    temperature=temperature
)

# =========================
# Prompt
# =========================

prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
Eres un asistente experto en análisis de historias de Jira para equipos de desarrollo software.

Tu objetivo NO es conversar como un chatbot.
Tu objetivo es ayudar a un jefe de proyecto técnico a entender mejor una historia de Jira.

Debes analizar la historia de forma práctica, clara y profesional.

Reglas:
- No inventes información.
- Si faltan datos, indica claramente qué falta.
- No des una estimación cerrada si hay incertidumbre.
- Usa rangos: optimista, realista y pesimista.
- Ten en cuenta backend, frontend, BBDD, integraciones, QA, despliegue y documentación.
- Prioriza dudas que puedan afectar al alcance o a la estimación.
- Escribe en español.
- Sé directo y útil.

Formato de respuesta:

## 1. Resumen de la historia
Explica brevemente qué se está pidiendo.

## 2. Lo que se pide realmente
Traduce la historia a lenguaje funcional/técnico.

## 3. Áreas posiblemente impactadas
Lista las áreas afectadas:
- Backend
- Frontend
- Base de datos
- Integraciones
- Seguridad/permisos
- QA
- Despliegue
- Documentación

## 4. Dudas antes de estimar
Separa las dudas en:
- Funcionales
- Técnicas
- Datos/BBDD
- Integraciones
- QA/validación

## 5. Riesgos detectados
Indica riesgos que podrían aumentar el esfuerzo.

## 6. Desglose técnico preliminar
Divide el trabajo en tareas técnicas concretas.

## 7. Estimación preliminar
Da una estimación en horas:
- Optimista
- Realista
- Pesimista

Incluye también:
- Confianza: alta, media o baja.
- Motivo de la confianza.

## 8. Recomendación
Di qué debería aclararse antes de cerrar la estimación.
"""
        ),
        (
            "human",
            """
Analiza la siguiente historia de Jira.

Modo de análisis solicitado:
{modo}

Título:
{titulo}

Descripción:
{descripcion}

Criterios de aceptación:
{criterios_aceptacion}

Contexto técnico:
{contexto_tecnico}

Tipo de tarea:
{tipo_tarea}

¿Toca frontend?
{toca_frontend}

¿Toca backend?
{toca_backend}

¿Toca base de datos?
{toca_bbdd}

¿Toca servicios externos?
{toca_servicios_externos}

Nivel de incertidumbre percibido:
{incertidumbre}
"""
        )
    ]
)

cadena = prompt_template | chat_model

# =========================
# Estado de sesión
# =========================

if "analisis_realizados" not in st.session_state:
    st.session_state.analisis_realizados = []

# =========================
# Formulario principal
# =========================

with st.form("formulario_historia_jira"):
    st.subheader("📌 Datos de la historia")

    titulo = st.text_input(
        "Título de la historia",
        placeholder="Ej: Exportar listado de solicitudes a Excel"
    )

    descripcion = st.text_area(
        "Descripción de la historia",
        height=180,
        placeholder="Ej: Como gestor quiero exportar el listado de solicitudes para revisarlas offline..."
    )

    criterios_aceptacion = st.text_area(
        "Criterios de aceptación",
        height=120,
        placeholder="Ej: Debe exportar las columnas visibles, respetar filtros, solo perfiles autorizados..."
    )

    col1, col2 = st.columns(2)

    with col1:
        tipo_tarea = st.selectbox(
            "Tipo de tarea",
            [
                "Nueva funcionalidad",
                "Evolutivo",
                "Corrección de bug",
                "Mejora técnica",
                "Integración",
                "Refactor",
                "No lo sé"
            ]
        )

        incertidumbre = st.selectbox(
            "Nivel de incertidumbre",
            ["Baja", "Media", "Alta", "No lo sé"]
        )

    with col2:
        toca_frontend = st.selectbox("¿Toca frontend?", ["Sí", "No", "No lo sé"])
        toca_backend = st.selectbox("¿Toca backend?", ["Sí", "No", "No lo sé"])
        toca_bbdd = st.selectbox("¿Toca base de datos?", ["Sí", "No", "No lo sé"])
        toca_servicios_externos = st.selectbox("¿Toca servicios externos?", ["Sí", "No", "No lo sé"])

    contexto_tecnico = st.text_area(
        "Contexto técnico",
        height=100,
        value="Java / Spring Boot, Angular, Oracle, WebLogic",
        placeholder="Ej: Java 17, Spring Boot, Angular, Oracle, servicios REST..."
    )

    analizar = st.form_submit_button("Analizar historia")

# =========================
# Análisis
# =========================

if analizar:
    if not descripcion.strip():
        st.warning("Mete al menos una descripción de la historia para poder analizarla.")
    else:
        st.subheader("🧠 Análisis generado")

        try:
            response_placeholder = st.empty()
            full_response = ""

            datos_historia = {
                "modo": modo,
                "titulo": titulo if titulo.strip() else "Sin título informado",
                "descripcion": descripcion,
                "criterios_aceptacion": criterios_aceptacion if criterios_aceptacion.strip() else "No informados",
                "contexto_tecnico": contexto_tecnico if contexto_tecnico.strip() else "No informado",
                "tipo_tarea": tipo_tarea,
                "toca_frontend": toca_frontend,
                "toca_backend": toca_backend,
                "toca_bbdd": toca_bbdd,
                "toca_servicios_externos": toca_servicios_externos,
                "incertidumbre": incertidumbre
            }

            for chunk in cadena.stream(datos_historia):
                contenido = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
                full_response += contenido
                response_placeholder.markdown(full_response + "▌")

            response_placeholder.markdown(full_response)

            st.session_state.analisis_realizados.insert(
                0,
                {
                    "titulo": datos_historia["titulo"],
                    "descripcion": descripcion,
                    "analisis": full_response
                }
            )

        except Exception as e:
            st.error(f"Error al generar el análisis: {str(e)}")
            st.info(
                "Revisa que tengas configurada correctamente la variable de entorno GOOGLE_API_KEY "
                "y que el modelo seleccionado esté disponible."
            )

# =========================
# Historial de análisis
# =========================

if st.session_state.analisis_realizados:
    st.divider()
    st.subheader("📚 Análisis anteriores")

    for i, item in enumerate(st.session_state.analisis_realizados[:5], start=1):
        with st.expander(f"{i}. {item['titulo']}"):
            st.markdown("### Descripción")
            st.markdown(item["descripcion"])

            st.markdown("### Análisis")
            st.markdown(item["analisis"])

    if st.button("Limpiar historial"):
        st.session_state.analisis_realizados = []
        st.rerun()
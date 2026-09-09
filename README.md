# Jira Story Analyzer

Asistente de IA para preparar historias de Jira antes de refinement y estimación.

La V1 convierte una historia en un análisis estructurado de alcance, gaps, riesgos,
estimabilidad y desglose técnico preliminar. Su objetivo no es "adivinar horas", sino ayudar
a decidir primero si existe información suficiente para defender una estimación.

> La IA prepara la estimación; la decisión final sigue siendo del equipo.

## Qué problema resuelve

En refinement es habitual intentar estimar historias que todavía tienen dudas de alcance,
permisos, integraciones, datos o comportamiento esperado. Eso genera números aparentemente
precisos sobre requisitos que aún no están suficientemente definidos.

Jira Story Analyzer introduce una decisión explícita de **estimation readiness** antes de
mostrar horas.

## Qué hace la V1

1. recibe la historia, criterios de aceptación y contexto técnico conocido;
2. separa hechos proporcionados, inferencias, supuestos e información faltante;
3. identifica dudas, riesgos y gaps realmente bloqueantes;
4. genera un desglose técnico preliminar sin inventar tecnologías o arquitectura;
5. decide si la historia es estimable;
6. solo muestra un rango de horas cuando existe una estimación defendible;
7. permite descargar el resultado en Markdown para compartirlo en Jira, Confluence o un chat de equipo.

La interfaz mantiene un único flujo: **Analizar historia**. No expone selector de modelo,
temperatura ni modos de análisis.

## Qué no hace

La V1 deliberadamente no incluye:

- integración directa con Jira;
- base de datos o persistencia de historias;
- RAG, agentes o LangGraph;
- autenticación o gestión multiusuario;
- selección de modelo desde la UI;
- estimaciones tratadas como compromiso de entrega;
- invención de arquitectura, tecnologías o requisitos que no estén respaldados por la historia.

## Estimation readiness

La salida final utiliza tres estados:

- `READY`: existe suficiente definición para mostrar un rango preliminar.
- `READY_WITH_RESERVATIONS`: existe un rango defendible, pero hay supuestos o información faltante no bloqueante.
- `NOT_READY`: existen gaps bloqueantes o no hay una estimación defendible.

La política final se aplica de forma determinista en código después de la respuesta del
modelo. Si el resultado es `NOT_READY`, la aplicación elimina cualquier estimación y fuerza
confianza baja, aunque el proveedor haya devuelto horas.

## Arquitectura

La V1 mantiene una arquitectura pequeña y explícita:

```text
app.py
  -> AnalysisService
    -> GeminiProvider
      -> AnalysisDraft
    -> estimation policy
      -> AnalysisResult
  -> Streamlit UI / Markdown export
```

Responsabilidades principales:

- `app.py`: UI Streamlit y estado de sesión.
- `src/config.py`: API key, modelo y timeout.
- `src/prompts/story_analysis.py`: reglas de análisis y grounding.
- `src/providers/gemini.py`: llamada estructurada a Gemini y traducción de errores.
- `src/domain/analysis.py`: contratos Pydantic de entrada y salida.
- `src/domain/estimation.py`: política final de estimabilidad y confianza.
- `src/services/analysis_service.py`: coordinación entre provider y dominio.
- `src/presentation/markdown.py`: exportación del análisis.

No se utiliza LangChain: una única llamada estructurada no justifica una capa adicional de
orquestación para esta V1.

## Stack

- Python 3.12
- Streamlit 1.63.0
- Google Gen AI SDK (`google-genai` 2.22.0)
- Gemini (`gemini-2.5-flash` por defecto)
- Pydantic 2.13.5
- pytest 9.1.1

## Configuración

La aplicación necesita una API key de Gemini.

Se admite, por orden de prioridad:

1. `GOOGLE_API_KEY` en variables de entorno;
2. `GEMINI_API_KEY` en variables de entorno;
3. `GOOGLE_API_KEY` en Streamlit Secrets;
4. `GEMINI_API_KEY` en Streamlit Secrets.

Modelo y timeout son configurables mediante:

```bash
GEMINI_MODEL="gemini-2.5-flash"
GEMINI_TIMEOUT_SECONDS="90"
```

Si no se especifican, la configuración oficial de la V1 es:

```text
model   = gemini-2.5-flash
timeout = 90 seconds
```

El timeout admitido está limitado a valores entre 5 y 120 segundos.

## Ejecución local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export GOOGLE_API_KEY="..."
streamlit run app.py
```

En Windows PowerShell puede configurarse la key con:

```powershell
$env:GOOGLE_API_KEY="..."
streamlit run app.py
```

## Tests y validación

Validación local:

```bash
pytest -q
python -m compileall app.py src tests scripts
```

La suite automática no consume Gemini real: utiliza dobles de prueba y smoke tests con una
key ficticia que no realiza peticiones.

El workflow `Core validation` ejecuta sobre Python 3.12:

- instalación de dependencias;
- `pip check`;
- compilación de fuentes;
- suite de pytest;
- comprobación de versiones runtime.

Se ejecuta automáticamente en `develop`, ramas `fix/**` y ramas V1 configuradas en el
workflow. Los pull requests hacia `develop` también activan la validación.

La validación semántica contra Gemini real puede ejecutarse manualmente con:

```bash
python scripts/live_core_validation.py
```

La combinación validada para la V1 es `gemini-2.5-flash` con timeout de 90 segundos.

## Privacidad y límites

- Las historias introducidas se envían a Gemini para generar el análisis.
- La aplicación no guarda historias ni resultados en una base de datos.
- El último análisis vive únicamente en `st.session_state` durante la sesión de Streamlit.
- Los logs técnicos no registran el texto de la historia ni la API key.
- Las estimaciones son orientativas y deben validarse con el equipo.
- La calidad del resultado depende de la información proporcionada y del comportamiento del modelo.

## Estructura del repositorio

```text
app.py
src/
  config.py
  domain/
    analysis.py
    estimation.py
  presentation/
    markdown.py
  prompts/
    story_analysis.py
  providers/
    gemini.py
  services/
    analysis_service.py
tests/
scripts/
docs/
```

`docs/baseline.md` conserva el punto de partida del prototipo como referencia histórica.

## Estado V1

- Etapas 0-2 — Baseline, refactor y Core: cerradas.
- Etapa 2.5 — Validación automatizada: cerrada.
- Etapa 3 — UX: cerrada.
- Etapa 3.5 — Validación E2E, visual y semántica con Gemini real: cerrada.
- Etapa 4 — Final Quality Review: en cierre de ajustes menores de release.

La rama de integración de la V1 es `develop`. El merge final a `main` y el despliegue de
producción se realizan únicamente después de cerrar la Etapa 4.

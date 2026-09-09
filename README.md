# Jira Story Analyzer

Asistente de IA para preparar historias de Jira antes de refinement y estimación.

La V1 transforma una historia en una salida estructurada con alcance, áreas impactadas,
hechos, inferencias, supuestos, información faltante, dudas, riesgos, desglose técnico y
un estado explícito de **estimation readiness**.

> La IA ayuda a preparar una estimación; no sustituye el criterio del equipo.

## Experiencia V1

La interfaz está pensada para que una persona pueda usarla sin conocer el stack interno:

1. pega la historia y el contexto que ya conozca;
2. opcionalmente carga un ejemplo para entender el producto en segundos;
3. ejecuta un único flujo: **Analizar historia**;
4. recibe primero el estado de estimabilidad y después el detalle;
5. descarga el análisis en Markdown para compartirlo en Jira, Confluence o un chat de equipo.

No hay selector de modelo, temperatura ni modos de análisis en la UI pública.

El último análisis se mantiene únicamente en `st.session_state` para que no desaparezca al
interactuar con la página. No existe persistencia en base de datos.

## Estimation readiness

- `READY`: existe suficiente definición para mostrar un rango preliminar.
- `READY_WITH_RESERVATIONS`: puede mostrarse un rango, pero hay supuestos o información
  faltante no bloqueante.
- `NOT_READY`: existen gaps bloqueantes o no hay una estimación defendible. La aplicación
  elimina cualquier rango de horas.

La política final se aplica en código después de la respuesta del modelo, por lo que un
`NOT_READY` nunca puede exponer horas aunque el proveedor las devuelva.

## Stack

- Python 3.12
- Streamlit 1.63
- Google Gen AI SDK (`google-genai`)
- Gemini (modelo configurable, `gemini-3.5-flash` por defecto)
- Pydantic
- pytest

LangChain no forma parte de la V1: una única llamada estructurada no justifica una capa
adicional de orquestación.

## Configuración local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export GOOGLE_API_KEY="..."
streamlit run app.py
```

También se admite `GEMINI_API_KEY`. En Streamlit se pueden usar los mismos nombres dentro
de `.streamlit/secrets.toml`.

Configuración opcional:

```bash
export GEMINI_MODEL="gemini-3.5-flash"
export GEMINI_TIMEOUT_SECONDS="45"
```

## Tests

```bash
pytest -q
python -m compileall app.py src tests scripts
```

Los tests automáticos no consumen la API de Gemini: usan dobles de prueba y smoke tests
reales de Streamlit/SDK con una key ficticia que no realiza peticiones.

La validación contra Gemini real se mantiene como gate de despliegue y puede ejecutarse
localmente con la key configurada en el entorno:

```bash
python scripts/live_core_validation.py
```

El workflow `Core validation` instala las dependencias fijadas en un Python 3.12 limpio,
ejecuta `pip check`, compila las fuentes y lanza toda la suite en las ramas de Core y UX.

## Privacidad

La aplicación no añade base de datos ni persistencia de historias. El contenido introducido
se envía a Gemini para generar el análisis. Los logs técnicos no registran el texto de la
historia y el último resultado solo vive durante la sesión actual de Streamlit.

## Estructura

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

## Estado

- Etapas 0-2 — Baseline, refactor y Core: cerradas.
- Etapa 2.5 — Validación automatizada: cerrada; E2E con Gemini real diferido al deploy.
- Etapa 3 — UX: implementada en `feature/v1-ux` y pendiente de validación final antes de merge.
- Deploy e integración con la web personal: fuera de esta rama.

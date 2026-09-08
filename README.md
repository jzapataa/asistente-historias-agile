# Jira Story Analyzer

Asistente de IA para preparar historias de Jira antes de refinement y estimación.

La V1 Core analiza una historia y devuelve una salida estructurada con alcance, áreas
impactadas, hechos, inferencias, supuestos, información faltante, dudas, riesgos,
desglose técnico y un estado explícito de **estimation readiness**.

> La IA ayuda a preparar una estimación; no sustituye el criterio del equipo.

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
- Streamlit
- Google Gen AI SDK (`google-genai`)
- Gemini (modelo configurable, `gemini-3.5-flash` por defecto)
- Pydantic
- pytest

LangChain no forma parte de la V1 Core: una única llamada estructurada no justifica una
capa adicional de orquestación.

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
python -m compileall app.py src tests
```

Los tests no llaman al proveedor real; Gemini se sustituye por dobles de prueba.

## Privacidad

La aplicación V1 Core no añade base de datos ni persistencia de historias. El contenido
introducido se envía a Gemini para generar el análisis. Los logs técnicos no registran el
texto de la historia.

## Estructura

```text
app.py
src/
  config.py
  domain/
    analysis.py
    estimation.py
  prompts/
    story_analysis.py
  providers/
    gemini.py
  services/
    analysis_service.py
tests/
docs/
```

## Estado

Esta rama cubre Baseline, Refactor mínimo y Core funcional. El rediseño visual, deploy e
integraciones externas quedan fuera de esta iteración.

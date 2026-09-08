# Baseline antes de V1 Core

Fecha de auditoría: 2026-09-08  
Rama fuente: `main`  
Commit fuente: `679a6b89787f29140a412c606ab62be8aff97d28`

## Estado original

El repositorio contenía solo:

- `.gitignore`
- `asistente_historias_agile.py`
- `requirements.txt`

La aplicación original concentraba Streamlit, configuración, secretos, prompt, llamada a
Gemini, estado de sesión y renderizado en un único fichero.

## Funcionalidad original observada

- Formulario de historia de Jira.
- Cuatro modos de análisis presentados en UI, pero no implementados como pipelines
  distintos.
- Selección manual de temperatura y modelo.
- Llamada a Gemini mediante LangChain con streaming de Markdown libre.
- Historial efímero en `st.session_state`.
- Estimación optimista/realista/pesimista pedida al modelo sin una política de dominio
  posterior que pudiera bloquear horas.

## Riesgos de baseline que esta iteración debe cerrar

1. Dependencias sin versiones fijadas.
2. SDK `google-generativeai` legado y redundante.
3. Acceso a `st.secrets` no seguro cuando no existe `secrets.toml`.
4. Sin output estructurado ni validación de schema.
5. Sin política determinista de estimabilidad.
6. Sin tests ni separación de responsabilidades.
7. Errores del proveedor demasiado genéricos y potencialmente expuestos al usuario.

Este documento es descriptivo; no afirma que el runtime original haya sido validado
end-to-end contra Gemini.

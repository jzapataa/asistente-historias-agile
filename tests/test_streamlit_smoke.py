from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def test_streamlit_app_starts_with_dummy_server_key(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key-not-used")

    app = AppTest.from_file(APP_PATH, default_timeout=10).run()

    assert not app.exception
    labels = [button.label for button in app.button]
    assert "Usar ejemplo" in labels
    assert "Limpiar" in labels
    assert "Analizar historia" in labels
    assert app.text_area(key="story_description")
    assert app.selectbox(key="story_task_type").value == "No lo sé"


def test_streamlit_app_handles_missing_key_without_uncaught_exception(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    app = AppTest.from_file(APP_PATH, default_timeout=10).run()

    assert not app.exception
    assert app.error
    assert "API key" in app.error[0].value

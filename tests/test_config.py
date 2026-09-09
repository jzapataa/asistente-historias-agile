from __future__ import annotations

import pytest

from src.config import (
    ConfigurationError,
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    Settings,
)


def clear_gemini_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "GEMINI_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)


def test_settings_reads_google_api_key_from_environment(monkeypatch) -> None:
    clear_gemini_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_API_KEY", " env-key ")

    settings = Settings.from_sources({})

    assert settings.api_key == "env-key"
    assert settings.model_name == DEFAULT_MODEL


def test_settings_uses_v1_gemini_defaults(monkeypatch) -> None:
    clear_gemini_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_API_KEY", "key")

    settings = Settings.from_sources({})

    assert DEFAULT_MODEL == "gemini-2.5-flash-lite"
    assert DEFAULT_TIMEOUT_SECONDS == 90
    assert settings.model_name == "gemini-2.5-flash-lite"
    assert settings.request_timeout_seconds == 90


def test_settings_allows_model_and_timeout_overrides_from_environment(monkeypatch) -> None:
    clear_gemini_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_API_KEY", "key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")
    monkeypatch.setenv("GEMINI_TIMEOUT_SECONDS", "60")

    settings = Settings.from_sources({})

    assert settings.model_name == "gemini-test"
    assert settings.request_timeout_seconds == 60


def test_settings_reads_key_from_streamlit_secrets_when_env_is_absent(monkeypatch) -> None:
    clear_gemini_env(monkeypatch)

    settings = Settings.from_sources({"GOOGLE_API_KEY": "secret-key"})

    assert settings.api_key == "secret-key"


def test_settings_allows_model_and_timeout_overrides_from_streamlit_secrets(monkeypatch) -> None:
    clear_gemini_env(monkeypatch)

    settings = Settings.from_sources(
        {
            "GOOGLE_API_KEY": "secret-key",
            "GEMINI_MODEL": "gemini-secret-model",
            "GEMINI_TIMEOUT_SECONDS": "75",
        }
    )

    assert settings.model_name == "gemini-secret-model"
    assert settings.request_timeout_seconds == 75


def test_settings_accepts_gemini_api_key_alias(monkeypatch) -> None:
    clear_gemini_env(monkeypatch)

    settings = Settings.from_sources({"GEMINI_API_KEY": "alias-key"})

    assert settings.api_key == "alias-key"


def test_settings_missing_key_is_a_configuration_error(monkeypatch) -> None:
    clear_gemini_env(monkeypatch)

    with pytest.raises(ConfigurationError, match="API key"):
        Settings.from_sources({})


def test_settings_rejects_timeout_outside_safe_range(monkeypatch) -> None:
    clear_gemini_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_API_KEY", "key")
    monkeypatch.setenv("GEMINI_TIMEOUT_SECONDS", "2")

    with pytest.raises(ConfigurationError, match="entre 5 y 120"):
        Settings.from_sources({})

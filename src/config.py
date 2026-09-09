"""Application configuration loaded from environment and optional Streamlit secrets."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping, Any


DEFAULT_MODEL = "gemini-2.5-flash-lite"
DEFAULT_TIMEOUT_SECONDS = 90


class ConfigurationError(RuntimeError):
    """Raised when required application configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    api_key: str
    model_name: str = DEFAULT_MODEL
    request_timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS

    @classmethod
    def from_sources(
        cls,
        secrets: Mapping[str, Any] | None = None,
    ) -> "Settings":
        secrets = secrets or {}

        api_key = (
            os.getenv("GOOGLE_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or _secret_value(secrets, "GOOGLE_API_KEY")
            or _secret_value(secrets, "GEMINI_API_KEY")
        )
        if not api_key or not api_key.strip():
            raise ConfigurationError(
                "No se ha configurado una API key de Gemini. Usa GOOGLE_API_KEY "
                "o GEMINI_API_KEY en el entorno o en Streamlit Secrets."
            )

        model_name = (
            os.getenv("GEMINI_MODEL")
            or _secret_value(secrets, "GEMINI_MODEL")
            or DEFAULT_MODEL
        )
        timeout_raw = (
            os.getenv("GEMINI_TIMEOUT_SECONDS")
            or _secret_value(secrets, "GEMINI_TIMEOUT_SECONDS")
        )
        timeout = _parse_timeout(timeout_raw)

        return cls(
            api_key=api_key.strip(),
            model_name=str(model_name).strip(),
            request_timeout_seconds=timeout,
        )


def _secret_value(secrets: Mapping[str, Any], key: str) -> str | None:
    try:
        value = secrets.get(key)
    except Exception:
        return None
    return str(value) if value is not None else None


def _parse_timeout(raw: str | None) -> int:
    if raw is None:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError("GEMINI_TIMEOUT_SECONDS debe ser un entero.") from exc
    if not 5 <= value <= 120:
        raise ConfigurationError(
            "GEMINI_TIMEOUT_SECONDS debe estar entre 5 y 120 segundos."
        )
    return value

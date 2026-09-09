"""Gemini provider using Google's current Gen AI SDK directly."""

from __future__ import annotations

import logging
from typing import Any

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from src.domain.analysis import AnalysisDraft, StoryInput
from src.prompts.story_analysis import SYSTEM_PROMPT, build_story_prompt


logger = logging.getLogger(__name__)


_SUPPORTED_JSON_SCHEMA_KEYS = frozenset(
    {
        "$id",
        "$defs",
        "$ref",
        "$anchor",
        "type",
        "format",
        "title",
        "description",
        "enum",
        "items",
        "prefixItems",
        "minItems",
        "maxItems",
        "minimum",
        "maximum",
        "anyOf",
        "oneOf",
        "properties",
        "additionalProperties",
        "required",
        "propertyOrdering",
    }
)
_SCHEMA_MAP_KEYS = frozenset({"$defs", "properties"})


class ProviderError(RuntimeError):
    user_message = "No se ha podido generar el análisis en este momento."


class ProviderAuthenticationError(ProviderError):
    user_message = "La configuración de acceso a Gemini no es válida."


class ProviderRateLimitError(ProviderError):
    user_message = (
        "Gemini ha alcanzado temporalmente su límite de uso. Inténtalo de nuevo más tarde."
    )


class ProviderTimeoutError(ProviderError):
    user_message = "Gemini ha tardado demasiado en responder. Inténtalo de nuevo."


class ProviderUnavailableError(ProviderError):
    user_message = "Gemini no está disponible temporalmente. Inténtalo de nuevo más tarde."


class ProviderRequestError(ProviderError):
    user_message = "Gemini ha rechazado la solicitud. Revisa el modelo y la configuración."


class InvalidProviderResponseError(ProviderError):
    user_message = (
        "Gemini respondió, pero el análisis no cumplió el formato esperado. Inténtalo de nuevo."
    )


def _sanitize_json_schema(value: Any, *, parent_key: str | None = None) -> Any:
    """Keep only JSON Schema keywords supported by Gemini structured output.

    Pydantic emits useful validation metadata such as ``default``, ``minLength`` and
    ``exclusiveMinimum``. The domain model still enforces those constraints after the
    response, but Gemini's JSON-schema endpoint supports a smaller keyword subset.
    """

    if isinstance(value, dict):
        if parent_key in _SCHEMA_MAP_KEYS:
            return {
                name: _sanitize_json_schema(schema)
                for name, schema in value.items()
            }
        return {
            key: _sanitize_json_schema(item, parent_key=key)
            for key, item in value.items()
            if key in _SUPPORTED_JSON_SCHEMA_KEYS
        }
    if isinstance(value, list):
        return [_sanitize_json_schema(item) for item in value]
    return value


def build_analysis_response_schema() -> dict[str, Any]:
    """Return a Gemini-compatible JSON Schema for the provider-facing draft."""

    return _sanitize_json_schema(AnalysisDraft.model_json_schema())


class GeminiProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        timeout_seconds: int,
        client: Any | None = None,
    ) -> None:
        self.model_name = model_name
        self._client = client or genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=timeout_seconds * 1_000),
        )

    def analyze(self, story: StoryInput) -> AnalysisDraft:
        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=build_story_prompt(story),
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_json_schema=build_analysis_response_schema(),
                ),
            )
        except errors.ClientError as exc:
            logger.warning("Gemini client error status=%s", exc.code)
            if exc.code in {401, 403}:
                raise ProviderAuthenticationError() from None
            if exc.code == 429:
                raise ProviderRateLimitError() from None
            raise ProviderRequestError() from None
        except errors.ServerError as exc:
            logger.warning("Gemini server error status=%s", exc.code)
            raise ProviderUnavailableError() from None
        except ValidationError as exc:
            logger.warning("Gemini request validation failed type=%s", type(exc).__name__)
            raise ProviderRequestError() from None
        except Exception as exc:
            error_type = type(exc).__name__
            logger.warning("Gemini transport error type=%s", error_type)
            if "timeout" in error_type.lower():
                raise ProviderTimeoutError() from None
            raise ProviderUnavailableError() from None

        try:
            response_text = getattr(response, "text", None)
            if not response_text:
                raise InvalidProviderResponseError()
            return AnalysisDraft.model_validate_json(response_text)
        except (ValidationError, ValueError, TypeError) as exc:
            logger.warning("Gemini response validation failed type=%s", type(exc).__name__)
            raise InvalidProviderResponseError() from None

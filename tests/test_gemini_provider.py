from __future__ import annotations

from types import SimpleNamespace

import pytest
from google.genai import errors
from pydantic import ValidationError

from src.domain.analysis import AnalysisDraft
from src.providers.gemini import (
    GeminiProvider,
    InvalidProviderResponseError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    build_analysis_response_schema,
)


class ModelsStub:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.last_kwargs = None

    def generate_content(self, **kwargs):
        self.last_kwargs = kwargs
        if self.error:
            raise self.error
        return self.response


class ClientStub:
    def __init__(self, models: ModelsStub) -> None:
        self.models = models


def build_provider(models: ModelsStub) -> GeminiProvider:
    return GeminiProvider(
        api_key="test-key",
        model_name="gemini-test",
        timeout_seconds=5,
        client=ClientStub(models),
    )


def test_provider_uses_json_schema_and_validates_response_text(
    story, ready_draft: AnalysisDraft
) -> None:
    models = ModelsStub(response=SimpleNamespace(text=ready_draft.model_dump_json()))
    provider = build_provider(models)

    result = provider.analyze(story)

    assert result == ready_draft
    assert models.last_kwargs["model"] == "gemini-test"
    config = models.last_kwargs["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_schema is None
    assert config.response_json_schema == build_analysis_response_schema()


def test_json_schema_strips_keywords_not_supported_by_gemini() -> None:
    schema = build_analysis_response_schema()
    serialized = str(schema)

    assert "$defs" in schema
    assert "anyOf" in serialized
    assert "default" not in serialized
    assert "exclusiveMinimum" not in serialized
    assert "minLength" not in serialized
    assert "maxLength" not in serialized


def test_provider_rejects_invalid_response(story) -> None:
    models = ModelsStub(response=SimpleNamespace(text='{"summary": "solo"}'))
    provider = build_provider(models)

    with pytest.raises(InvalidProviderResponseError):
        provider.analyze(story)


@pytest.mark.parametrize("status_code", [401, 403])
def test_provider_maps_authentication_errors(story, status_code: int) -> None:
    api_error = errors.ClientError(
        status_code,
        {
            "error": {
                "code": status_code,
                "message": "auth failed",
                "status": "PERMISSION_DENIED",
            }
        },
    )
    provider = build_provider(ModelsStub(error=api_error))

    with pytest.raises(ProviderAuthenticationError):
        provider.analyze(story)


def test_provider_maps_rate_limit(story) -> None:
    api_error = errors.ClientError(
        429,
        {"error": {"code": 429, "message": "quota", "status": "RESOURCE_EXHAUSTED"}},
    )
    provider = build_provider(ModelsStub(error=api_error))

    with pytest.raises(ProviderRateLimitError):
        provider.analyze(story)


def test_provider_maps_other_client_error_as_request_error(story) -> None:
    api_error = errors.ClientError(
        400,
        {"error": {"code": 400, "message": "bad request", "status": "INVALID_ARGUMENT"}},
    )
    provider = build_provider(ModelsStub(error=api_error))

    with pytest.raises(ProviderRequestError):
        provider.analyze(story)


@pytest.mark.parametrize("status_code", [500, 503])
def test_provider_maps_server_errors_as_unavailable(story, status_code: int) -> None:
    api_error = errors.ServerError(
        status_code,
        {
            "error": {
                "code": status_code,
                "message": "provider unavailable",
                "status": "UNAVAILABLE",
            }
        },
    )
    provider = build_provider(ModelsStub(error=api_error))

    with pytest.raises(ProviderUnavailableError):
        provider.analyze(story)


def test_provider_maps_timeout_transport_error(story) -> None:
    provider = build_provider(ModelsStub(error=TimeoutError("request timed out")))

    with pytest.raises(ProviderTimeoutError):
        provider.analyze(story)


def test_provider_maps_sdk_validation_error_as_request_error(story) -> None:
    try:
        AnalysisDraft.model_validate({})
    except ValidationError as validation_error:
        provider = build_provider(ModelsStub(error=validation_error))
    else:  # pragma: no cover - defensive, the model requires fields
        raise AssertionError("Expected AnalysisDraft validation to fail")

    with pytest.raises(ProviderRequestError):
        provider.analyze(story)


def test_provider_maps_unknown_transport_failure(story) -> None:
    provider = build_provider(ModelsStub(error=RuntimeError("network down")))

    with pytest.raises(ProviderUnavailableError):
        provider.analyze(story)

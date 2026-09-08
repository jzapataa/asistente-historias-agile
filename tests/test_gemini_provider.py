from __future__ import annotations

from types import SimpleNamespace

import pytest
from google.genai import errors

from src.domain.analysis import AnalysisDraft
from src.providers.gemini import (
    GeminiProvider,
    InvalidProviderResponseError,
    ProviderRateLimitError,
    ProviderUnavailableError,
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


def test_provider_uses_structured_parsed_response(story, ready_draft: AnalysisDraft) -> None:
    models = ModelsStub(response=SimpleNamespace(parsed=ready_draft, text=None))
    provider = build_provider(models)

    result = provider.analyze(story)

    assert result == ready_draft
    assert models.last_kwargs["model"] == "gemini-test"
    assert models.last_kwargs["config"].response_mime_type == "application/json"


def test_provider_accepts_valid_json_fallback(story, ready_draft: AnalysisDraft) -> None:
    models = ModelsStub(
        response=SimpleNamespace(parsed=None, text=ready_draft.model_dump_json())
    )
    provider = build_provider(models)

    result = provider.analyze(story)

    assert result.summary == ready_draft.summary


def test_provider_rejects_invalid_response(story) -> None:
    models = ModelsStub(response=SimpleNamespace(parsed=None, text='{"summary": "solo"}'))
    provider = build_provider(models)

    with pytest.raises(InvalidProviderResponseError):
        provider.analyze(story)


def test_provider_maps_rate_limit(story) -> None:
    api_error = errors.ClientError(
        429,
        {"error": {"code": 429, "message": "quota", "status": "RESOURCE_EXHAUSTED"}},
    )
    provider = build_provider(ModelsStub(error=api_error))

    with pytest.raises(ProviderRateLimitError):
        provider.analyze(story)


def test_provider_maps_unknown_transport_failure(story) -> None:
    provider = build_provider(ModelsStub(error=RuntimeError("network down")))

    with pytest.raises(ProviderUnavailableError):
        provider.analyze(story)

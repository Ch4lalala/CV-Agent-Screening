import asyncio
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from app.ai import client as client_module
from app.ai.client import AIClient, get_ai_client, get_chat_model
from app.ai.config import get_ai_settings
from app.ai.exceptions import (
    AIConfigurationError,
    AIProviderError,
    AIStructuredOutputError,
)
from app.ai.structured_output import AIHealthResponse
from app.main import app


class ResultRunnable:
    def __init__(self, result: object) -> None:
        self.result = result

    async def ainvoke(self, _: object) -> object:
        return self.result


class NativeStructuredModel:
    def __init__(self, result: object) -> None:
        self.result = result

    def with_structured_output(self, _: object, **__: object) -> ResultRunnable:
        return ResultRunnable(self.result)


class FallbackModel:
    def with_structured_output(self, _: object, **__: object) -> None:
        raise NotImplementedError

    async def ainvoke(self, _: object) -> AIMessage:
        return AIMessage(content='{"message":"fallback works","status":"ok"}')


class PlainModel:
    def __init__(self, response: object) -> None:
        self.response = response

    async def ainvoke(self, _: object) -> object:
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


@pytest.fixture(autouse=True)
def reset_ai_state(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for name in (
        "AI_API_KEY",
        "AI_BASE_URL",
        "AI_MODEL",
        "AI_TIMEOUT_SECONDS",
        "AI_MAX_RETRIES",
        "AI_TEMPERATURE",
    ):
        monkeypatch.delenv(name, raising=False)
    get_ai_settings.cache_clear()
    get_chat_model.cache_clear()
    get_ai_client.cache_clear()
    yield
    app.dependency_overrides.pop(get_ai_client, None)
    get_ai_settings.cache_clear()
    get_chat_model.cache_clear()
    get_ai_client.cache_clear()


def configure_ai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_API_KEY", "test-provider-key")
    monkeypatch.setenv("AI_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("AI_MODEL", "test-model")
    monkeypatch.setenv("AI_TIMEOUT_SECONDS", "12")
    monkeypatch.setenv("AI_MAX_RETRIES", "1")
    monkeypatch.setenv("AI_TEMPERATURE", "0.2")


def test_valid_ai_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_ai(monkeypatch)

    settings = get_ai_settings()

    assert settings.api_key is not None
    assert settings.api_key.get_secret_value() == "test-provider-key"
    assert settings.base_url == "https://provider.example/v1"
    assert settings.model == "test-model"
    assert settings.timeout_seconds == 12
    assert settings.max_retries == 1
    assert settings.temperature == 0.2

    model = get_chat_model()
    assert model.model_name == "test-model"
    assert model.openai_api_base == "https://provider.example/v1"
    assert model.request_timeout == 12
    assert model.max_retries == 1
    assert model.temperature == 0.2


@pytest.mark.parametrize("missing_name", ["AI_API_KEY", "AI_MODEL"])
def test_missing_required_configuration(
    monkeypatch: pytest.MonkeyPatch, missing_name: str
) -> None:
    configure_ai(monkeypatch)
    monkeypatch.delenv(missing_name)

    with pytest.raises(AIConfigurationError, match=missing_name):
        get_chat_model()


def test_client_creation_is_lazy(monkeypatch: pytest.MonkeyPatch) -> None:
    model = PlainModel(AIMessage(content="available"))
    calls = 0

    def fake_get_chat_model() -> PlainModel:
        nonlocal calls
        calls += 1
        return model

    monkeypatch.setattr(client_module, "get_chat_model", fake_get_chat_model)
    client = AIClient()

    assert calls == 0
    asyncio.run(client.invoke([HumanMessage(content="hello")]))
    assert calls == 1


def test_plain_invocation_success() -> None:
    client = AIClient(PlainModel(AIMessage(content="hello")))

    result = asyncio.run(client.invoke([HumanMessage(content="hello")]))

    assert result.content == "hello"


def test_provider_exception_is_converted_without_details() -> None:
    provider_message = "provider rejected secret-key-value"
    client = AIClient(PlainModel(RuntimeError(provider_message)))

    with pytest.raises(AIProviderError) as error:
        asyncio.run(client.invoke([HumanMessage(content="hello")]))

    assert provider_message not in str(error.value)
    assert str(error.value) == "AI provider request failed"


def test_structured_output_validation_success() -> None:
    client = AIClient(
        NativeStructuredModel({"message": "model ready", "status": "ok"})
    )

    result = asyncio.run(
        client.invoke_structured(
            AIHealthResponse, [HumanMessage(content="check")]
        )
    )

    assert result == AIHealthResponse(message="model ready", status="ok")


def test_invalid_structured_output_failure() -> None:
    client = AIClient(
        NativeStructuredModel({"message": "wrong status", "status": "failed"})
    )

    with pytest.raises(AIStructuredOutputError):
        asyncio.run(
            client.invoke_structured(
                AIHealthResponse, [HumanMessage(content="check")]
            )
        )


def test_structured_output_fallback() -> None:
    client = AIClient(FallbackModel())

    result = asyncio.run(
        client.invoke_structured(
            AIHealthResponse, [HumanMessage(content="check")]
        )
    )

    assert result.status == "ok"
    assert result.message == "fallback works"


def test_health_does_not_require_ai_configuration(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_ai_endpoint_reports_missing_configuration(client: TestClient) -> None:
    response = client.post("/api/v1/ai/test")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Missing required AI configuration: AI_API_KEY, AI_MODEL"
    }


def test_ai_endpoint_success_without_network(client: TestClient) -> None:
    class SuccessfulClient:
        model_name = "mock-model"

        async def invoke_structured(
            self, _: object, __: object
        ) -> AIHealthResponse:
            return AIHealthResponse(message="model ready", status="ok")

    app.dependency_overrides[get_ai_client] = SuccessfulClient

    response = client.post("/api/v1/ai/test")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "model": "mock-model",
        "message": "model ready",
    }


def test_ai_endpoint_does_not_expose_provider_error_or_secret(
    client: TestClient,
) -> None:
    secret = "never-return-this-api-key"

    class FailingClient:
        model_name = "mock-model"

        async def invoke_structured(self, _: object, __: object) -> Any:
            provider_error = RuntimeError(f"authorization failed for {secret}")
            raise AIProviderError("AI provider request failed") from provider_error

    app.dependency_overrides[get_ai_client] = FailingClient

    response = client.post("/api/v1/ai/test")

    assert response.status_code == 502
    assert response.json() == {"detail": "AI provider is temporarily unavailable"}
    assert secret not in response.text

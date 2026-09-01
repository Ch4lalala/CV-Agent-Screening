"""Single reusable model-client construction and invocation path."""

import logging
from collections.abc import Sequence
from functools import lru_cache
from typing import TypeVar

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.ai.config import AISettings, get_ai_settings
from app.ai.exceptions import (
    AIConfigurationError,
    AIProviderError,
    AIStructuredOutputError,
)
from app.ai.structured_output import invoke_structured_output

logger = logging.getLogger(__name__)
SchemaT = TypeVar("SchemaT", bound=BaseModel)


def _create_chat_model(settings: AISettings) -> ChatOpenAI:
    settings.require_provider_configuration()
    try:
        return ChatOpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            model=settings.model,
            timeout=settings.timeout_seconds,
            max_retries=settings.max_retries,
            temperature=settings.temperature,
        )
    except Exception as exc:
        raise AIConfigurationError("AI client configuration is invalid") from exc


@lru_cache(maxsize=1)
def get_chat_model() -> ChatOpenAI:
    """Create and cache the provider client only when an AI call needs it."""

    return _create_chat_model(get_ai_settings())


class AIClient:
    """Generic asynchronous AI facade used by future application services."""

    def __init__(self, model: object | None = None) -> None:
        self._model = model

    def get_model(self) -> object:
        """Expose the centrally configured model for compatible internal tools."""

        if self._model is None:
            self._model = get_chat_model()
        return self._model

    @property
    def model_name(self) -> str:
        settings = get_ai_settings()
        settings.require_provider_configuration()
        assert settings.model is not None
        return settings.model

    async def invoke(self, messages: Sequence[BaseMessage]) -> BaseMessage:
        """Run an ordinary chat-model request through the shared client."""

        try:
            response = await self.get_model().ainvoke(list(messages))  # type: ignore[attr-defined]
        except AIConfigurationError:
            raise
        except Exception as exc:
            logger.warning("AI request failed (%s)", type(exc).__name__)
            raise AIProviderError("AI provider request failed") from exc

        if not isinstance(response, BaseMessage):
            logger.warning("AI request returned an unexpected response type")
            raise AIProviderError("AI provider returned an invalid response")
        return response

    async def invoke_structured(
        self,
        schema: type[SchemaT],
        messages: Sequence[BaseMessage],
    ) -> SchemaT:
        """Run a model request and validate its response against a schema."""

        try:
            return await invoke_structured_output(
                self.get_model(), schema, list(messages)
            )
        except AIConfigurationError:
            logger.warning("AI configuration is unavailable")
            raise
        except AIStructuredOutputError:
            logger.warning("Structured output validation failed")
            raise
        except Exception as exc:
            logger.warning("AI request failed (%s)", type(exc).__name__)
            raise AIProviderError("AI provider request failed") from exc


@lru_cache(maxsize=1)
def get_ai_client() -> AIClient:
    """Return the process-local client without initializing a provider SDK."""

    return AIClient()

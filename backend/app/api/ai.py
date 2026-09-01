"""Minimal endpoint for explicitly testing optional AI configuration."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.ai.client import AIClient, get_ai_client
from app.ai.exceptions import (
    AIConfigurationError,
    AIProviderError,
    AIStructuredOutputError,
)
from app.ai.structured_output import AIHealthResponse

router = APIRouter(prefix="/ai", tags=["ai"])
AIClientDependency = Annotated[AIClient, Depends(get_ai_client)]


class AITestResponse(BaseModel):
    status: Literal["ok"]
    model: str
    message: str


@router.post("/test", response_model=AITestResponse)
async def test_ai_connection(client: AIClientDependency) -> AITestResponse:
    """Make one small, explicit provider call and validate its output."""

    messages = [
        SystemMessage(
            content=(
                "This is a connectivity test. Return the requested schema with "
                "status set to 'ok' and a short confirmation message. Do not "
                "include credentials or configuration values."
            )
        ),
        HumanMessage(content="Confirm that the model is available."),
    ]
    try:
        result = await client.invoke_structured(AIHealthResponse, messages)
        model_name = client.model_name
    except AIConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except AIProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider is temporarily unavailable",
        ) from exc
    except AIStructuredOutputError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider returned an invalid structured response",
        ) from exc

    return AITestResponse(
        status=result.status,
        model=model_name,
        message=result.message,
    )

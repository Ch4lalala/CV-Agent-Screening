"""Pydantic-validated structured output for provider-agnostic model calls."""

from collections.abc import Sequence
from typing import Literal, TypeVar

from langchain_core.exceptions import OutputParserException
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.ai.exceptions import AIStructuredOutputError

SchemaT = TypeVar("SchemaT", bound=BaseModel)
_NATIVE_UNAVAILABLE_STATUS_CODES = {400, 404, 405, 422}


class AIHealthResponse(BaseModel):
    """Small schema used only to verify structured model connectivity."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=200)
    status: Literal["ok"]


def _validate_result(schema: type[SchemaT], result: object) -> SchemaT:
    try:
        if isinstance(result, schema):
            return result
        return schema.model_validate(result)
    except ValidationError as exc:
        raise AIStructuredOutputError(
            "AI provider returned invalid structured output"
        ) from exc


async def _invoke_json_fallback(
    model: object,
    schema: type[SchemaT],
    messages: Sequence[BaseMessage],
) -> SchemaT:
    parser = PydanticOutputParser(pydantic_object=schema)
    format_message = SystemMessage(
        content=(
            "Return only a JSON value that follows this schema. "
            "Do not add prose or markdown.\n"
            f"{parser.get_format_instructions()}"
        )
    )
    response = await model.ainvoke([format_message, *messages])  # type: ignore[attr-defined]
    content = getattr(response, "content", None)
    if not isinstance(content, str):
        raise AIStructuredOutputError(
            "AI provider returned invalid structured output"
        )
    try:
        return parser.parse(content)
    except (OutputParserException, ValidationError, ValueError, TypeError) as exc:
        raise AIStructuredOutputError(
            "AI provider returned invalid structured output"
        ) from exc


async def invoke_structured_output(
    model: object,
    schema: type[SchemaT],
    messages: Sequence[BaseMessage],
) -> SchemaT:
    """Invoke native structured output, with a simple JSON parsing fallback.

    The fallback is used when the adapter does not implement native structured
    output or an endpoint rejects that request shape. Other provider errors
    bubble to the client layer for consistent classification.
    """

    try:
        structured_model = model.with_structured_output(  # type: ignore[attr-defined]
            schema,
            method="function_calling",
        )
    except (AttributeError, NotImplementedError):
        return await _invoke_json_fallback(model, schema, messages)

    try:
        result = await structured_model.ainvoke(list(messages))
    except NotImplementedError:
        return await _invoke_json_fallback(model, schema, messages)
    except (OutputParserException, ValidationError) as exc:
        raise AIStructuredOutputError(
            "AI provider returned invalid structured output"
        ) from exc
    except Exception as exc:
        if getattr(exc, "status_code", None) in _NATIVE_UNAVAILABLE_STATUS_CODES:
            return await _invoke_json_fallback(model, schema, messages)
        raise

    return _validate_result(schema, result)

"""Environment-backed AI settings with no import-time provider setup."""

import os
from dataclasses import dataclass
from functools import lru_cache

from pydantic import SecretStr

from app.ai.exceptions import AIConfigurationError


def _optional_environment_value(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _float_environment_value(name: str, default: float) -> float:
    raw_value = _optional_environment_value(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError as exc:
        raise AIConfigurationError(f"{name} must be a number") from exc


def _integer_environment_value(name: str, default: int) -> int:
    raw_value = _optional_environment_value(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise AIConfigurationError(f"{name} must be an integer") from exc


@dataclass(frozen=True, repr=False)
class AISettings:
    """Configuration shared by every model call in the application."""

    api_key: SecretStr | None
    base_url: str | None
    model: str | None
    timeout_seconds: float = 60.0
    max_retries: int = 2
    temperature: float = 0.0

    @classmethod
    def from_environment(cls) -> "AISettings":
        api_key = _optional_environment_value("AI_API_KEY")
        settings = cls(
            api_key=SecretStr(api_key) if api_key is not None else None,
            base_url=_optional_environment_value("AI_BASE_URL"),
            model=_optional_environment_value("AI_MODEL"),
            timeout_seconds=_float_environment_value("AI_TIMEOUT_SECONDS", 60.0),
            max_retries=_integer_environment_value("AI_MAX_RETRIES", 2),
            temperature=_float_environment_value("AI_TEMPERATURE", 0.0),
        )
        settings.validate_values()
        return settings

    def validate_values(self) -> None:
        if not 0 < self.timeout_seconds <= 600:
            raise AIConfigurationError(
                "AI_TIMEOUT_SECONDS must be greater than 0 and at most 600"
            )
        if not 0 <= self.max_retries <= 10:
            raise AIConfigurationError("AI_MAX_RETRIES must be between 0 and 10")
        if not 0 <= self.temperature <= 2:
            raise AIConfigurationError("AI_TEMPERATURE must be between 0 and 2")

    def require_provider_configuration(self) -> None:
        missing = []
        if self.api_key is None:
            missing.append("AI_API_KEY")
        if self.model is None:
            missing.append("AI_MODEL")
        if missing:
            joined_names = ", ".join(missing)
            raise AIConfigurationError(
                f"Missing required AI configuration: {joined_names}"
            )


@lru_cache(maxsize=1)
def get_ai_settings() -> AISettings:
    """Read AI settings on first AI use, not during application startup."""

    return AISettings.from_environment()


def get_configured_ai_model_name() -> str | None:
    """Return only the non-secret model identifier for screening audit metadata."""

    return _optional_environment_value("AI_MODEL")

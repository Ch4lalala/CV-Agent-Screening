"""Safe application-level exceptions for AI integration failures."""


class AIError(Exception):
    """Base class for failures exposed by the internal AI abstraction."""


class AIConfigurationError(AIError):
    """Raised when required AI configuration is missing or invalid."""


class AIProviderError(AIError):
    """Raised when the configured model provider cannot complete a request."""


class AIStructuredOutputError(AIError):
    """Raised when a model response does not satisfy the requested schema."""

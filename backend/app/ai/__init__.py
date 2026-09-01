"""Central AI integration primitives.

Application code should import AI access from this package instead of creating
provider SDK clients directly.
"""

from app.ai.client import AIClient, get_ai_client
from app.ai.exceptions import (
    AIConfigurationError,
    AIProviderError,
    AIStructuredOutputError,
)

__all__ = [
    "AIClient",
    "AIConfigurationError",
    "AIProviderError",
    "AIStructuredOutputError",
    "get_ai_client",
]

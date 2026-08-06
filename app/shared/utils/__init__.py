"""
Shared utilities for MCP services.

LLM Integration:
    - LLMResponse: Response wrapper for LLM-generated content
    - client_supports_elicitation: Check if client supports MCP elicitation
"""

from app.shared.utils.llm_utils import (
    LLMResponse,
    client_supports_elicitation,
)

__all__ = [
    "LLMResponse",
    "client_supports_elicitation",
]

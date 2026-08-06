# Copyright [2026] [IBM]
# Licensed under the Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0)
# See the LICENSE file in the project root for license information.

"""
Utilities for LLM interactions.

Key Components:
    - client_supports_elicitation: Check if client supports MCP elicitation capability
    - LLMResponse: Response wrapper containing generated content
"""

from typing import Optional
from fastmcp import Context
from app.shared.logging import LOGGER


class LLMResponse:
    def __init__(self, content: str):
        self.content = content


def client_supports_elicitation(ctx: Optional[Context]) -> bool:
    """
    Check if the MCP client supports elicitation capability.
    
    Inspects the negotiated client capabilities from the MCP session to
    determine whether elicitation is available, without actually calling
    ctx.elicit().
    
    IMPORTANT: Elicitation requires a STATEFUL MCP server. The server must
    maintain session state across multiple requests to support the elicitation
    workflow (prompt -> user response -> continuation). This is verified by
    checking for the presence of fastmcp_context and a valid session_id.
    
    Args:
        ctx: Optional MCP Context containing session and client information
        
    Returns:
        True if both client advertises elicitation support AND server is stateful,
        False otherwise
        
    Example:
        >>> from app.shared.logging import auto_context
        >>>
        >>> @auto_context
        >>> async def my_tool(request, ctx=None):
        ...     if client_supports_elicitation(ctx):
        ...         response = await ctx.elicit(message="...", response_type=MyModel)
    """
    if not ctx:
        return False
    
    try:
        # Check for server statefulness via fastmcp_context
        # The MCP server needs to be stateful for elicitation to work properly
        if not hasattr(ctx, 'session_id') or ctx.session_id is None:
            LOGGER.debug("FastMCP session_id not available or None so MCP server is likely stateless")
            return False
        
        # Check client capabilities for elicitation support
        session = ctx.session
        if session is None:
            return False
        client_params = session.client_params
        if client_params is None or client_params.capabilities is None:
            return False
        return client_params.capabilities.elicitation is not None
    except Exception:
        # Any issue accessing capabilities means we can't confirm support
        return False



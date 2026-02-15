"""
Guardrails Middleware.

Responsible for:
- Enforcing AI safety constraints
- Filtering or validating user input
- Filtering or validating model output
- Preventing unsafe or disallowed behavior

Applies cross-cutting AI safety policies across the system.
"""

# Example Code:
from starlette.middleware.base import BaseHTTPMiddleware


class GuardrailsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        return response

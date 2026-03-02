"""
Guardrails Middleware.

Responsible for:
- Enforcing AI safety constraints
- Filtering or validating user input
- Filtering or validating model output
- Preventing unsafe or disallowed behavior

Applies cross-cutting AI safety policies across the system.

This repo currently applies LLM-related guardrails primarily outside the HTTP
layer:
- Provider-agnostic PII redaction is applied at the LLM boundary (LLM factory).
- Service-layer redaction can be applied before state enters LangGraph to avoid
    persisting raw PII in checkpoints/state.

We keep this HTTP middleware minimal to avoid subtle request-body streaming
issues (especially with file uploads) and to ensure guardrails also apply to
non-HTTP entry points.
"""

# Example Code:
from functools import lru_cache

from starlette.middleware.base import BaseHTTPMiddleware

from app.infrastructure.llm.pii_guardrails import PiiInputRedactor


class GuardrailsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        return response


@lru_cache(maxsize=1)
def get_pii_input_redactor() -> PiiInputRedactor:
    """Global PII redactor (inputs only).

    Used by services to sanitize user-provided fields before they enter graph
    state/checkpointing.
    """

    return PiiInputRedactor()

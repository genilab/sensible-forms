"""
Global Constants.

Defines:
- Default configuration values
- Reusable fixed values
- System-wide limits

Avoid hardcoding repeated values throughout the codebase.
"""

# LLM invocation defaults/limits
#
# These are intentionally conservative defaults for this example repo.
# Override per-call when needed.

# A general upper limit for single-shot responses in this repo.
LLM_TOKEN_UPPER_LIMIT: int = 1024

# Used in chat-style assistants where we want deterministic-ish answers.
LLM_TEMPERATURE_LOW: float = 0.2

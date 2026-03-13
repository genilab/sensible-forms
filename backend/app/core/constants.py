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

# Chat-style assistant defaults
LLM_TEMPERATURE_CHAT: float = 0.5

# Orchestration-style nodes should be more deterministic and short.
LLM_TEMPERATURE_ORCHESTRATOR: float = 0.1

# Max output tokens for common node types.
LLM_MAX_OUTPUT_TOKENS_CHAT: int = 3056
LLM_MAX_OUTPUT_TOKENS_ORCHESTRATOR: int = 256

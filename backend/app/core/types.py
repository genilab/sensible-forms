"""
Shared System-Wide Types.

Contains reusable data structures and enumerations
that are shared across multiple domains.

Only types that are not owned by a specific domain
should be defined here.
"""

"""
After initial integration, this file may be empty or contain only a few shared types. That's expected.
We can expand upon this file as the system grows and we identify common types that are used across multiple domains.
"""

# Example Code:
from enum import Enum


class LLMProvider(str, Enum):
    GEMINI = "gemini"

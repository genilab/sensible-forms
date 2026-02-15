"""
LLM Client Abstraction

Defines a provider-agnostic interface for interacting with
large language models.

This file ensures:
- The rest of the application does NOT depend on a specific LLM vendor
- We can swap providers (Gemini, OpenAI, Anthropic, etc.)
  without rewriting business logic
- Consistent error handling and response normalization

This layer should contain ZERO domain logic.
"""

# Example Code:
from abc import ABC, abstractmethod
from typing import Any, Optional

class LLMClient(ABC):
    @abstractmethod
    def invoke(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate text from a given prompt.

        Parameters:
            prompt (str): The input text prompt
            temperature (float): Controls randomness
            max_tokens (Optional[int]): Maximum tokens to generate
            **kwargs: Provider-specific parameters

        Returns:
            str: Generated model output
        """
        raise NotImplementedError
"""LangGraph checkpointer factory.

This module centralizes how graphs persist and restore state.

For now, we use an in-memory checkpointer to keep the example repo simple.
You can later swap this to SQLite/Postgres/Redis by changing this file only.
"""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def get_checkpointer():
    try:
        from langgraph.checkpoint.memory import MemorySaver
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "LangGraph is required for checkpointing. Install it with: pip install langgraph."
        ) from e

    return MemorySaver()
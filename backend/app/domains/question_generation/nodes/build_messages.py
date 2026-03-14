from __future__ import annotations

from typing import Any, Dict

from app.domains.question_generation.prompts import SYSTEM_PROMPT


def build_messages(state: Dict[str, Any]) -> Dict[str, Any]:
    topic = (state.get("topic") or "").strip()
    system = SYSTEM_PROMPT.strip() if isinstance(SYSTEM_PROMPT, str) else str(SYSTEM_PROMPT)
    existing_messages = state.get("messages") or []

    user = f"Topic: {topic}" if topic else "Topic: (missing)"

    messages = []
    if not existing_messages:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})

    return {"messages": messages}

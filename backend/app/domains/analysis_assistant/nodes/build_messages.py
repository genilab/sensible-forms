from __future__ import annotations

from typing import Any, Dict

from app.domains.analysis_assistant.prompts import SYSTEM_PROMPT


def build_messages(state: Dict[str, Any]) -> Dict[str, Any]:
    data_summary = (state.get("data_summary") or "").strip()
    existing_messages = state.get("messages") or []

    prompt = (
        "Survey summary:\n"
        f"{data_summary}\n\n"
        "Return 3-5 concise insights as bullet points."
    )

    messages = []
    if not existing_messages:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
    messages.append({"role": "user", "content": prompt})

    return {"messages": messages}

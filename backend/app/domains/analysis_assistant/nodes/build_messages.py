from __future__ import annotations

import json
from typing import Any, Dict

from app.domains.analysis_assistant.prompts import (
    SYSTEM_PROMPT,
    build_legacy_summary_user_prompt,
    build_no_dataset_user_prompt,
    build_uploaded_dataset_user_prompt,
)


def build_messages(state: Dict[str, Any]) -> Dict[str, Any]:
    data_summary = (state.get("data_summary") or "").strip()
    user_message = (state.get("user_message") or "").strip()
    dataset_profile = state.get("dataset_profile")
    active_file_id = (state.get("active_file_id") or "").strip()
    existing_messages = state.get("messages") or []

    has_profile = isinstance(dataset_profile, dict) and len(dataset_profile) > 0
    has_dataset = has_profile or bool(active_file_id)

    if has_dataset:
        profile_text = "(none)"
        if isinstance(dataset_profile, dict):
            # Compact JSON to keep context small.
            profile_text = json.dumps(dataset_profile, ensure_ascii=False)

        prompt = build_uploaded_dataset_user_prompt(
            profile_json=profile_text,
            user_message=user_message,
        )
    elif user_message:
        # Chat was invoked without an uploaded dataset.
        prompt = build_no_dataset_user_prompt(user_message=user_message)
    else:
        # Legacy path: analyze a user-provided freeform summary string.
        prompt = build_legacy_summary_user_prompt(data_summary=data_summary)

    # Preserve conversation history across turns.
    messages = list(existing_messages)

    # Ensure the system prompt is present for consistent behavior, even when
    # restoring from a checkpoint that doesn't include it.
    has_system = any(isinstance(m, dict) and m.get("role") == "system" for m in messages)
    if not has_system:
        messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})

    messages.append({"role": "user", "content": prompt})

    return {"messages": messages}

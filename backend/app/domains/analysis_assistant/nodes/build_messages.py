from __future__ import annotations

import json
from typing import Any, Dict

from app.domains.analysis_assistant.prompts import (
    SYSTEM_PROMPT,
    build_legacy_summary_user_prompt,
    build_no_dataset_user_prompt,
    build_uploaded_dataset_followup_user_prompt,
    build_uploaded_dataset_user_prompt,
)


def build_messages(state: Dict[str, Any]) -> Dict[str, Any]:
    """Construct the chat `messages` list for the LLM.

    This node is responsible for translating the current graph state into the
    exact prompt the model sees.

    Inputs it may use:
    - `dataset_profile`: compact dataset summary dict (preferred)
    - `active_file_id`: indicates that a dataset exists even if no profile was built yet
    - `user_message`: the current user turn
    - `data_summary`: legacy freeform summary (rare)

    Output:
    - `messages`: list of {role, content} dicts suitable for `LLMClient.invoke_llm()`.
    """

    # Pull state fields and normalize them.
    data_summary = (state.get("data_summary") or "").strip()
    user_message = (state.get("user_message") or "").strip()
    dataset_profile = state.get("dataset_profile")
    active_file_id = (state.get("active_file_id") or "").strip()

    # `messages` is persisted across turns via checkpointing; we append onto it.
    existing_messages = state.get("messages") or []

    # Upload-mode is the "intro" path where we intentionally produce a fuller
    # dataset snapshot + suggested next analyses.
    upload_mode = bool(state.get("upload_mode"))

    # Decide which prompt template to use.
    # If we have a dataset profile (or at least an active file), we use the
    # dataset-aware prompt that grounds the model in column names and summaries.
    has_profile = isinstance(dataset_profile, dict) and len(dataset_profile) > 0
    has_dataset = has_profile or bool(active_file_id)

    if has_dataset:
        # Compact JSON keeps context smaller and reduces the chance of truncation.
        profile_text = "(none)"
        if isinstance(dataset_profile, dict):
            profile_text = json.dumps(dataset_profile, ensure_ascii=False)

        if upload_mode:
            prompt = build_uploaded_dataset_user_prompt(
                profile_json=profile_text,
                user_message=user_message,
            )
        else:
            prompt = build_uploaded_dataset_followup_user_prompt(
                profile_json=profile_text,
                user_message=user_message,
            )
    elif user_message:
        # Chat was invoked without an uploaded dataset. We still provide helpful guidance.
        prompt = build_no_dataset_user_prompt(user_message=user_message)
    else:
        # Legacy path: analyze a user-provided freeform summary string.
        prompt = build_legacy_summary_user_prompt(data_summary=data_summary)

    # Preserve conversation history across turns.
    messages = list(existing_messages)

    # Ensure the system prompt is present.
    # Why: depending on checkpoint state and how nodes were upgraded over time,
    # we can't assume the restored message list always begins with a system message.
    has_system = any(isinstance(m, dict) and m.get("role") == "system" for m in messages)
    if not has_system:
        messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})

    # Append the constructed prompt as the next user turn.
    messages.append({"role": "user", "content": prompt})

    # LangGraph merges this into state; downstream nodes read `messages`.
    return {"messages": messages}

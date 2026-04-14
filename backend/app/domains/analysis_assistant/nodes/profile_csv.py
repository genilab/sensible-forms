from __future__ import annotations

from typing import Any

from app.domains.analysis_assistant.file_store import load_file
from app.domains.analysis_assistant.prompts import build_default_upload_user_message
from app.domains.analysis_assistant.tools import build_profile, read_csv_bytes


def profile_csv(state: dict[str, Any]) -> dict[str, Any]:
    file_id = (state.get("active_file_id") or "").strip()
    if not file_id:
        raise ValueError("active_file_id is required in upload_mode")

    file_bytes = load_file(file_id)
    df = read_csv_bytes(file_bytes)
    profile = build_profile(df).to_compact_dict()

    # If this call was an upload-triggered event, provide a default user message.
    user_message = (state.get("user_message") or "").strip()
    if not user_message:
        user_message = build_default_upload_user_message()

    return {"dataset_profile": profile, "user_message": user_message}

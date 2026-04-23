from __future__ import annotations

from typing import Any

from app.domains.analysis_assistant.file_store import load_file
from app.domains.analysis_assistant.prompts import build_default_upload_user_message
from app.domains.analysis_assistant.tools import build_profile, read_csv_bytes


def profile_csv(state: dict[str, Any]) -> dict[str, Any]:
    """Build a compact dataset profile from the uploaded CSV.

    This node is only used when `upload_mode=True`.

    Inputs (required):
    - `active_file_id`: identifier returned by the upload endpoint

    Outputs:
    - `dataset_profile`: compact dict (no raw rows)
    - `user_message`: ensured non-empty (defaults to an upload-oriented prompt)
    """

    file_id = (state.get("active_file_id") or "").strip()
    if not file_id:
        # In upload_mode we *must* have an active file to profile.
        raise ValueError("active_file_id is required in upload_mode")

    # Retrieve uploaded bytes from the domain file store.
    file_bytes = load_file(file_id)

    # Parse the CSV into a DataFrame (enforces a conservative max row limit).
    df = read_csv_bytes(file_bytes)

    # Build a compact, JSON-friendly profile with column kinds, missingness, top values, etc.
    profile = build_profile(df).to_compact_dict()

    # Upload-triggered runs may not include a user message; supply a helpful default.
    user_message = (state.get("user_message") or "").strip()
    if not user_message:
        user_message = build_default_upload_user_message()

    # Return partial state updates; LangGraph merges these into the global state.
    return {"dataset_profile": profile, "user_message": user_message}

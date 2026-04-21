from __future__ import annotations

from typing import Any, Dict

from app.domains.form_deployment.prompts import SYSTEM_PROMPT


def build_messages(state: Dict[str, Any]) -> Dict[str, Any]:
    msg = (state.get("message") or "").strip()
    existing_messages = state.get("messages") or []

    context = (
        "Last deterministic deploy attempt:\n"
        f"- filename: {state.get('last_deploy_filename') or 'null'}\n"
        f"- status: {state.get('last_deploy_status') or 'null'}\n"
        f"- formId: {state.get('last_deploy_formId') or 'null'}\n"
        f"- feedback: {state.get('last_deploy_feedback') or 'null'}\n"
        
        "Last deterministic retrieve attempt:\n"
        f"- formId: {state.get('last_retrieve_formId') or 'null'}"
        f"- status: {state.get('last_retrieve_status') or 'null'}"
        f"- feedback: {state.get('last_retrieve_feedback') or 'null'}"
    )

    prompt = (
        f"{context}\n"
        f"User question: {msg}\n\n"
        "Answer:"
    )

    messages = []
    if not existing_messages:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
    messages.append({"role": "user", "content": prompt})

    return {"messages": messages}

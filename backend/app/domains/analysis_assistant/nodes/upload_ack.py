from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from app.domains.analysis_assistant.nodes.state import State
from app.domains.analysis_assistant.prompts import (
    UPLOAD_ACK_DATASET_READY_TEMPLATE,
    UPLOAD_ACK_FILE_BULLET_TEMPLATE,
    UPLOAD_ACK_HAVE_ACCESS_TEMPLATE,
    UPLOAD_ACK_LINK_SUGGESTION,
    UPLOAD_ACK_THANKS_GENERIC,
    UPLOAD_ACK_THANKS_TEMPLATE,
    UPLOAD_ACK_UNLABELED_HINT,
)


def upload_ack(state: State):
    """Finalize upload mode by returning a deterministic acknowledgement.

    Important: if an upstream ingestion step already produced an AIMessage with
    plain text (e.g., a clarifying question), we do NOT append a new ack message
    that would hide it; we only clear `mode`.
    """

    messages = state.get("messages", [])
    csv_data = state.get("csv_data", [])
    datasets = state.get("datasets", [])

    last_human_msg = next(
        (m for m in reversed(messages or []) if isinstance(m, HumanMessage)), None
    )
    last_user_prompt = (
        last_human_msg.content if last_human_msg is not None else state.get("last_user_prompt") # (Fallback) Last user prompt may be in state due to checkpointing, if this is not the first run of the graph for this thread.
    )

    last_id = state.get("last_uploaded_csv_id")
    last_csv = next((c for c in csv_data if c.id == last_id), None)
    if last_csv is None and csv_data:
        last_csv = csv_data[-1]

    # If upstream already emitted a plain-text AI message and we don't have a
    # concrete uploaded CSV to acknowledge, don't append an acknowledgement that
    # would hide that message.
    if last_csv is None and messages:
        last_message = messages[-1]
        if isinstance(last_message, AIMessage) and not getattr(last_message, "tool_calls", None):
            return {"mode": None, "last_user_prompt": last_user_prompt}

    # If we've already acknowledged *this exact upload id* (e.g., due to retries),
    # don't append another acknowledgement.
    #
    # Important nuance with checkpointing: `messages` contains prior runs. We must NOT
    # suppress acknowledgements just because the last AI message is some earlier chat
    # response (which would cause the API to re-surface that old message).
    if last_id and messages:
        last_message = messages[-1]
        if isinstance(last_message, AIMessage) and not getattr(last_message, "tool_calls", None):
            content = getattr(last_message, "content", None)
            if isinstance(content, str) and ("uploaded" in content.lower()) and (last_id in content):
                return {"mode": None, "last_user_prompt": last_user_prompt}

    label = getattr(last_csv, "label", None) if last_csv else None
    label_display = label or "Unlabeled CSV"
    rows = last_csv.num_rows if last_csv else 0
    cols = len(last_csv.columns or []) if last_csv else 0

    lines = [
        (
            UPLOAD_ACK_THANKS_TEMPLATE.format(
                label_display=label_display,
                csv_id=last_csv.id,
                rows=rows,
                cols=cols,
            )
            if last_csv
            else UPLOAD_ACK_THANKS_GENERIC
        )
    ]

    if len(csv_data) > 1:
        lines.append(UPLOAD_ACK_HAVE_ACCESS_TEMPLATE.format(count=len(csv_data)))
        for c in csv_data:
            l = getattr(c, "label", None) or "Unlabeled CSV"
            lines.append(
                UPLOAD_ACK_FILE_BULLET_TEMPLATE.format(
                    label=l,
                    csv_id=c.id,
                    rows=c.num_rows,
                    cols=len(c.columns or []),
                )
            )
        # Blank line to end the Markdown list cleanly.
        lines.append("")

    unlabeled_now = [c for c in csv_data if not getattr(c, "label", None)]
    if unlabeled_now:
        lines.append(UPLOAD_ACK_UNLABELED_HINT)

    if datasets:
        lines.append(UPLOAD_ACK_DATASET_READY_TEMPLATE.format(dataset_id=datasets[-1].id))
    else:
        if len(csv_data) >= 2:
            lines.append(UPLOAD_ACK_LINK_SUGGESTION)

    return {
        "messages": [AIMessage(content="\n".join(lines))],
        "mode": None,
        "last_user_prompt": last_user_prompt,
    }

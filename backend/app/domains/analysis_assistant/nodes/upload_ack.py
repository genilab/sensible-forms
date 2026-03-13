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
        last_human_msg.content if last_human_msg is not None else state.get("last_user_prompt")
    )

    # If an upstream node already produced a plain AI message, keep it as the
    # final message and only clear upload mode.
    #
    # Important nuance with checkpointing: `messages` includes prior runs. We only want
    # to suppress the ack when the most recent AI message is a non-upload response
    # (e.g., a clarifying question), or when we've already acknowledged the current
    # upload id.
    if messages:
        last_message = messages[-1]
        if isinstance(last_message, AIMessage) and not getattr(last_message, "tool_calls", None):
            content = getattr(last_message, "content", None)
            if isinstance(content, str) and content.strip():
                content_lc = content.lower()
                last_id = state.get("last_uploaded_csv_id")

                # If the last AI message isn't an upload acknowledgement, keep it.
                if "uploaded" not in content_lc:
                    return {"mode": None, "last_user_prompt": last_user_prompt}

                # If it already references the current upload id, don't add another ack.
                if last_id and last_id in content:
                    return {"mode": None, "last_user_prompt": last_user_prompt}

    last_id = state.get("last_uploaded_csv_id")
    last_csv = next((c for c in csv_data if c.id == last_id), None)
    if last_csv is None and csv_data:
        last_csv = csv_data[-1]

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

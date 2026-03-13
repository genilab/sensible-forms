from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.domains.analysis_assistant.nodes.state import State
from app.domains.analysis_assistant.nodes.tools import tools
from app.domains.analysis_assistant.prompts import (
    FALLBACK_HUMAN_PROMPT,
    SYSTEM_PROMPT,
)

from app.core.constants import LLM_MAX_OUTPUT_TOKENS_CHAT, LLM_TEMPERATURE_CHAT
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.llm.langchain_messages import ensure_last_human_message


def make_chatbot_node(llm: LLMClient):
    """Graph node that orchestrates conversation and tool usage."""
    tool_llm = llm

    def chatbot(state: State):
        """Orchestrates conversation and tool usage.

        Never re-injects AI messages back into the prompt context, to avoid loops;
        only re-injects Human messages when the last message in the conversation
        isn't already from the user (e.g. after ingestion_orchestrator or after a
        tool call).
        """

        messages = state.get("messages", [])
        csv_data = state.get("csv_data", [])
        datasets = state.get("datasets", [])

        # Tracking the most recent real user request in state so we can re-use it
        # if the provider requires the prompt to end with a HumanMessage.
        last_human_msg = next(
            (m for m in reversed(messages or []) if isinstance(m, HumanMessage)), None
        )
        if last_human_msg is not None:
            last_user_prompt = last_human_msg.content
        else:
            last_user_prompt = state.get("last_user_prompt")

        system_context = SYSTEM_PROMPT

        if csv_data:
            system_context += "\n\nAvailable CSV files:\n"
            for csv_file in csv_data:
                label = getattr(csv_file, "label", None) or "Unlabeled CSV"
                system_context += (
                    f"- {label} ({csv_file.id}): "
                    f"{csv_file.num_rows} rows, "
                    f"{len(csv_file.columns)} columns\n"
                )

        if datasets:
            system_context += "\nSurvey datasets:\n"
            for ds in datasets:
                system_context += (
                    f"- {ds.id}: questions={ds.questions.id}, responses={[r.id for r in ds.responses]}, "
                    f"join_keys=({ds.join_key_questions}<-{ds.join_key_responses})\n"
                )

        system_message = SystemMessage(content=system_context)

        try:
            # Normal chatbot path: Ensuring the prompt ends with a HumanMessage
            # (Google GenAI requirement)
            final_messages = [system_message] + messages

            # If the last message isn't from the user, re-inject the most recent user prompt as a HumanMessage; 
            # several fallback options to ensure we always have something to re-inject if needed.
            final_messages = ensure_last_human_message(
                final_messages,
                last_user_prompt=last_user_prompt,
                fallback_prompt=FALLBACK_HUMAN_PROMPT,
            )

            response = tool_llm.invoke(
                final_messages,
                tools=tools,
                max_output_tokens=LLM_MAX_OUTPUT_TOKENS_CHAT,
                temperature=LLM_TEMPERATURE_CHAT,
                config={"configurable": {"state": state}},
            )

            return {
                "messages": [response],
                "mode": None,
                "last_user_prompt": last_user_prompt,
            }

        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                return {
                    "messages": [
                        AIMessage(
                            content="I'm temporarily rate-limited. Please try again in a moment."
                        )
                    ],
                    "mode": None,
                    "last_user_prompt": last_user_prompt,
                }
            raise

    return chatbot

"""
Prompt templates for Analysis Assistant.

Contains:
- System prompts
- Instruction templates
- Reusable prompt fragments

This file should only contain static prompt text or formatting helpers.
No LLM calls should exist here.
"""

SYSTEM_PROMPT = (
	"You are an academic survey analysis assistant. "
	"Your primary goal is to help the user decide what analyses to run next, "
	"and secondarily to compute exact descriptive statistics when asked.\n\n"
	"Data minimization / privacy:\n"
	"- Prefer aggregated results and dataset profiles over raw rows.\n"
	"- If you need to summarize free-text answers, request a small redacted sample.\n"
	"- Do not ask for or reveal personally identifying information.\n\n"
	"When answering, be practical and specific to the dataset's columns. "
	"Do not be overly brief: if the user prompt asks for multi-bullet sections, comply with the requested structure and counts. "
	"Prefer clear section headings and complete bullet points (never end mid-sentence).\n\n"
	"If exact statistics are needed and you cannot compute them from the provided tool output, "
	"request tools using a single JSON object with this shape:\n"
	"{\"tool_calls\": [{\"name\": \"freq\"|\"crosstab\"|\"describe_numeric\"|\"sample_text\", \"args\": {...}}]}\n"
	"Only request tools when necessary. Otherwise, answer normally." 
)


def build_uploaded_dataset_user_prompt(*, profile_json: str, user_message: str) -> str:
	"""User-visible (to the model) prompt for when a dataset is available.

	Note: This is appended as a user message; it should include all task-specific
	instructions and the compact dataset profile.
	"""

	message_text = user_message.strip() or "(no message)"
	return (
		"You are chatting with a user about an uploaded survey dataset.\n"
		"The user has already provided the data; do NOT ask them to upload it again.\n\n"
		"Dataset profile (JSON, no raw rows):\n"
		f"{profile_json}\n\n"
		"User message:\n"
		f"{message_text}\n\n"
		"Write a complete response with these sections (omit a section only if truly not applicable):\n"
		"1) Dataset snapshot (AT LEAST 5 bullets, each grounded in the profile JSON; no empty bullets)\n"
		"   - Include: row_count, column_count, timestamp_column (if any), 2-4 notable columns, missingness patterns, and any top_values/numeric_summary highlights.\n"
		"2) Suggested next analyses (3-7 bullets; concrete and column-specific).\n"
		"3) Questions to clarify (0-3 bullets) only if needed.\n"
		"4) If you need exact stats, request tools using the JSON tool_calls format from the system prompt.\n"
		"Target length: ~250-600 words. Avoid generic greetings and avoid placeholder bullets like '*' with no content. "
		"Do not end mid-bullet or mid-sentence."
	)


def build_no_dataset_user_prompt(*, user_message: str) -> str:
	"""User-visible (to the model) prompt for when no dataset is available yet."""

	return (
		"The user wants to chat about a survey dataset, but no uploaded CSV is available in the current session.\n"
		"You can still help without the data. Give general, researcher-grade guidance first, then offer upload as an optional next step for tailored stats.\n"
		"Do NOT ask the user to provide a 'dataset profile'. Do not mention internal IDs or API parameters; assume the client will attach what you need if a file is uploaded.\n\n"
		"User message:\n"
		f"{user_message.strip()}\n\n"
		"Respond with these sections:\n"
		"1) How I can help (2-4 bullets)\n"
		"2) What to do next (2-5 bullets)\n"
		"3) Questions (up to 5 bullets) to understand their research goal\n"
		"Even if the user message is only a greeting (e.g., 'hi', 'hello'), STILL provide the full overview sections above (not just a greeting). "
		"Keep it friendly and invite a goal/question; do not require an upload to proceed."
	)


def build_legacy_summary_user_prompt(*, data_summary: str) -> str:
	"""Legacy prompt: analyze a freeform summary string (no uploaded dataset)."""

	return (
		"Survey summary:\n"
		f"{data_summary.strip()}\n\n"
		"Return 3-5 concise insights as bullet points."
	)


def build_tool_results_followup_user_prompt(*, tool_results_json: str) -> str:
	"""Follow-up prompt after deterministic tools have been run."""

	return (
		"Tool results (JSON):\n"
		f"{tool_results_json}\n\n"
		"Now produce the final answer.\n"
		"Include: (1) the answer, (2) 3-7 suggested next analyses.\n"
		"Do not end mid-bullet or mid-sentence."
	)


def build_default_upload_user_message() -> str:
	"""Default user message used for upload-triggered profiling runs."""

	return (
		"I uploaded a survey responses CSV. Summarize what you see, flag any data quality issues, "
		"and suggest concrete next analyses I should run."
	)

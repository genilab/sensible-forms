from typing import Annotated, Any, List, Optional
import uuid

from langchain.tools import tool
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from app.domains.analysis_assistant.structs.surveyDataset import SurveyDataset
from app.domains.analysis_assistant.tools.utils.dataset_inference import (
    find_question_id_column,
    detect_wide_response_columns,
)

# Declares relationships between question and response CSVs, creating a SurveyDataset object.
# Establishes intentional relationships between CSVs, encoding joins without executing them, creating a SurveyDataset.

@tool
def create_survey_dataset(
    questions_csv_id: str,
    response_csv_ids: list[str],
    join_key_questions: str,
    join_key_responses: Optional[str] = None,
    responses_wide: bool = False,
    response_question_columns: Optional[List[str]] = None,
    dataset_id: Optional[str] = None,
    state: Annotated[dict, InjectedState] = None,
    runtime: Any = None,
) -> Command:
    """Create a SurveyDataset by linking a questions CSV to one or more response CSVs.

    This tool does *not* execute a join. Instead, it creates a ``SurveyDataset`` object
    that declares how questions and responses relate (join keys, wide vs long format).
    Downstream tools can then interpret responses consistently.

    Expectations:
    - CSVs must already exist in ``state["csv_data"]``.
    - The questions CSV contains a question identifier column (explicit or inferred).

    Args:
        questions_csv_id: CSV id containing question metadata.
        response_csv_ids: One or more CSV ids containing responses.
        join_key_questions: Column in the questions CSV that identifies questions.
            If invalid, the tool attempts to infer a suitable question id column.
        join_key_responses: For long/tidy response CSVs, the column that identifies the
            question id in each response row. If omitted, the tool attempts to infer.
        responses_wide: If true, treat responses as wide format (question ids are columns).
        response_question_columns: For wide responses, optional explicit list of question
            columns to treat as responses.
        dataset_id: Optional explicit dataset id. If omitted, a random id is generated.
        state: LangGraph-injected state dict.
        runtime: Tool runtime injected by LangGraph ToolNode.

    Returns:
        A ``Command`` update that adds a new dataset in ``state["datasets"]`` and a
        user-visible ``ToolMessage`` describing the result.
    """

    # ---- 1) Validate tool runtime + initialize state ----
    state = state or {}

    # ToolRuntime is always injected by ToolNode, but keep a defensive fallback
    # so this tool remains callable in isolation.
    if runtime is None:  # pragma: no cover
        raise ValueError("ToolRuntime was not injected.")

    # ---- 2) Index available CSVs by id for fast lookups ----
    csvs = {c.id: c for c in state.get("csv_data", [])}

    # ---- 3) Validate required inputs early (return ToolMessage on failure) ----
    if not questions_csv_id:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content="questions_csv_id is required; dataset not created.",
                        tool_call_id=runtime.tool_call_id,
                    )
                ]
            }
        )

    if not response_csv_ids:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content="response_csv_ids is empty; dataset not created.",
                        tool_call_id=runtime.tool_call_id,
                    )
                ]
            }
        )

    if questions_csv_id not in csvs:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"Questions CSV {questions_csv_id!r} not found; dataset not created.",
                        tool_call_id=runtime.tool_call_id,
                    )
                ]
            }
        )

    # ---- 4) Resolve CSV objects from ids ----
    questions_csv = csvs[questions_csv_id]

    # Build the responses list first so downstream inference can inspect it.
    responses = []
    for rid in response_csv_ids:
        if rid not in csvs:
            return Command(
                update={
                    "messages": [
                        ToolMessage(
                            content=f"Response CSV {rid!r} not found; dataset not created.",
                            tool_call_id=runtime.tool_call_id,
                        )
                    ]
                }
            )
        responses.append(csvs[rid])

    # ---- 5) Infer helpful defaults (question id column + likely wide-format response columns) ----
    qid_col = find_question_id_column(questions_csv.columns or [])
    detected_response_cols = detect_wide_response_columns(questions_csv, responses)

    # ---- 6) Validate/adjust join_key_questions (fallback to inferred question id column) ----
    if join_key_questions not in (questions_csv.columns or []):
        if qid_col:
            join_key_questions = qid_col
        else:
            # Cannot proceed without a valid questions key
            return Command(
                update={
                    "messages": [
                        ToolMessage(
                            content="Unable to infer join key for questions CSV; dataset not created.",
                            tool_call_id=runtime.tool_call_id,
                        )
                    ]
                }
            )

    # ---- 7) Interpret response format: wide vs long/tidy ----
    # Wide: each row is a respondent and question ids are columns.
    # Long: one row per (respondent, question) and a join key identifies the question.
    if responses_wide:
        # ---- 7a) Wide-format: validate/choose which response columns correspond to question ids ----
        cols = response_question_columns or detected_response_cols or []
        if not cols:
            # Try to infer wide-format; if still missing, do not raise — return unchanged
            return Command(
                update={
                    "messages": [
                        ToolMessage(
                            content="Unable to infer wide-format response columns; dataset not created.",
                            tool_call_id=runtime.tool_call_id,
                        )
                    ]
                }
            )
        # Ensure all responses contain these columns; if not, continue without raising
        for r in responses:
            missing_cols = [c for c in cols if c not in (r.columns or [])]
            if missing_cols:
                # If some columns are missing in a response, keep going — downstream validation can report details
                pass
        response_question_columns = cols
    else:
        # ---- 7b) Long/tidy format: ensure a join key exists in responses; infer if omitted ----
        if not join_key_responses:
            # If responses also have the questions key, reuse it
            if all(join_key_questions in (r.columns or []) for r in responses):
                join_key_responses = join_key_questions
            elif detected_response_cols:
                # Switch to wide-format if response columns match question ids
                responses_wide = True
                response_question_columns = detected_response_cols
            else:
                # Cannot infer; return unchanged to avoid hard error
                return Command(
                    update={
                        "messages": [
                            ToolMessage(
                                content="Unable to infer response join key; dataset not created.",
                                tool_call_id=runtime.tool_call_id,
                            )
                        ]
                    }
                )
        else:
            # Validate presence; if missing, try fallback to inferred question id column.
            for r in responses:
                if join_key_responses not in (r.columns or []):
                    if qid_col and qid_col in (r.columns or []):
                        join_key_responses = qid_col
                    else:
                        return Command(
                            update={
                                "messages": [
                                    ToolMessage(
                                        content=(
                                            f"Response CSV missing join key {join_key_responses!r}; dataset not created."
                                        ),
                                        tool_call_id=runtime.tool_call_id,
                                    )
                                ]
                            }
                        )

    # ---- 8) Materialize the SurveyDataset (relationships only; no joins executed here) ----
    dataset = SurveyDataset(
        id=dataset_id or f"dataset_{uuid.uuid4()}",
        questions=questions_csv,
        responses=responses,
        join_key_questions=join_key_questions,
        join_key_responses=join_key_responses,
        responses_wide=responses_wide,
        response_question_columns=response_question_columns,
    )

    # ---- 9) Return dataset update + a user-visible ToolMessage ----
    return Command(
        update={
            "datasets": [dataset],
            "messages": [
                ToolMessage(
                    content=(
                        f"Created dataset {dataset.id!r} with questions_csv_id={questions_csv_id!r} "
                        f"and {len(response_csv_ids)} response CSV(s)."
                    ),
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )

import uuid
from typing import Annotated, Any

from langchain.tools import tool
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from app.domains.analysis_assistant.structs.insights import Insight
from app.domains.analysis_assistant.tools.utils.confidence import score_response_summary


# Output safety caps and defaults.
_MIN_LIMIT = 1
_MAX_LIMIT = 5000
_DEFAULT_MAX_INSIGHTS = 250
_DEFAULT_MAX_ROWS_PER_FILE = 500

# Interprets joined survey data to extract insights.
# Performs deterministic joins internally, produces Insight objects, and attaches evidence and confidence score.


@tool
def extract_survey_insights(
    dataset_id: str,
    state: Annotated[dict, InjectedState],
    runtime: Any,
    max_insights: int = 250,
    max_rows_per_file: int = 500,
) -> Command:
    """Extract atomic response-summary insights from a SurveyDataset.

    This tool deterministically walks response rows and produces one ``Insight`` per
    observed non-empty response value (subject to caps). It supports both:
    - wide responses (question ids as columns)
    - long/tidy responses (a join key identifies the question id per row)

    Caps:
    - ``max_insights`` limits total insights returned
    - ``max_rows_per_file`` limits how many rows are scanned per response CSV
    Both are clamped to a safe range to avoid runaway output.

    Args:
        dataset_id: The id of a ``SurveyDataset`` present in ``state["datasets"]``.
        state: LangGraph-injected state dict.
        runtime: Tool runtime (used for ToolMessage tool_call_id).
        max_insights: Maximum number of insights to emit (default 250).
        max_rows_per_file: Maximum number of rows per response CSV to scan (default 500).

    Returns:
        A ``Command`` update containing:
        - ``insights``: list of ``Insight`` objects
        - ``messages``: a single ``ToolMessage`` summarizing extracted count (and whether capped)
    """

    # ---- 1) Locate the dataset in state (graceful failure, no exceptions) ----
    datasets = state.get("datasets", [])
    dataset = next((d for d in datasets if d.id == dataset_id), None)
    if dataset is None:
        # Gracefully return existing insights without raising to avoid 500s
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"No dataset found for dataset_id={dataset_id!r}.",
                        tool_call_id=runtime.tool_call_id,
                    )
                ]
            }
        )

    # ---- 2) Normalize caps to safe ranges to avoid runaway tool output ----
    max_insights = max(_MIN_LIMIT, min(int(max_insights or _DEFAULT_MAX_INSIGHTS), _MAX_LIMIT))
    max_rows_per_file = max(_MIN_LIMIT, min(int(max_rows_per_file or _DEFAULT_MAX_ROWS_PER_FILE), _MAX_LIMIT))

    # ---- 3) Accumulate Insight objects ----
    insights: list[Insight] = []

    # ---- 4) Build question lookup tables (question_id -> question row/text) ----
    # These make response processing deterministic and avoid repeated scans of the questions CSV.
    q_lookup: dict[str, dict] = {}
    q_text_lookup: dict[str, str] = {}
    if dataset.join_key_questions:
        for row in dataset.questions.rows:
            key = row.get(dataset.join_key_questions)
            if key is None:
                continue
            key_s = str(key)
            q_lookup[key_s] = row
            for k in ("question", "question_text", "text", "prompt", "label"):
                if k in row and str(row.get(k) or "").strip():
                    q_text_lookup[key_s] = str(row.get(k)).strip()
                    break

    # Track whether we stopped early due to caps.
    capped = False

    # ---- 5) Walk each response CSV and emit per-cell (wide) or per-row (long) response summaries ----
    for resp_csv in dataset.responses:
        if dataset.responses_wide:
            # ---- 5a) Wide format: columns are question IDs; each row is a respondent ----
            cols = dataset.response_question_columns or []
            for idx, row in enumerate(resp_csv.rows[:max_rows_per_file]):
                if len(insights) >= max_insights:
                    capped = True
                    break

                # Iterate each question column and create a response_summary insight when non-empty.
                for qid in cols:
                    if len(insights) >= max_insights:
                        capped = True
                        break
                    if qid not in row:
                        continue
                    response_value = row.get(qid)
                    # Skip empty values
                    if response_value is None or response_value == "":
                        continue

                    qid_s = str(qid)
                    question_row = q_lookup.get(qid_s) if q_lookup else None
                    question_text = q_text_lookup.get(qid_s)
                    confidence = score_response_summary(
                        response_value=response_value,
                        question_row=question_row,
                        source_field=qid,
                        is_wide=True,
                    )
                    # Each filled cell becomes a small, atomic Insight with evidence pointing to the CSV/row/column.
                    insights.append(
                        Insight(
                            id=str(uuid.uuid4()),
                            dataset_id=dataset.id,
                            insight_type="response_summary",
                            summary=f"Response to question {qid}: {response_value}",
                            confidence=confidence,
                            evidence={
                                "question_id": qid_s,
                                "question_text": question_text,
                                "csv_id": resp_csv.id,
                                "row_index": idx,
                                "column": qid,
                                "value": response_value,
                                "join_key_questions": dataset.join_key_questions,
                            },
                            statistics={},
                        )
                    )
        else:
            # ---- 5b) Long format: each row carries a question id via join_key_responses ----
            join_key = dataset.join_key_responses or ""
            for idx, row in enumerate(resp_csv.rows[:max_rows_per_file]):
                if len(insights) >= max_insights:
                    capped = True
                    break

                # Resolve question id from the response row; skip if missing/empty.
                qid = row.get(join_key)
                if qid is None or qid == "":
                    continue

                qid_s = str(qid)
                if q_lookup and qid_s not in q_lookup:
                    continue

                # Extract the first non-empty response value from common long-format fields.
                source_field = None
                response_value = None
                for k in ("response", "answer", "value"):
                    if k in row and row.get(k) not in (None, ""):
                        source_field = k
                        response_value = row.get(k)
                        break

                if response_value is None or response_value == "":
                    continue

                question_row = q_lookup.get(qid_s) if q_lookup else None
                question_text = q_text_lookup.get(qid_s)
                confidence = score_response_summary(
                    response_value=response_value,
                    question_row=question_row,
                    source_field=source_field,
                    is_wide=False,
                )
                # Each response row becomes one response_summary insight with evidence pointing to the source field.
                insights.append(
                    Insight(
                        id=str(uuid.uuid4()),
                        dataset_id=dataset.id,
                        insight_type="response_summary",
                        summary=f"Response to question {qid}: {response_value}",
                        confidence=confidence,
                        evidence={
                            "question_id": qid_s,
                            "question_text": question_text,
                            "csv_id": resp_csv.id,
                            "row_index": idx,
                            "field": source_field,
                            "value": response_value,
                            "columns": list(row.keys())[:25],
                            "join_keys": {
                                "question_key": dataset.join_key_questions,
                                "response_key": dataset.join_key_responses,
                            },
                        },
                        statistics={},
                    )
                )

    # ---- 6) Return a batch update: all extracted insights + a single summarizing ToolMessage ----
    return Command(
        update={
            "insights": insights,
            "messages": [
                ToolMessage(
                    content=(
                        f"Extracted {len(insights)} insights for dataset_id={dataset_id!r}."
                        + (" (capped)" if capped else "")
                    ),
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )
from __future__ import annotations

import uuid

from langchain_core.messages import HumanMessage, SystemMessage

from app.domains.analysis_assistant.nodes.state import State
from app.domains.analysis_assistant.nodes.tools import tools
from app.domains.analysis_assistant.prompts import INGESTION_ORCHESTRATOR_SYSTEM_PROMPT
from app.domains.analysis_assistant.structs.surveyDataset import SurveyDataset
from app.domains.analysis_assistant.tools.labelCSV import infer_label_for_csv
from app.domains.analysis_assistant.tools.utils.dataset_inference import (
    detect_wide_response_columns,
    find_question_id_column,
)

from app.core.constants import (
    LLM_MAX_OUTPUT_TOKENS_ORCHESTRATOR,
    LLM_TEMPERATURE_ORCHESTRATOR,
)

from app.infrastructure.llm.client import LLMClient


def _ensure_unique_label(existing_labels: set[str], base: str) -> str:
    """Helper to ensure inferred labels are unique by appending suffixes when needed."""
    if base not in existing_labels:
        return base
    i = 2
    while f"{base}_{i}" in existing_labels:
        i += 1
    return f"{base}_{i}"


def make_ingestion_orchestrator_node(llm: LLMClient):
    """Graph node that orchestrates CSV ingestion, labeling, and dataset creation."""
    tool_llm = llm

    def ingestion_orchestrator(state: State):
        """Label CSVs and (if possible) create a dataset.

        Prefers deterministic inference; uses one LLM call only when necessary.
        """

        csvs = state.get("csv_data", [])
        datasets = state.get("datasets", [])

        # ---- Deterministic pass (preferred): label + dataset creation without LLM ----
        existing_labels = {getattr(c, "label", None) for c in csvs if getattr(c, "label", None)}
        unlabeled = [c for c in csvs if not getattr(c, "label", None)]
        for c in unlabeled:
            inferred = infer_label_for_csv(c)
            if inferred:
                c.label = _ensure_unique_label(existing_labels, inferred)
                existing_labels.add(c.label)

        # Auto-create dataset when we have 1 questions + >=1 responses and none exists
        if not datasets and len(csvs) >= 2:
            questions_csv = next(
                (c for c in csvs if getattr(c, "label", None) == "questions"), None
            )
            response_csvs = [
                c
                for c in csvs
                if getattr(c, "label", None) in {"responses", "answers"}
                or str(getattr(c, "label", "")).startswith("responses")
            ]

            if questions_csv and response_csvs:
                join_key_questions = (
                    find_question_id_column(questions_csv.columns) or "question_id"
                )
                wide_cols = detect_wide_response_columns(questions_csv, response_csvs)
                if wide_cols:
                    dataset = SurveyDataset(
                        id=f"dataset_{uuid.uuid4()}",
                        questions=questions_csv,
                        responses=response_csvs,
                        join_key_questions=join_key_questions,
                        join_key_responses=None,
                        responses_wide=True,
                        response_question_columns=wide_cols,
                    )
                    return {"datasets": datasets + [dataset]}

                if all(join_key_questions in (r.columns or []) for r in response_csvs):
                    dataset = SurveyDataset(
                        id=f"dataset_{uuid.uuid4()}",
                        questions=questions_csv,
                        responses=response_csvs,
                        join_key_questions=join_key_questions,
                        join_key_responses=join_key_questions,
                        responses_wide=False,
                        response_question_columns=None,
                    )
                    return {"datasets": datasets + [dataset]}

        # If nothing left to do, skip LLM
        unlabeled = [c for c in csvs if not getattr(c, "label", None)]
        needs_dataset = len(csvs) >= 2 and not datasets

        # In upload flows, keep ingestion deterministic and avoid an immediate LLM call.
        # The upload_ack node will confirm receipt and can prompt the user for clarification.
        if state.get("mode") == "upload":
            return {}

        if not unlabeled and not needs_dataset:
            return {}

        sys = INGESTION_ORCHESTRATOR_SYSTEM_PROMPT

        # Overlap-based candidate keys
        col_sets = [set(c.columns or []) for c in csvs]
        overlaps: set[str] = set()
        for i in range(len(col_sets)):
            for j in range(i + 1, len(col_sets)):
                overlaps |= col_sets[i] & col_sets[j]
        priority = ["question_id", "qid", "questionId", "id"]
        prioritized = [k for k in priority if k in overlaps]
        other = [k for k in overlaps if k not in prioritized]
        candidate_keys = (prioritized + sorted(other))[:5]

        # Trimmed CSV previews
        ctx = "CSV files (trimmed):\n"
        for c in csvs:
            cols_preview = (c.columns or [])[:5]
            ctx += (
                f"- {c.id}: rows={len(c.rows)}, cols={cols_preview} "
                f"(+{max(0, (len(c.columns or []) - len(cols_preview)))})\n"
            )
        if candidate_keys:
            ctx += f"Candidate join keys (overlap): {candidate_keys}\n"

        # Detect wide-format candidates based on question IDs
        q_id_col = next(
            (
                k
                for k in ["question_id", "qid", "questionId"]
                if any(k in (c.columns or []) for c in csvs)
            ),
            None,
        )
        qids: set[str] = set()
        q_csvs = []
        if q_id_col:
            q_csvs = [c for c in csvs if q_id_col in (c.columns or [])]
            if q_csvs:
                for row in q_csvs[0].rows[:100]:
                    qid = row.get(q_id_col)
                    if qid:
                        qids.add(str(qid))

        wide_candidates: dict[str, list[str]] = {}
        if qids and q_csvs:
            ctx += (
                f"Question IDs sample (from questions CSV '{q_csvs[0].id}'): "
                f"{list(sorted(qids))[:10]}\n"
            )
            for c in csvs:
                matches = [col for col in (c.columns or []) if col in qids]
                if matches:
                    wide_candidates[c.id] = matches[:10]

        if wide_candidates:
            ctx += f"Wide-format candidates: {wide_candidates}\n"

        # Also list response column previews for non-wide candidates
        for c in csvs:
            if c.id not in wide_candidates:
                cols_preview = (c.columns or [])[:10]
                ctx += f"Response columns preview for {c.id}: {cols_preview}\n"

        # Explicitly list unlabeled CSVs with basic previews to encourage labeling
        if unlabeled:
            ctx += "Unlabeled CSVs:\n"
            for c in unlabeled:
                cols_preview = (c.columns or [])[:5]
                ctx += (
                    f"- {c.id}: rows={len(c.rows)}, cols={cols_preview} "
                    f"(+{max(0, (len(c.columns or []) - len(cols_preview)))})\n"
                )

        messages = [
            SystemMessage(content=sys),
            HumanMessage(
                content=(
                    ctx
                    + "\nActions: "
                    + "1) If confident from the previews, call label_csv for unlabeled CSVs; otherwise, ask the user for clarification, but prioritize labeling with label_csv. "
                    + "2) If multiple CSVs belong to the same survey, call create_survey_dataset and set: "
                    + "   - join_key_questions: the exact column in questions with the identifiers. "
                    + "   - responses_wide + response_question_columns: when response columns represent questions. "
                    + "   - OR join_key_responses: the exact column in responses that contains the question identifier per row. "
                    + "Prefer wide-format when both patterns exist."
                )
            ),
        ]

        response = tool_llm.invoke(
            messages,
            tools=tools,
            max_output_tokens=LLM_MAX_OUTPUT_TOKENS_ORCHESTRATOR,
            temperature=LLM_TEMPERATURE_ORCHESTRATOR,
            config={"configurable": {"state": state}},
        )

        return {"messages": [response]}

    return ingestion_orchestrator

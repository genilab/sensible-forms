from __future__ import annotations

import uuid

from app.domains.analysis_assistant.nodes.state import State
from app.domains.analysis_assistant.structs.surveyDataset import SurveyDataset
from app.domains.analysis_assistant.tools.labelCSV import infer_label_for_csv
from app.domains.analysis_assistant.tools.utils.dataset_inference import (
    detect_wide_response_columns,
    find_question_id_column,
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

    def ingestion_orchestrator(state: State):
        """Label CSVs and (if possible) create a dataset.

        Prefers deterministic inference; uses one LLM call only when necessary.
        """

        csvs = state.get("csv_data", [])
        datasets = state.get("datasets", [])

        # ---- Deterministic pass (preferred): label + dataset creation without LLM ----
        existing_labels = {getattr(c, "label", None) for c in csvs if getattr(c, "label", None)}
        labels_changed = False
        unlabeled = [c for c in csvs if not getattr(c, "label", None)]
        for c in unlabeled:
            inferred = infer_label_for_csv(c)
            if inferred:
                new_label = _ensure_unique_label(existing_labels, inferred)
                if getattr(c, "label", None) != new_label:
                    labels_changed = True
                c.label = new_label
                existing_labels.add(c.label)

        # Auto-create dataset when we have 1 questions + >=1 responses and none exists
        if not datasets and len(csvs) >= 2:
            questions_csv = next(
                (c for c in csvs if getattr(c, "label", None) == "questions"), None
            )
            response_csvs = [
                c
                for c in csvs
                if (getattr(c, "label", None) == "responses")
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
                    return {"csv_data": csvs, "datasets": datasets + [dataset]}

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
                    return {"csv_data": csvs, "datasets": datasets + [dataset]}

        # Deterministic labeling may have updated CSVFile objects in-place.
        # Return the updated list explicitly so state merges/checkpointing reliably reflect the changes.
        return {"csv_data": csvs} if labels_changed else {}

    return ingestion_orchestrator

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from app.domains.analysis_assistant.structs.csvFile import CSVFile
from app.domains.analysis_assistant.structs.surveyDataset import SurveyDataset
from app.domains.analysis_assistant.structs.insights import Insight


class State(TypedDict):
    messages: Annotated[list, add_messages]
    csv_data: list[CSVFile]
    datasets: Annotated[list[SurveyDataset], operator.add]
    csv_text: str | None
    insights: Annotated[list[Insight], operator.add]
    mode: str | None
    last_uploaded_csv_id: str | None
    last_user_prompt: str | None

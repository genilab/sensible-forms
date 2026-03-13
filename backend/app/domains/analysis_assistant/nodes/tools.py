"""Tool registry for the Analysis Assistant routed graph.

This module intentionally contains *no* LLM construction logic.
It only exposes the set of LangChain tools that can be bound to the active
LLM client.
"""

from app.domains.analysis_assistant.tools.aggregateCategoricalInsight import (
    aggregate_categorical_question_insight,
)
from app.domains.analysis_assistant.tools.aggregateNumericInsight import (
    aggregate_numeric_question_insight,
)
from app.domains.analysis_assistant.tools.createSurveyDataset import create_survey_dataset
from app.domains.analysis_assistant.tools.describeCSVs import describe_csv
from app.domains.analysis_assistant.tools.extractSurveyInsights import extract_survey_insights
from app.domains.analysis_assistant.tools.labelCSV import label_csv
from app.domains.analysis_assistant.tools.listCSVs import list_csvs
from app.domains.analysis_assistant.tools.numAggregation import (
    aggregate_column,
    aggregate_column_multi,
)
from app.domains.analysis_assistant.tools.sampleRows import sample_rows


tools = [
    describe_csv,
    sample_rows,
    list_csvs,
    aggregate_column,
    aggregate_column_multi,
    aggregate_numeric_question_insight,
    aggregate_categorical_question_insight,
    label_csv,
    create_survey_dataset,
    extract_survey_insights,
]

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from app.domains.analysis_assistant.structs.csvFile import CSVFile

@dataclass
class SurveyDataset:
    id: str
    questions: CSVFile
    responses: List[CSVFile]
    join_key_questions: str
    join_key_responses: Optional[str]
    responses_wide: bool = False
    response_question_columns: Optional[List[str]] = None

    def validate(self) -> Dict[str, Any]:
        missing = []
        # Validate question join key exists in questions CSV
        questions_key_missing = self.join_key_questions not in (self.questions.columns or [])

        if self.responses_wide:
            cols = self.response_question_columns or []
            for r in self.responses:
                for c in cols:
                    if c not in (r.columns or []):
                        missing.append(f"{r.id}:{c}")
        else:
            for r in self.responses:
                if not self.join_key_responses or self.join_key_responses not in (r.columns or []):
                    missing.append(r.id)

        return {
            "valid": not missing and not questions_key_missing,
            "missing_join_key": missing,
            "missing_questions_key": questions_key_missing,
        }

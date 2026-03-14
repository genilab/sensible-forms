from __future__ import annotations

from typing import Any, Dict, List


def parse_questions(state: Dict[str, Any]) -> Dict[str, Any]:
    raw = state.get("raw_response")
    if not isinstance(raw, str):
        raw = ""

    questions: List[str] = [
        line.strip("- ") for line in raw.splitlines() if line.strip()
    ]

    return {"questions": questions}

from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class CSVFile:
    id: str
    rows: List[Dict[str, Any]]
    columns: List[str]
    label: str | None = None

    @property
    def num_rows(self) -> int:
        return len(self.rows)

    def sample(self, n=5):
        return self.rows[:n]

    def column_values(self, col: str):
        return [r[col] for r in self.rows if col in r]

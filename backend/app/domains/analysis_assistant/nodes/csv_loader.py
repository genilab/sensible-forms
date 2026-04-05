from __future__ import annotations

import csv
import uuid

from app.domains.analysis_assistant.structs.csvFile import CSVFile
from app.domains.analysis_assistant.nodes.state import State
from app.infrastructure.logging.logger import logger


def csv_loader(state: State):
    """Graph node that loads CSV text into structured CSVFile objects in state."""
    csv_text = state.get("csv_text")
    if not csv_text:
        return {}

    reader = csv.DictReader(csv_text.splitlines())
    rows = list(reader)

    existing = state.get("csv_data") or []

    csv_file = CSVFile(
        id=f"csv_{uuid.uuid4()}",
        rows=rows,
        columns=reader.fieldnames,
    )

    logger.debug("csv_loader processed CSV", extra={"csv_count": len(existing) + 1})

    return {
        "csv_data": existing + [csv_file],
        "csv_text": None,
        "mode": "upload",   # Set mode to 'upload' to indicate we're in an upload flow, which can influence routing and node behavior downstream.
        "last_uploaded_csv_id": csv_file.id,
    }

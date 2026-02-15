"""
File Validation Middleware.

Responsible for:
- Validating uploaded file types
- Enforcing file size limits
- Performing basic safety checks
- Rejecting invalid or unsafe uploads

Does not contain storage logic.
"""

# Example Code:
from __future__ import annotations

import csv
import io


def validate_csv_file(
    filename: str,
    *,
    file_size_bytes: int | None = None,
    max_size_bytes: int = 5_000_000,
):
    if not filename.lower().endswith(".csv"):
        raise ValueError("Only .csv files are allowed.")
    if file_size_bytes is not None and file_size_bytes > max_size_bytes:
        raise ValueError(f"File too large. Max size is {max_size_bytes} bytes.")


def validate_csv_required_columns(
    file_bytes: bytes,
    *,
    required_columns: list[str],
    encoding: str = "utf-8",
) -> None:
    """Validate a CSV has a header row containing required columns.

    Raises:
        ValueError: When the CSV is empty, has no header row, or is missing required columns.
    """

    if not file_bytes:
        raise ValueError("Uploaded CSV is empty. Add a header row and at least one question.")

    text = file_bytes.decode(encoding, errors="replace")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header:
        raise ValueError(
            "Could not read a header row. Ensure the CSV is comma-delimited with a first-row header."
        )

    normalized = [h.strip().lower() for h in header if h is not None]
    missing = [col for col in required_columns if col.lower() not in normalized]
    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing)
            + ". Expected at least: "
            + ", ".join(required_columns)
            + "."
        )

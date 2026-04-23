from __future__ import annotations

import io

import pandas as pd


DEFAULT_CSV_ENCODING = "utf-8"
DEFAULT_MAX_CSV_ROWS = 500


def read_csv_bytes(
    file_bytes: bytes,
    *,
    encoding: str = DEFAULT_CSV_ENCODING,
    max_rows: int = DEFAULT_MAX_CSV_ROWS,
) -> pd.DataFrame:
    """Read a CSV from bytes with a conservative row limit."""

    if not file_bytes:
        raise ValueError("Uploaded CSV is empty.")

    text = file_bytes.decode(encoding, errors="replace")
    df = pd.read_csv(io.StringIO(text))

    if df.shape[0] > max_rows:
        raise ValueError(
            f"CSV has {df.shape[0]} rows; this assistant supports up to {max_rows} rows."
        )

    df.columns = [str(c).strip() for c in df.columns]
    return df

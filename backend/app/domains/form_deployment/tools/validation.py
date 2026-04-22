"""
File Deployment Middleware / Tools.

Responsible for:
- Validating uploaded file parameters
"""

from __future__ import annotations

import io
import pandas as pd
import numpy as np


# Form Deployment Questions CSV check
def form_deployment_check_questions_csv_tool(
    file_bytes: bytes,
    *,
    encoding: str = "utf-8",
) -> None:
    """Checks if a CSV file format is correct after the user enters 'Check File'."""
    if not file_bytes:
        raise ValueError("Uploaded CSV is empty. Add a header row and at least one question.")

    text = file_bytes.decode(encoding, errors="replace")
    data = pd.read_csv(io.StringIO(text))
    errors = []

    # 1. Confirm data is in state - critical
    if data.empty:
        errors.append("\nNo CSV file uploaded.\n")

    else:
        df = data.replace(['', '#'], np.nan).infer_objects() # Normalize empty strings to np.nan for consistent handling and fix FutureWarning

        # 2. Confirm columns exist in dataframe - critical
        columns = df.columns.tolist() if not df.empty else [] # Handle empty DataFrame
        if not columns:
            errors.append("\nNo columns detected in CSV.\n")

        # 3. Check column names - critical
        valid_columns = ["question_id", "question_text", "question_type", "response_options", "is_other", "choice_type", "scale_min", "scale_max", "scale_min_label", "scale_max_label", "required"]
        if columns != valid_columns:
            invalid_columns = [col for col in columns if col not in valid_columns]
            errors.append(f"""
            CSV columns are incorrect.
            The correct columns are: {", ".join(valid_columns)}
            The current invalid columns are: {", ".join(invalid_columns)}
            """)

        # Only proceed with further checks if critical errors have not occurred
        if not errors:

            # 4. Check for valid question types
            valid_types = ["choiceQuestion", "textQuestion", "scaleQuestion", "dateQuestion", "timeQuestion"]
            if not df["question_type"].isin(valid_types).all():
                invalid_rows = df[~df["question_type"].isin(valid_types)].index.tolist()
                invalid_types = df.loc[invalid_rows, 'question_type'].tolist()
                errors.append(f"""
                Invalid question types detected.
                The correct question types are: {", ".join(valid_types)}
                The current invalid rows are: {", ".join(map(str, invalid_rows))}
                The current invalid question types are: {", ".join(map(str, invalid_types))}
                """)

            # 5. Check for ;-separated response_options (ignoring NaN/empty entries)
            if df['response_options'].notna().any() and not df['response_options'].dropna().apply(lambda x: ';' in str(x)).all():
                invalid_rows = df[df['response_options'].notna() & ~df['response_options'].apply(lambda x: ';' in str(x))].index.tolist()
                invalid_responses = df.loc[invalid_rows, 'response_options'].tolist()
                errors.append(f"""
                Response options are incorrectly formatted.
                Valid response options must be separated by semicolons if provided.
                The current invalid rows are: {", ".join(map(str, invalid_rows))}
                The current invalid response options are: {", ".join(map(str, invalid_responses))}
                """)

            # 6. Check for valid is_other entry (ignoring NaN/empty entries)
            valid_is_other_values = ['true', 'false', '1', '0', '1.0', '0.0']
            invalid_required_rows = df[df['is_other'].notna() & ~df['is_other'].astype(str).str.lower().isin(valid_is_other_values)]
            if not invalid_required_rows.empty:
                invalid_rows_idx = invalid_required_rows.index.tolist()
                invalid_values = invalid_required_rows['is_other'].tolist()
                errors.append(f"""
                Invalid values detected in 'is_other' column.
                Valid values must be boolean (True/False) or interpretable as such (e.g. {", ".join(valid_is_other_values)}).
                The current invalid rows are: {", ".join(map(str, invalid_rows_idx))}
                The current invalid 'is_other' values are: {", ".join(map(str, invalid_values))}
                """)

            # 7. Check for valid choice_type entry (ignoring NaN/empty entries)
            valid_choice_type_values = ['RADIO', 'CHECKBOX', 'DROP_DOWN']
            invalid_required_rows = df[df['choice_type'].notna() & ~df['choice_type'].astype(str).isin(valid_choice_type_values)]
            if not invalid_required_rows.empty:
                invalid_rows_idx = invalid_required_rows.index.tolist()
                invalid_values = invalid_required_rows['choice_type'].tolist()
                errors.append(f"""
                Invalid values detected in 'choice_type' column.
                Valid values are: {", ".join(valid_choice_type_values)}).
                The current invalid rows are: {", ".join(map(str, invalid_rows_idx))}
                The current invalid 'choice_type' values are: {", ".join(map(str, invalid_values))}
                """)

            # 8. Check for int/float in scale_min & scale_max
            # Check if 'scale_min' can be converted to numeric (ignoring NaN)
            numeric_scale_min = pd.to_numeric(df['scale_min'], errors='coerce')
            invalid_scale_min_rows = df[numeric_scale_min.isna() & df['scale_min'].notna()]
            if not invalid_scale_min_rows.empty:
                invalid_rows_idx = invalid_scale_min_rows.index.tolist()
                invalid_values = invalid_scale_min_rows['scale_min'].tolist()
                errors.append(f"""
                Invalid scale options detected in 'scale_min'.
                Valid scale options must be numbers.
                The current invalid rows are: {", ".join(map(str, invalid_rows_idx))}
                The current invalid 'scale_min' values are: {", ".join(map(str, invalid_values))}
                """)

            # Check if 'scale_max' can be converted to numeric (ignoring NaN)
            numeric_scale_max = pd.to_numeric(df['scale_max'], errors='coerce')
            invalid_scale_max_rows = df[numeric_scale_max.isna() & df['scale_max'].notna()]
            if not invalid_scale_max_rows.empty:
                invalid_rows_idx = invalid_scale_max_rows.index.tolist()
                invalid_values = invalid_scale_max_rows['scale_max'].tolist()
                errors.append(f"""
                Invalid scale options detected in 'scale_max'.
                Valid scale options must be numbers.
                The current invalid rows are: {", ".join(map(str, invalid_rows_idx))}
                The current invalid 'scale_max' values are: {", ".join(map(str, invalid_values))}
                """)

            # 9. Check for scale_min & scale_max valid range
            # Check if 'scale_min' is in valid range [0-1]
            if not numeric_scale_min.empty and invalid_scale_min_rows.empty:
                invalid_range_min_rows = df[(numeric_scale_min.notna()) & ((numeric_scale_min < 0) | (numeric_scale_min > 1))]
                if not invalid_range_min_rows.empty:
                    invalid_rows_idx = invalid_range_min_rows.index.tolist()
                    invalid_values = invalid_range_min_rows['scale_min'].tolist()
                    errors.append(f"""
                    Invalid scale options detected in 'scale_min'.
                    Valid scale options must be between 0 and 1.
                    The current invalid rows are: {", ".join(map(str, invalid_rows_idx))}
                    The current invalid 'scale_min' values are: {", ".join(map(str, invalid_values))}
                    """)

            # Check if 'scale_max' is in valid range [2-10]
            if not numeric_scale_max.empty and invalid_scale_max_rows.empty:
                invalid_range_max_rows = df[(numeric_scale_max.notna()) & ((numeric_scale_max < 2) | (numeric_scale_max > 10))]
                if not invalid_range_max_rows.empty:
                    invalid_rows_idx = invalid_range_max_rows.index.tolist()
                    invalid_values = invalid_range_max_rows['scale_max'].tolist()
                    errors.append(f"""
                    Invalid scale options detected in 'scale_max'.
                    Valid scale options must be between 2 and 10.
                    The current invalid rows are: {", ".join(map(str, invalid_rows_idx))}
                    The current invalid 'scale_max' values are: {", ".join(map(str, invalid_values))}
                    """)

            # 10. Check for bool in 'required'
            valid_required_values = ['true', 'false', '1', '0', '1.0', '0.0']
            invalid_required_rows = df[df['required'].notna() & ~df['required'].astype(str).str.lower().isin(valid_required_values)]
            if not invalid_required_rows.empty:
                invalid_rows_idx = invalid_required_rows.index.tolist()
                invalid_values = invalid_required_rows['required'].tolist()
                errors.append(f"""
                Invalid values detected in 'required' column.
                Valid values must be boolean (True/False) or interpretable as such (e.g. {", ".join(valid_required_values)}).
                The current invalid rows are: {", ".join(map(str, invalid_rows_idx))}
                The current invalid 'required' values are: {", ".join(map(str, invalid_values))}
                """)

            # 11. Check for empty rows
            empty_rows = df[df.isnull().all(axis=1)]
            if not empty_rows.empty:
                empty_rows_idx = empty_rows.index.tolist()
                errors.append(f"""
                Empty rows detected at indices: {', '.join(map(str, empty_rows_idx))}
                """)

    if errors:
        raise ValueError("".join(errors))

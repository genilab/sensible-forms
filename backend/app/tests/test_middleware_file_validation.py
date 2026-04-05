import pytest

from app.middleware.file_validation import validate_csv_file, validate_csv_required_columns


# Middleware: validate_csv_file accepts .csv extensions case-insensitively.
def test_validate_csv_file_accepts_csv_extension():
    validate_csv_file("survey.csv")
    validate_csv_file("SURVEY.CSV")


# Middleware: validate_csv_file rejects non-CSV extensions with a clear error.
def test_validate_csv_file_rejects_non_csv_extension():
    with pytest.raises(ValueError, match=r"^Only \.csv files are allowed\.$"):
        validate_csv_file("survey.txt")


    # Middleware: validate_csv_file enforces max size when file_size_bytes is provided.
def test_validate_csv_file_enforces_max_size_when_provided():
    with pytest.raises(ValueError, match=r"^File too large\. Max size is 10 bytes\.$"):
        validate_csv_file("survey.csv", file_size_bytes=11, max_size_bytes=10)


    # Middleware: validate_csv_required_columns rejects empty uploads.
def test_validate_csv_required_columns_rejects_empty_upload():
    with pytest.raises(ValueError, match=r"Uploaded CSV is empty\."):
        validate_csv_required_columns(b"", required_columns=["a"])


    # Middleware: validate_csv_required_columns rejects payloads that lack a header row.
def test_validate_csv_required_columns_rejects_missing_header_row():
    with pytest.raises(ValueError, match=r"Could not read a header row"):
        validate_csv_required_columns(b"\n", required_columns=["a"])


    # Middleware: validate_csv_required_columns rejects uploads missing required columns.
def test_validate_csv_required_columns_rejects_missing_required_columns():
    with pytest.raises(ValueError, match=r"Missing required columns: c\."):
        validate_csv_required_columns(b"a,b\n1,2\n", required_columns=["c"])


    # Middleware: validate_csv_required_columns matches required columns case-insensitively and ignores surrounding whitespace.
def test_validate_csv_required_columns_accepts_required_columns_case_insensitive_and_trimmed():
    validate_csv_required_columns(b" A , B \n1,2\n", required_columns=["a", "b"])

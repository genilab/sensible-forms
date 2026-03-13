from __future__ import annotations

from app.domains.analysis_assistant.structs.csvFile import CSVFile
from app.domains.analysis_assistant.tools.describeCSVs import describe_csv
from app.domains.analysis_assistant.tools.listCSVs import list_csvs
from app.domains.analysis_assistant.tools.sampleRows import sample_rows


def test_sample_rows_missing_csv_returns_error_object():
    out = sample_rows.func(csv_id="missing", state={"csv_data": []}, n=5)
    assert out["csv_id"] == "missing"
    assert out["rows"] == []
    assert "not found" in out["error"].lower()


def test_sample_rows_clamps_n_and_returns_list_sample():
    csv_file = CSVFile(
        id="c1",
        columns=["a"],
        rows=[{"a": 1}, {"a": 2}, {"a": 3}],
        label=None,
    )
    state = {"csv_data": [csv_file]}

    # Negative => 0 => empty list
    assert sample_rows.func(csv_id="c1", state=state, n=-10) == []

    # None-ish => 0
    assert sample_rows.func(csv_id="c1", state=state, n=None) == []

    # Normal
    assert sample_rows.func(csv_id="c1", state=state, n=2) == [{"a": 1}, {"a": 2}]

    # Large => clamped to 50 but we only have 3
    assert sample_rows.func(csv_id="c1", state=state, n=999) == [{"a": 1}, {"a": 2}, {"a": 3}]


def test_describe_csv_missing_and_success():
    csv_file = CSVFile(id="c1", columns=["a", "b"], rows=[{"a": 1, "b": 2}], label=None)
    state = {"csv_data": [csv_file]}

    missing = describe_csv.func(csv_id="missing", state=state)
    assert missing["rows"] is None
    assert missing["columns"] is None
    assert "not found" in missing["error"].lower()

    ok = describe_csv.func(csv_id="c1", state=state)
    assert ok["csv_id"] == "c1"
    assert ok["rows"] == 1
    assert ok["columns"] == ["a", "b"]


def test_list_csvs_formats_each_csv_on_new_line():
    c1 = CSVFile(id="c1", columns=["a"], rows=[{"a": 1}], label=None)
    c2 = CSVFile(id="c2", columns=["a", "b"], rows=[{"a": 1, "b": 2}, {"a": 3, "b": 4}], label=None)
    out = list_csvs.func(state={"csv_data": [c1, c2]})
    lines = out.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("c1:")
    assert "1 rows" in lines[0]
    assert "1 columns" in lines[0]
    assert lines[1].startswith("c2:")
    assert "2 rows" in lines[1]
    assert "2 columns" in lines[1]

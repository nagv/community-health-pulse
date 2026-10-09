"""CSV validation boundary, dataset store lifecycle and analysis argument checks."""

from datetime import date

import pytest
from test_data import CSV

from backend import data
from backend.analysis import Analysis
from backend.data import InvalidDataset, validate_csv
from shared.models import Filters

HEADER = b"visit_id,visit_date,locality,age,gender,condition\n"


@pytest.mark.parametrize(
    "payload,issue",
    [
        (b"visit_id,visit_id,visit_date,locality,age,gender,condition\n", "Duplicate column"),
        (HEADER + b"v1,2026-07-01,Lakeside,8\n", "wrong number of fields"),
        (HEADER + "v1,2026-07-01,Lakeside,8,Female,Fièvre\n".encode("latin-1"), "UTF-8"),
        (HEADER + b"v1,2026-07-01,Lakeside,8,Female," + b"x" * 201 + b"\n", "200 characters"),
    ],
    ids=["duplicate-columns", "field-count", "not-utf8", "too-long"],
)
def test_csv_structure_problems_are_rejected_with_reason(payload, issue):
    with pytest.raises(InvalidDataset) as exc:
        validate_csv(payload)
    assert any(issue in message for message in exc.value.issues)


def test_blank_lines_are_skipped_and_extra_columns_dropped_with_warning():
    payload = (
        b"visit_id,visit_date,locality,age,gender,condition,notes\n"
        b"v1,2026-07-01,Lakeside,8,Female,Fever,private note\n"
        b"\n"
        b"v2,2026-07-02,Lakeside,9,Male,Skin,\n"
    )
    frame, report = validate_csv(payload)
    assert len(frame) == 2
    assert "notes" not in frame.columns
    assert any("Additional columns" in warning for warning in report.warnings)


def test_store_expires_idle_datasets_and_evicts_least_recently_used(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(data.time, "monotonic", lambda: clock[0])
    store = data.DatasetStore()
    first = store.add(CSV, "first").dataset_id
    clock[0] += 3601  # more than one idle hour
    with pytest.raises(KeyError):
        store.get(first)

    ids = []
    for i in range(9):
        clock[0] += 1
        ids.append(store.add(CSV, f"d{i}").dataset_id)
    assert len(store.items) == 8
    assert ids[0] not in store.items
    assert all(dataset_id in store.items for dataset_id in ids[1:])


def test_analysis_rejects_invalid_arguments():
    frame, _ = validate_csv(CSV)
    a = Analysis(frame)
    with pytest.raises(ValueError, match="grouping"):
        a.breakdown(Filters(), "visit_id")
    for limit in (0, 51):
        with pytest.raises(ValueError, match="Limit"):
            a.top_conditions(Filters(), limit)
    with pytest.raises(ValueError, match="daily or weekly"):
        a.trend(Filters(), "monthly")
    d = date
    with pytest.raises(ValueError, match="ordered"):
        a.compare(Filters(), d(2026, 7, 2), d(2026, 7, 1), d(2026, 7, 8), d(2026, 7, 8), "condition")
    with pytest.raises(ValueError, match="overlap"):
        a.compare(Filters(), d(2026, 7, 1), d(2026, 7, 5), d(2026, 7, 4), d(2026, 7, 8), "condition")


def test_selection_outside_dataset_has_no_previous_period():
    frame, _ = validate_csv(CSV)
    f = Filters(start_date=date(2027, 1, 1), end_date=date(2027, 1, 31))
    a = Analysis(frame)
    assert a.previous_period(f) is None
    summary = a.summary(f)
    assert summary["recorded_visits"] == 0 and summary["avg_visits_per_day"] == 0.0
    assert summary["top_condition"] is None and summary["change_pct"] is None

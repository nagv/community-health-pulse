from datetime import date

import pytest

from backend.analysis import Analysis
from backend.data import InvalidDataset, sample_csv, validate_csv
from shared.models import Filters

CSV = b"""visit_id,visit_date,locality,age,gender,condition
v1,2026-07-01,Northstead,8,Female,Respiratory
v2,2026-07-02,Northstead,40,Male,Fever
v3,2026-07-08,Lakeside,70,Female,Respiratory
v4,2026-07-08,Lakeside,30,Male,Skin
"""


def test_valid_csv_and_exact_duplicates():
    frame, report = validate_csv(CSV + b"v4,2026-07-08,Lakeside,30,Male,Skin\n")
    assert len(frame) == 4
    assert report.duplicates_removed == 1


@pytest.mark.parametrize(
    "payload",
    [
        b"a,b\n1,2\n",
        CSV.replace(b"2026-07-01", b"2026-02-30"),
        CSV.replace(b",8,", b",121,"),
        CSV.replace(b",8,", b",1.5,"),
        CSV.replace(b",Female,", b",,"),
        CSV + b"v1,2026-07-09,Lakeside,10,Male,Fever\n",
        b"visit_id,visit_date,locality,age,gender,condition\n",
    ],
)
def test_bad_csv_reports_issues(payload):
    with pytest.raises(InvalidDataset) as exc:
        validate_csv(payload)
    assert exc.value.issues


def test_upload_limits():
    with pytest.raises(InvalidDataset):
        validate_csv(b"x" * (10 * 1024 * 1024 + 1))
    with pytest.raises(InvalidDataset):
        validate_csv(CSV, max_rows=3)


def test_synthetic_data_is_reproducible():
    assert sample_csv() == sample_csv()
    df, _ = validate_csv(sample_csv())
    assert df.visit_date.nunique() == 90
    assert df.locality.nunique() == 4
    assert df.condition.nunique() == 5


def test_analytics_filters_counts_and_weekly_grouping():
    df, _ = validate_csv(CSV)
    a = Analysis(df)
    assert a.summary(Filters())["recorded_visits"] == 4
    assert a.top_conditions(Filters())[0] == {"condition": "Respiratory", "visits": 2, "share_pct": 50.0}
    assert [r["visits"] for r in a.trend(Filters(), "weekly")] == [2, 2]
    f = Filters(localities=["Lakeside"], age_bands=["65+"])
    assert a.summary(f)["recorded_visits"] == 1
    assert a.records(f, 1, 25)["total"] == 1


def test_period_comparison_and_zero_baseline():
    df, _ = validate_csv(CSV)
    a = Analysis(df)
    rows = a.compare(
        Filters(), date(2026, 7, 1), date(2026, 7, 7), date(2026, 7, 8), date(2026, 7, 14), "condition"
    )
    skin = next(r for r in rows if r["condition"] == "Skin")
    assert skin["previous_visits"] == 0 and skin["current_visits"] == 1
    assert skin["change_pct"] is None
    assert skin["previous_share_pct"] == 0 and skin["current_share_pct"] == 50
    with pytest.raises(ValueError):
        a.compare(
            Filters(), date(2026, 7, 8), date(2026, 7, 1), date(2026, 7, 8), date(2026, 7, 9), "condition"
        )


def test_empty_selection_and_zero_filled_dates():
    df, _ = validate_csv(CSV)
    a = Analysis(df)
    f = Filters(start_date=date(2026, 7, 3), end_date=date(2026, 7, 7))
    assert a.summary(f)["recorded_visits"] == 0
    assert all(r["visits"] == 0 for r in a.trend(f, "daily"))
    assert a.top_conditions(f) == []
    assert a.records(f, 1, 25)["rows"] == []


def test_filters_reject_reversed_dates():
    with pytest.raises(ValueError):
        Filters(start_date=date(2026, 8, 1), end_date=date(2026, 7, 1))


def test_extreme_date_filters_are_clipped_to_dataset():
    df, _ = validate_csv(CSV)
    a = Analysis(df)
    f = Filters(start_date=date.min, end_date=date.max)
    assert sum(row["visits"] for row in a.trend(f, "weekly")) == 4
    assert a.trend(Filters(start_date=date(2500, 1, 1), end_date=date.max), "daily") == []


def test_summary_headline_fields_break_ties_alphabetically():
    frame, _ = validate_csv(CSV)
    summary = Analysis(frame).summary(Filters())
    assert summary["avg_visits_per_day"] == 0.5  # 4 visits over 1-8 July
    assert (summary["top_condition"], summary["top_condition_share_pct"]) == ("Respiratory", 50.0)
    assert summary["busiest_locality"] == "Lakeside"  # 2-2 tie with Northstead


@pytest.mark.parametrize(
    "start,end,previous,change",
    [
        (None, None, None, None),  # earlier window would predate the dataset
        (date(2026, 7, 2), date(2026, 7, 8), None, None),
        (date(2026, 7, 5), date(2026, 7, 8), 2, 0.0),  # 1-4 July vs 5-8 July
        (date(2026, 7, 7), date(2026, 7, 8), 0, None),  # zero baseline: change undefined
    ],
)
def test_summary_previous_period(start, end, previous, change):
    frame, _ = validate_csv(CSV)
    summary = Analysis(frame).summary(Filters(start_date=start, end_date=end))
    assert summary["previous_period_visits"] == previous
    assert summary["change_pct"] == change


def test_previous_period_keeps_other_filters():
    frame, _ = validate_csv(CSV)
    f = Filters(start_date=date(2026, 7, 5), end_date=date(2026, 7, 8), localities=["Lakeside"])
    previous = Analysis(frame).previous_period(f)
    assert (previous.start_date, previous.end_date) == (date(2026, 7, 1), date(2026, 7, 4))
    assert previous.localities == ["Lakeside"]

"""CSV validation and reproducible synthetic data. Validated datasets are never persisted by the application."""

import csv
import io
import random
import threading
import time
from dataclasses import dataclass
from datetime import date, timedelta
from uuid import uuid4

import pandas as pd

from shared.models import DatasetInfo, ValidationReport

COLUMNS = ["visit_id", "visit_date", "locality", "age", "gender", "condition"]
MAX_BYTES = 10 * 1024 * 1024
MAX_ROWS = 100_000


class InvalidDataset(ValueError):
    def __init__(self, issues):
        self.issues = issues
        super().__init__("CSV validation failed.")


def validate_csv(payload: bytes, max_rows: int = MAX_ROWS):
    if len(payload) > MAX_BYTES:
        raise InvalidDataset(["File exceeds the 10 MB upload limit."])
    try:
        text = payload.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text), strict=True)
        header = next(reader)
        if len(set(header)) != len(header):
            raise InvalidDataset(["Duplicate column names are not allowed."])
        missing = sorted(set(COLUMNS) - set(header))
        if missing:
            raise InvalidDataset(["Missing required columns: " + ", ".join(missing)])
        records = []
        for values in reader:
            if not values:
                continue
            if len(values) != len(header):
                raise InvalidDataset([f"CSV record {len(records) + 2}: wrong number of fields."])
            records.append(values)
            if len(records) > max_rows:
                raise InvalidDataset([f"File exceeds the {max_rows:,} row limit."])
    except (UnicodeDecodeError, csv.Error, StopIteration):
        raise InvalidDataset(["Upload a non-empty, UTF-8 encoded CSV with a header."]) from None
    if not records:
        raise InvalidDataset(["The CSV must contain at least one visit."])
    df = pd.DataFrame(records, columns=header)[COLUMNS].copy()
    for col in COLUMNS:
        df[col] = df[col].str.strip()
    issues = []
    for col in COLUMNS:
        bad = df[col].eq("")
        if bad.any():
            issues.append(
                f"{col}: {int(bad.sum())} missing value(s); CSV record(s) "
                + ", ".join(str(i + 2) for i in df.index[bad][:5])
            )
    valid_shape = df.visit_date.str.fullmatch(r"\d{4}-\d{2}-\d{2}")
    parsed = pd.to_datetime(df.visit_date, format="%Y-%m-%d", errors="coerce")
    if (~valid_shape | parsed.isna()).any():
        issues.append("visit_date: use valid ISO dates in YYYY-MM-DD format.")
    ages = pd.to_numeric(df.age, errors="coerce")
    if (ages.isna() | ages.lt(0) | ages.gt(120) | ages.mod(1).ne(0)).any():
        issues.append("age: every value must be a whole number between 0 and 120.")
    if df[COLUMNS].map(lambda value: len(value) > 200).any().any():
        issues.append("Values must be 200 characters or fewer.")
    if issues:
        raise InvalidDataset(issues)
    # Normalise types before checking IDs so 08 and 8 represent the same age.
    df["visit_date"] = parsed.dt.date
    df["age"] = ages.astype(int)
    input_rows = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    if df.visit_id.duplicated().any():
        raise InvalidDataset(["Conflicting records share a visit_id. Resolve them before uploading."])
    warnings = []
    if set(header) - set(COLUMNS):
        warnings.append("Additional columns were ignored; only the six declared fields are stored.")
    report = ValidationReport(
        input_rows=input_rows,
        accepted_rows=len(df),
        duplicates_removed=input_rows - len(df),
        warnings=warnings,
    )
    return df, report


def sample_csv() -> bytes:
    rng = random.Random(42)
    out = io.StringIO(newline="")
    writer = csv.writer(out)
    writer.writerow(COLUMNS)
    localities = ["Northstead", "Rivermere", "Lakeside", "Pinehurst"]
    conditions = ["Respiratory", "Fever", "Digestive", "Skin", "Other"]
    n = 0
    for day in range(90):
        for _ in range(rng.randint(22, 42)):
            n += 1
            writer.writerow(
                [
                    f"DEMO-{n:05}",
                    date(2026, 7, 1) + timedelta(days=day),
                    rng.choice(localities),
                    rng.randint(0, 90),
                    rng.choice(["Female", "Male", "Other / unspecified"]),
                    rng.choices(conditions, weights=[29, 23, 17, 14, 17])[0],
                ]
            )
    return out.getvalue().encode("utf-8")


@dataclass
class StoredDataset:
    frame: pd.DataFrame
    info: DatasetInfo
    last_used: float


class DatasetStore:
    """Single-process demo store; at most eight datasets, one-hour idle expiry."""

    def __init__(self):
        self.items = {}
        self.lock = threading.RLock()

    def add(self, payload: bytes, name: str, synthetic: bool = False) -> DatasetInfo:
        frame, report = validate_csv(payload)
        info = DatasetInfo(
            dataset_id=uuid4().hex,
            name=name[:120],
            synthetic=synthetic,
            row_count=len(frame),
            start_date=frame.visit_date.min(),
            end_date=frame.visit_date.max(),
            localities=sorted(frame.locality.unique()),
            conditions=sorted(frame.condition.unique()),
            genders=sorted(frame.gender.unique()),
            validation=report,
        )
        with self.lock:
            self._expire()
            if len(self.items) >= 8:
                oldest = min(self.items, key=lambda k: self.items[k].last_used)
                del self.items[oldest]
            self.items[info.dataset_id] = StoredDataset(frame, info, time.monotonic())
        return info

    def _expire(self):
        now = time.monotonic()
        for key in list(self.items):
            if now - self.items[key].last_used > 3600:
                del self.items[key]

    def get(self, dataset_id: str) -> StoredDataset:
        with self.lock:
            self._expire()
            if dataset_id not in self.items:
                raise KeyError(dataset_id)
            item = self.items[dataset_id]
            item.last_used = time.monotonic()
            return item

    def delete(self, dataset_id: str):
        with self.lock:
            self.items.pop(dataset_id, None)

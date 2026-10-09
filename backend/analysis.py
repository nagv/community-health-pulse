"""Deterministic computations used by the API and the agent's tools."""

from datetime import date, timedelta

import pandas as pd

from shared.models import AGE_BANDS, Filters


class Analysis:
    def __init__(self, frame: pd.DataFrame):
        self.frame = frame.copy()
        self.frame["age_band"] = pd.cut(self.frame.age, [-1, 4, 17, 44, 64, 120], labels=AGE_BANDS).astype(
            str
        )

    def select(self, filters: Filters):
        df = self.frame
        if filters.start_date:
            df = df[df.visit_date >= filters.start_date]
        if filters.end_date:
            df = df[df.visit_date <= filters.end_date]
        for field, values in [
            ("locality", filters.localities),
            ("age_band", filters.age_bands),
            ("condition", filters.conditions),
            ("gender", filters.genders),
        ]:
            if values:
                df = df[df[field].isin(values)]
        return df

    def selected_range(self, filters: Filters) -> tuple[date, date]:
        """The selected date window, clipped to the dataset's coverage."""
        lo, hi = self.frame.visit_date.min(), self.frame.visit_date.max()
        return max(filters.start_date or lo, lo), min(filters.end_date or hi, hi)

    def previous_period(self, filters: Filters) -> Filters | None:
        """Same filters over the equally long window just before the selection.

        None when that window would start before the dataset does, so a partial
        earlier window is never compared against a full one.
        """
        start, end = self.selected_range(filters)
        if start > end:
            return None
        days = (end - start).days + 1
        prev_end = start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=days - 1)
        if prev_start < self.frame.visit_date.min():
            return None
        return filters.model_copy(update={"start_date": prev_start, "end_date": prev_end})

    @staticmethod
    def _leader(column: pd.Series) -> tuple[str, int]:
        counts = column.value_counts()
        label = min(counts.index, key=lambda value: (-counts[value], str(value)))
        return str(label), int(counts[label])

    def summary(self, filters: Filters):
        df = self.select(filters)
        start, end = self.selected_range(filters)
        range_days = max((end - start).days + 1, 0)
        top_condition = top_share = busiest = None
        if len(df):
            # Ties break alphabetically, matching breakdown()'s ordering.
            top_condition, top_count = self._leader(df.condition)
            top_share = round(top_count / len(df) * 100, 2)
            busiest, _ = self._leader(df.locality)
        previous = self.previous_period(filters)
        previous_visits = len(self.select(previous)) if previous else None
        change_pct = (
            round((len(df) - previous_visits) / previous_visits * 100, 2) if previous_visits else None
        )
        return {
            "recorded_visits": len(df),
            "localities": int(df.locality.nunique()),
            "completeness_pct": 100.0 if len(df) else 0.0,
            "date_coverage_days": (df.visit_date.max() - df.visit_date.min()).days + 1 if len(df) else 0,
            "start_date": df.visit_date.min() if len(df) else None,
            "end_date": df.visit_date.max() if len(df) else None,
            "avg_visits_per_day": round(len(df) / range_days, 1) if range_days else 0.0,
            "top_condition": top_condition,
            "top_condition_share_pct": top_share,
            "busiest_locality": busiest,
            "previous_period_visits": previous_visits,
            "change_pct": change_pct,
        }

    def breakdown(self, filters: Filters, group: str):
        if group not in ("condition", "locality", "age_band", "gender"):
            raise ValueError("Unsupported grouping.")
        df = self.select(filters)
        counts = df.groupby(group, observed=True).size().reset_index(name="visits")
        counts = counts.sort_values(["visits", group], ascending=[False, True])
        counts["share_pct"] = (counts.visits / len(df) * 100).round(2) if len(df) else 0.0
        return counts.to_dict("records")

    def top_conditions(self, filters: Filters, limit: int = 10):
        if not 1 <= limit <= 50:
            raise ValueError("Limit must be between 1 and 50.")
        return self.breakdown(filters, "condition")[:limit]

    def trend(self, filters: Filters, frequency: str):
        if frequency not in ("daily", "weekly"):
            raise ValueError("Choose daily or weekly.")
        df = self.select(filters)
        start = max(filters.start_date or self.frame.visit_date.min(), self.frame.visit_date.min())
        end = min(filters.end_date or self.frame.visit_date.max(), self.frame.visit_date.max())
        if start > end:
            return []
        # Group first, then fill missing intervals (including zero-visit periods).
        counts = (
            pd.Series(1, index=pd.to_datetime(df.visit_date))
            .resample("D" if frequency == "daily" else "W-MON", label="left", closed="left")
            .sum()
        )
        index = pd.date_range(start, end, freq="D")
        if frequency == "weekly":
            index = index.to_period("W-SUN").start_time.unique()
        counts = counts.reindex(index, fill_value=0)
        return [{"period": t.date().isoformat(), "visits": int(v)} for t, v in counts.items()]

    def compare(
        self,
        filters: Filters,
        previous_start: date,
        previous_end: date,
        current_start: date,
        current_end: date,
        group: str,
    ):
        if previous_start > previous_end or current_start > current_end:
            raise ValueError("Each comparison period needs an ordered start and end date.")
        if not (previous_end < current_start or current_end < previous_start):
            raise ValueError("Comparison periods must not overlap.")
        previous = filters.model_copy(update={"start_date": previous_start, "end_date": previous_end})
        current = filters.model_copy(update={"start_date": current_start, "end_date": current_end})
        before = {r[group]: r for r in self.breakdown(previous, group)}
        after = {r[group]: r for r in self.breakdown(current, group)}
        rows = []
        for label in sorted(before.keys() | after.keys()):
            old = before.get(label, {})
            new = after.get(label, {})
            p, c = old.get("visits", 0), new.get("visits", 0)
            rows.append(
                {
                    group: label,
                    "previous_visits": p,
                    "current_visits": c,
                    "change": c - p,
                    "change_pct": round((c - p) / p * 100, 2) if p else None,
                    "previous_share_pct": old.get("share_pct", 0),
                    "current_share_pct": new.get("share_pct", 0),
                }
            )
        return sorted(rows, key=lambda r: (-r["change"], str(r[group])))

    def records(self, filters: Filters, page: int, page_size: int):
        df = self.select(filters)
        rows = (
            df.sort_values(["visit_date", "visit_id"]).iloc[(page - 1) * page_size : page * page_size].copy()
        )
        rows["visit_date"] = rows.visit_date.map(date.isoformat)
        return {"rows": rows.to_dict("records"), "total": len(df), "page": page, "page_size": page_size}

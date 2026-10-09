"""Dataset-bound tools. The model cannot submit executable code or chart values."""

from datetime import date
from typing import Literal
from uuid import uuid4

from langchain_core.tools import tool

from backend.analysis import Analysis
from shared.models import AnalysisStep, ChartSpec, Filters, Group


class ToolSession:
    def __init__(self, analysis: Analysis, filters: Filters):
        self.analysis = analysis
        self.base = filters
        self.results = {}
        self.charts = []
        self.steps = []
        self.executions = 0

    def effective(self, overrides: Filters | None):
        return Filters.model_validate(
            {**self.base.model_dump(), **(overrides.model_dump(exclude_unset=True) if overrides else {})}
        )

    def record(self, label, rows, filters, group=None, measures=None, **extra):
        if self.executions >= 12:
            raise RuntimeError("Tool execution limit reached.")
        self.executions += 1
        result_id = uuid4().hex
        result = {
            "result_id": result_id,
            "rows": rows[:50],
            "filters": filters,
            "group": group,
            "measures": measures or ["visits"],
            **extra,
        }
        if len(rows) > 50:
            result["truncated"] = True
            result["total_groups"] = len(rows)
        self.results[result_id] = result
        self.steps.append(AnalysisStep(label=label, success=True, result_id=result_id, filters=filters))
        return result

    def tools(self):
        @tool
        async def get_dataset_summary(filters: Filters | None = None) -> dict:
            """Get calculated visit totals, coverage and available fields. Optional filters override active UI filters."""
            f = self.effective(filters)
            summary = self.analysis.summary(f)
            summary = {k: v.isoformat() if isinstance(v, date) else v for k, v in summary.items()}
            return self.record(
                "Checked dataset and date coverage",
                [],
                f.model_dump(mode="json"),
                summary=summary,
                available_fields=["visit_date", "locality", "age", "age_band", "gender", "condition"],
                condition_options=sorted(self.analysis.frame.condition.unique())[:100],
                locality_options=sorted(self.analysis.frame.locality.unique())[:100],
            )

        @tool
        async def get_top_conditions(limit: int = 10, filters: Filters | None = None) -> dict:
            """Rank recorded conditions by visit count and visit share. Limit must be 1 to 50."""
            f = self.effective(filters)
            return self.record(
                "Counted visits by condition",
                self.analysis.top_conditions(f, limit),
                f.model_dump(mode="json"),
                group="condition",
            )

        @tool
        async def get_visit_trend(
            frequency: Literal["daily", "weekly"] = "weekly", filters: Filters | None = None
        ) -> dict:
            """Calculate daily or Monday-start weekly visit counts, including zero-visit periods."""
            f = self.effective(filters)
            rows = self.analysis.trend(f, frequency)
            # Trends may have more than 50 periods; chart source keeps full timeline.
            result = self.record("Calculated visit trend", rows, f.model_dump(mode="json"), group="period")
            self.results[result["result_id"]]["rows"] = rows
            return {**result, "rows": rows[:100], "truncated": len(rows) > 100}

        @tool
        async def compare_periods(
            previous_start: date,
            previous_end: date,
            current_start: date,
            current_end: date,
            group: Group = "condition",
            filters: Filters | None = None,
        ) -> dict:
            """Compare two explicitly specified non-overlapping periods. Dates are inclusive.
            Dates replace active date filters; other filters remain. Null change_pct means zero baseline.
            Do not assume unspecified comparison periods: ask the user for dates first."""
            f = self.effective(filters)
            rows = self.analysis.compare(f, previous_start, previous_end, current_start, current_end, group)
            scope = f.model_dump(mode="json")
            scope.update(
                start_date=None,
                end_date=None,
                previous_period=[previous_start.isoformat(), previous_end.isoformat()],
                current_period=[current_start.isoformat(), current_end.isoformat()],
            )
            return self.record(
                "Compared the selected periods",
                rows,
                scope,
                group=group,
                measures=["previous_visits", "current_visits", "change"],
            )

        @tool
        async def get_group_breakdown(group: Group = "locality", filters: Filters | None = None) -> dict:
            """Summarise recorded visits by locality, condition, age_band or gender."""
            f = self.effective(filters)
            return self.record(
                "Grouped recorded visits",
                self.analysis.breakdown(f, group),
                f.model_dump(mode="json"),
                group=group,
            )

        @tool
        async def create_chart(result_id: str, kind: Literal["bar", "line"], x: str, y: str) -> dict:
            """Create a chart from a previous analysis result_id. Never supply invented data.
            x must equal that result's group; y must be one of its measures."""
            if self.executions >= 12:
                raise RuntimeError("Tool execution limit reached.")
            self.executions += 1
            if result_id not in self.results:
                raise ValueError("Use a result_id returned by an analysis tool in this request.")
            result = self.results[result_id]
            if x != result["group"] or y not in result["measures"]:
                raise ValueError("Choose the group and a supported measure from that result.")
            chart = ChartSpec(
                truncated=len(result["rows"]) < result.get("total_groups", len(result["rows"])),
                total_groups=result.get("total_groups", len(result["rows"])),
                result_id=result_id,
                title=f"{y.replace('_', ' ').title()} by {x.replace('_', ' ')}",
                kind=kind,
                x=x,
                y=y,
                rows=result["rows"],
                filters=result["filters"],
            )
            self.charts.append(chart)
            self.steps.append(
                AnalysisStep(
                    label="Created chart", success=True, result_id=result_id, filters=result["filters"]
                )
            )
            return {"result_id": result_id, "chart_created": True, "filters": result["filters"]}

        return [
            get_dataset_summary,
            get_top_conditions,
            get_visit_trend,
            compare_periods,
            get_group_breakdown,
            create_chart,
        ]

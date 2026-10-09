"""Typed HTTP contracts shared by both applications."""

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

AGE_BANDS = ["0-4", "5-17", "18-44", "45-64", "65+"]
Group = Literal["condition", "locality", "age_band", "gender"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Filters(Contract):
    start_date: date | None = None
    end_date: date | None = None
    localities: list[str] = Field(default_factory=list, max_length=100)
    age_bands: list[Literal["0-4", "5-17", "18-44", "45-64", "65+"]] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list, max_length=100)
    genders: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def date_order(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("Start date must be on or before end date.")
        return self


class ValidationReport(Contract):
    input_rows: int
    accepted_rows: int
    duplicates_removed: int
    warnings: list[str] = Field(default_factory=list)


class DatasetInfo(Contract):
    dataset_id: str
    name: str
    synthetic: bool
    row_count: int
    start_date: date
    end_date: date
    localities: list[str]
    conditions: list[str]
    genders: list[str]
    age_bands: list[str] = Field(default_factory=lambda: AGE_BANDS.copy())
    validation: ValidationReport


class Summary(Contract):
    recorded_visits: int
    localities: int
    completeness_pct: float
    date_coverage_days: int
    start_date: date | None
    end_date: date | None


class ChartSpec(Contract):
    truncated: bool = False
    total_groups: int | None = None
    result_id: str
    title: str
    kind: Literal["bar", "line"]
    x: str
    y: str
    rows: list[dict[str, Any]]
    filters: dict[str, Any]


class DashboardRequest(Contract):
    filters: Filters = Field(default_factory=Filters)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)


class RecordsPage(Contract):
    rows: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


class DashboardResponse(Contract):
    condition_groups: int
    summary: Summary
    filters: Filters
    charts: list[ChartSpec]
    conditions: list[dict[str, Any]]
    records: RecordsPage


class ChatTurn(Contract):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(Contract):
    dataset_id: str
    question: str = Field(min_length=1, max_length=2000)
    filters: Filters = Field(default_factory=Filters)
    history: list[ChatTurn] = Field(default_factory=list, max_length=12)


class AnalysisStep(Contract):
    label: str
    success: bool
    result_id: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(Contract):
    answer: str
    charts: list[ChartSpec] = Field(default_factory=list)
    steps: list[AnalysisStep] = Field(default_factory=list)
    filters: Filters
    duration_ms: int
    token_usage: dict[str, int] = Field(default_factory=dict)

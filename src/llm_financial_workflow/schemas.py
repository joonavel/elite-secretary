from __future__ import annotations

import operator
from typing import Any

from pydantic import BaseModel, Field
from typing_extensions import Annotated, TypedDict


def merge_dicts(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = dict(left)
    merged.update(right)
    return merged


class RunRequest(BaseModel):
    scenario_id: str = "fixed_h1_financial_report_demo"
    report_period: str = "2025 H1"
    source_seed_csv_path: str
    output_dir: str
    run_id: str
    org_scope: str = "company-wide"
    metrics: list[str] = Field(default_factory=lambda: ["cost_usd", "token_usage"])
    output_formats: list[str] = Field(default_factory=lambda: ["excel", "json"])
    source_ref: str = "employee_llm_credit_usage.csv"


class InsightDocument(BaseModel):
    insights: list[str] = Field(min_length=3, max_length=3)
    patterns: list[str] = Field(min_length=2, max_length=2)
    recommendations: list[str] = Field(min_length=3, max_length=3)


class WorkflowState(TypedDict, total=False):
    run_id: str
    scenario_id: str
    report_period: str
    output_dir: str
    source_seed_csv_path: str
    org_scope: str
    metrics: list[str]
    output_formats: list[str]
    source_ref: str
    log_path: str
    summary_path: str
    status_by_step: Annotated[dict[str, str], merge_dicts]
    source_paths: Annotated[dict[str, str], merge_dicts]
    summary_paths: Annotated[dict[str, str], merge_dicts]
    artifacts: Annotated[list[str], operator.add]
    logs: Annotated[list[dict[str, Any]], operator.add]
    errors: Annotated[list[str], operator.add]
    financial_rows: list[dict[str, Any]]
    team_monthly_cost: list[dict[str, Any]]
    team_monthly_tokens: list[dict[str, Any]]
    team_h1_summary: list[dict[str, Any]]
    support_payload: dict[str, Any]
    excel_report_path: str
    insight_payload_path: str

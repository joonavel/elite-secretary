from __future__ import annotations

import csv
import importlib.util
import json
import sys
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any


def _load_generator_module():
    module_path = Path(__file__).resolve().parents[3] / "scripts" / "generate_llm_credit_db.py"
    spec = importlib.util.spec_from_file_location("generate_llm_credit_db", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load generator module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


generator = _load_generator_module()


@dataclass(frozen=True)
class GeneratedFinancialArtifacts:
    financial_rows: list[dict[str, Any]]
    financial_csv_path: Path
    financial_sql_path: Path


@dataclass(frozen=True)
class AggregatedArtifacts:
    team_monthly_cost: list[dict[str, Any]]
    team_monthly_tokens: list[dict[str, Any]]
    team_h1_summary: list[dict[str, Any]]
    support_payload: dict[str, Any]
    cost_csv_path: Path
    token_csv_path: Path
    summary_csv_path: Path
    support_json_path: Path


class DataValidationError(ValueError):
    """Raised when source data is missing or malformed."""


def load_seed_rows(seed_csv_path: Path) -> list[dict[str, Any]]:
    if not seed_csv_path.exists():
        raise DataValidationError(f"Seed CSV not found: {seed_csv_path}")

    with seed_csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = [column for column in generator.SEED_COLUMNS if column not in fieldnames]
        if missing:
            raise DataValidationError(f"Seed CSV is missing required columns: {', '.join(missing)}")

        rows: list[dict[str, Any]] = []
        for record in reader:
            row: dict[str, Any] = {
                "employee_id": int(record["employee_id"]),
                "employee_name": record["employee_name"],
                "employee_type": record["employee_type"],
            }
            for column in generator.SEED_COLUMNS[3:]:
                try:
                    row[column] = Decimal(record[column]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                except Exception as exc:
                    raise DataValidationError(f"Invalid numeric value in {column}: {record[column]!r}") from exc
            rows.append(row)

    return rows


class FinancialDataService:
    def generate_financial_source(self, seed_csv_path: Path, output_dir: Path) -> GeneratedFinancialArtifacts:
        seed_rows = load_seed_rows(seed_csv_path)
        financial_rows = generator.build_financial_dataset(seed_rows)
        generator.validate_financial_rows(financial_rows)

        financial_csv_path = output_dir / "employee_llm_financial_usage_2025_h1.csv"
        financial_sql_path = output_dir / "employee_llm_financial_usage_2025_h1.sql"
        generator.write_csv_file(financial_rows, generator.FINANCIAL_COLUMNS, financial_csv_path)
        generator.write_sql_file(
            generator.FINANCIAL_CREATE_SQL,
            "employee_llm_financial_usage_2025_h1",
            generator.FINANCIAL_COLUMNS,
            financial_rows,
            financial_sql_path,
        )
        return GeneratedFinancialArtifacts(
            financial_rows=financial_rows,
            financial_csv_path=financial_csv_path,
            financial_sql_path=financial_sql_path,
        )

    def aggregate(self, financial_rows: list[dict[str, Any]], output_dir: Path) -> AggregatedArtifacts:
        team_monthly_cost = generator.build_team_monthly_cost(financial_rows)
        team_monthly_tokens = generator.build_team_monthly_tokens(financial_rows)
        team_h1_summary = generator.build_team_h1_summary(financial_rows)
        support_payload = self._build_support_payload(
            financial_rows,
            team_monthly_cost,
            team_monthly_tokens,
            team_h1_summary,
        )

        cost_csv_path = output_dir / "employee_llm_team_monthly_cost_2025_h1.csv"
        token_csv_path = output_dir / "employee_llm_team_monthly_tokens_2025_h1.csv"
        summary_csv_path = output_dir / "employee_llm_team_h1_summary_2025_h1.csv"
        support_json_path = output_dir / "employee_llm_report_support_2025_h1.json"

        generator.write_csv_file(
            team_monthly_cost,
            ["team_name", *generator.REPORT_MONTHS, "h1_total_cost_usd", "monthly_avg_cost_usd"],
            cost_csv_path,
        )
        generator.write_csv_file(
            team_monthly_tokens,
            ["team_name", *generator.REPORT_MONTHS, "h1_total_tokens", "monthly_avg_tokens"],
            token_csv_path,
        )
        generator.write_csv_file(
            team_h1_summary,
            ["team_name", "h1_total_cost_usd", "h1_total_tokens", "cost_share_pct", "monthly_avg_cost_usd"],
            summary_csv_path,
        )
        with support_json_path.open("w", encoding="utf-8") as handle:
            json.dump(self._to_jsonable(support_payload), handle, ensure_ascii=False, indent=2)
            handle.write("\n")

        return AggregatedArtifacts(
            team_monthly_cost=team_monthly_cost,
            team_monthly_tokens=team_monthly_tokens,
            team_h1_summary=team_h1_summary,
            support_payload=self._to_jsonable(support_payload),
            cost_csv_path=cost_csv_path,
            token_csv_path=token_csv_path,
            summary_csv_path=summary_csv_path,
            support_json_path=support_json_path,
        )

    def _build_support_payload(
        self,
        financial_rows: list[dict[str, Any]],
        team_monthly_cost: list[dict[str, Any]],
        team_monthly_tokens: list[dict[str, Any]],
        team_h1_summary: list[dict[str, Any]],
    ) -> dict[str, Any]:
        total_cost = sum((Decimal(str(row["h1_total_cost_usd"])) for row in team_h1_summary), Decimal("0.00"))
        total_tokens = sum(int(row["h1_total_tokens"]) for row in team_h1_summary)
        top_team = max(team_h1_summary, key=lambda row: Decimal(str(row["h1_total_cost_usd"])))
        highest_share_team = max(team_h1_summary, key=lambda row: Decimal(str(row["cost_share_pct"])))

        monthly_totals: dict[str, Decimal] = {}
        for month in generator.REPORT_MONTHS:
            monthly_totals[month] = sum((Decimal(str(row[month])) for row in team_monthly_cost), Decimal("0.00"))

        growth_window = []
        for previous, current in zip(generator.REPORT_MONTHS, generator.REPORT_MONTHS[1:]):
            growth_window.append((previous, current, monthly_totals[current] - monthly_totals[previous]))
        steepest_growth = max(growth_window, key=lambda item: item[2])

        main_cost = sum((row["cost_usd"] for row in financial_rows if row["model_tier"] == "main"), Decimal("0.00"))
        small_cost = sum((row["cost_usd"] for row in financial_rows if row["model_tier"] == "small"), Decimal("0.00"))
        main_share_pct = ((main_cost / (main_cost + small_cost)) * Decimal("100")).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        return {
            "report_period": "2025 H1",
            "data_source": "generated from employee_llm_credit_usage.csv seed dataset",
            "seed": generator.SEED,
            "months": generator.REPORT_MONTHS,
            "teams": generator.TEAMS,
            "totals": {
                "h1_total_cost_usd": f"{total_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}",
                "h1_total_tokens": total_tokens,
                "main_tier_share_pct": f"{main_share_pct:.2f}",
            },
            "insights_seed": {
                "top_team_name": top_team["team_name"],
                "top_team_cost_usd": f"{Decimal(str(top_team['h1_total_cost_usd'])):.2f}",
                "top_team_cost_share_pct": f"{Decimal(str(highest_share_team['cost_share_pct'])) * Decimal('100'):.2f}",
                "steepest_growth_from": steepest_growth[0],
                "steepest_growth_to": steepest_growth[1],
                "steepest_growth_delta_usd": f"{steepest_growth[2].quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}",
                "monthly_totals": {month: f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}" for month, value in monthly_totals.items()},
            },
            "team_monthly_cost": team_monthly_cost,
            "team_monthly_tokens": team_monthly_tokens,
            "team_h1_summary": team_h1_summary,
        }

    def _to_jsonable(self, value: Any) -> Any:
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, list):
            return [self._to_jsonable(item) for item in value]
        if isinstance(value, dict):
            return {key: self._to_jsonable(item) for key, item in value.items()}
        return value

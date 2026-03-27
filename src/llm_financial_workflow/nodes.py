from __future__ import annotations

import json
from pathlib import Path

from llm_financial_workflow.config import AppConfig
from llm_financial_workflow.logging_utils import append_jsonl, make_step_log, utc_now
from llm_financial_workflow.schemas import WorkflowState
from llm_financial_workflow.services.data_service import FinancialDataService
from llm_financial_workflow.services.excel_mcp_service import ExcelMCPService
from llm_financial_workflow.services.insight_service import InsightService


STEP_ORDER = [
    "initialize_run",
    "load_scenario",
    "prepare_financial_source",
    "validate_financial_source",
    "aggregate_financials",
    "build_excel_report",
    "build_insight_payload",
    "join_outputs",
    "finalize_run",
]


def _status_update(step_name: str, status: str) -> dict[str, str]:
    return {step_name: status}


def _log_step(state: WorkflowState, step_name: str, status: str, **kwargs: object) -> dict[str, object]:
    payload = make_step_log(
        run_id=state["run_id"],
        step_name=step_name,
        status=status,
        input_summary=kwargs.get("input_summary"),
        output_summary=kwargs.get("output_summary"),
        error_message=kwargs.get("error_message"),
    )
    append_jsonl(Path(state["log_path"]), payload)
    return payload


async def initialize_run(state: WorkflowState, config: AppConfig) -> WorkflowState:
    output_dir = Path(state["output_dir"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / f"{state['run_id']}.jsonl"
    summary_path = output_dir / f"{state['run_id']}_summary.json"
    status_by_step = {step: "pending" for step in STEP_ORDER}
    log_entry = _log_step(
        {
            **state,
            "log_path": str(log_path),
        },
        "initialize_run",
        "success",
        input_summary={"scenario_id": state["scenario_id"], "report_period": state["report_period"]},
        output_summary={"output_dir": str(output_dir)},
    )
    return {
        "log_path": str(log_path),
        "summary_path": str(summary_path),
        "status_by_step": {**status_by_step, "initialize_run": "success"},
        "logs": [log_entry],
    }


async def load_scenario(state: WorkflowState, config: AppConfig) -> WorkflowState:
    scenario = {
        "scenario_id": state["scenario_id"],
        "report_period": state["report_period"],
        "source_seed_csv_path": state["source_seed_csv_path"],
        "notes": "FR-3 downstream fixed demo scenario",
    }
    log_entry = _log_step(
        state,
        "load_scenario",
        "success",
        output_summary=scenario,
    )
    return {
        "status_by_step": _status_update("load_scenario", "success"),
        "logs": [log_entry],
    }


async def prepare_financial_source(state: WorkflowState, config: AppConfig) -> WorkflowState:
    service = FinancialDataService()
    generated = service.generate_financial_source(
        seed_csv_path=Path(state["source_seed_csv_path"]),
        output_dir=Path(state["output_dir"]),
    )
    log_entry = _log_step(
        state,
        "prepare_financial_source",
        "success",
        input_summary={"seed_csv": state["source_seed_csv_path"]},
        output_summary={"financial_rows": len(generated.financial_rows)},
    )
    return {
        "financial_rows": generated.financial_rows,
        "source_paths": {
            "financial_csv": str(generated.financial_csv_path),
            "financial_sql": str(generated.financial_sql_path),
        },
        "artifacts": [str(generated.financial_csv_path), str(generated.financial_sql_path)],
        "status_by_step": _status_update("prepare_financial_source", "success"),
        "logs": [log_entry],
    }


async def validate_financial_source(state: WorkflowState, config: AppConfig) -> WorkflowState:
    rows = state["financial_rows"]
    if not rows:
        raise ValueError("financial_rows is empty")
    log_entry = _log_step(
        state,
        "validate_financial_source",
        "success",
        output_summary={"row_count": len(rows), "report_period": state["report_period"]},
    )
    return {
        "status_by_step": _status_update("validate_financial_source", "success"),
        "logs": [log_entry],
    }


async def aggregate_financials(state: WorkflowState, config: AppConfig) -> WorkflowState:
    service = FinancialDataService()
    aggregated = service.aggregate(state["financial_rows"], Path(state["output_dir"]))
    log_entry = _log_step(
        state,
        "aggregate_financials",
        "success",
        output_summary={
            "teams": len(aggregated.team_h1_summary),
            "cost_csv": str(aggregated.cost_csv_path),
        },
    )
    return {
        "team_monthly_cost": aggregated.team_monthly_cost,
        "team_monthly_tokens": aggregated.team_monthly_tokens,
        "team_h1_summary": aggregated.team_h1_summary,
        "support_payload": aggregated.support_payload,
        "summary_paths": {
            "cost_csv": str(aggregated.cost_csv_path),
            "token_csv": str(aggregated.token_csv_path),
            "summary_csv": str(aggregated.summary_csv_path),
            "support_json": str(aggregated.support_json_path),
        },
        "artifacts": [
            str(aggregated.cost_csv_path),
            str(aggregated.token_csv_path),
            str(aggregated.summary_csv_path),
            str(aggregated.support_json_path),
        ],
        "status_by_step": _status_update("aggregate_financials", "success"),
        "logs": [log_entry],
    }


async def build_excel_report(state: WorkflowState, config: AppConfig) -> WorkflowState:
    service = ExcelMCPService(config.excel_mcp_command)
    insight_document = state.get("support_payload", {}).get("insight_document", {
        "insights": ["Pending insight generation."] * 3,
        "patterns": ["Pending insight generation."] * 2,
        "recommendations": ["Pending insight generation."] * 3,
    })
    report_path = await service.build_report(
        output_dir=Path(state["output_dir"]),
        report_name=config.default_excel_report_name,
        financial_csv_path=Path(state["source_paths"]["financial_csv"]),
        cost_csv_path=Path(state["summary_paths"]["cost_csv"]),
        token_csv_path=Path(state["summary_paths"]["token_csv"]),
        summary_csv_path=Path(state["summary_paths"]["summary_csv"]),
        support_payload=state["support_payload"],
        insight_document=insight_document,
    )
    log_entry = _log_step(
        state,
        "build_excel_report",
        "success",
        output_summary={"excel_report_path": str(report_path)},
    )
    return {
        "excel_report_path": str(report_path),
        "artifacts": [str(report_path)],
        "status_by_step": _status_update("build_excel_report", "success"),
        "logs": [log_entry],
    }


async def build_insight_payload(state: WorkflowState, config: AppConfig) -> WorkflowState:
    service = InsightService(model_name=config.openai_model)
    insight_document = await service.build_insights(state["support_payload"])
    payload = dict(state["support_payload"])
    payload["generated_at_utc"] = utc_now()
    payload["insights"] = insight_document["insights"]
    payload["patterns"] = insight_document["patterns"]
    payload["recommendations"] = insight_document["recommendations"]
    payload["insight_document"] = insight_document

    insight_payload_path = Path(state["summary_paths"]["support_json"])
    insight_payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log_entry = _log_step(
        state,
        "build_insight_payload",
        "success",
        output_summary={"insight_payload_path": str(insight_payload_path)},
    )
    return {
        "support_payload": payload,
        "insight_payload_path": str(insight_payload_path),
        "artifacts": [str(insight_payload_path)],
        "status_by_step": _status_update("build_insight_payload", "success"),
        "logs": [log_entry],
    }


async def join_outputs(state: WorkflowState, config: AppConfig) -> WorkflowState:
    if state.get("excel_report_path") and state.get("support_payload", {}).get("insights"):
        service = ExcelMCPService(config.excel_mcp_command)
        await service.update_insights(
            report_path=Path(state["excel_report_path"]),
            support_payload=state["support_payload"],
            insight_document=state["support_payload"]["insight_document"],
        )
    log_entry = _log_step(
        state,
        "join_outputs",
        "success",
        output_summary={
            "excel_report_path": state.get("excel_report_path"),
            "insight_payload_path": state.get("insight_payload_path"),
        },
    )
    return {
        "status_by_step": _status_update("join_outputs", "success"),
        "logs": [log_entry],
    }


async def finalize_run(state: WorkflowState, config: AppConfig) -> WorkflowState:
    final_status = {**state["status_by_step"], "finalize_run": "success"}
    artifacts = list(dict.fromkeys(state.get("artifacts", [])))
    summary_payload = {
        "run_id": state["run_id"],
        "scenario_id": state["scenario_id"],
        "report_period": state["report_period"],
        "status_by_step": final_status,
        "artifacts": artifacts,
        "excel_report_path": state.get("excel_report_path"),
        "insight_payload_path": state.get("insight_payload_path"),
    }
    Path(state["summary_path"]).write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log_entry = _log_step(
        state,
        "finalize_run",
        "success",
        output_summary={"summary_path": state["summary_path"]},
    )
    return {
        "artifacts": [state["summary_path"]],
        "status_by_step": _status_update("finalize_run", "success"),
        "logs": [log_entry],
    }

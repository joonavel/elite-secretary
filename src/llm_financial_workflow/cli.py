from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from pathlib import Path

from llm_financial_workflow.config import AppConfig
from llm_financial_workflow.graph import build_workflow
from llm_financial_workflow.schemas import RunRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the FR4-FR11 LangGraph financial workflow.")
    parser.add_argument("--scenario-id", default="fixed_h1_financial_report_demo")
    parser.add_argument("--report-period", default=None)
    parser.add_argument("--seed-csv-path", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--request-json", default=None)
    return parser.parse_args()


def load_run_request(args: argparse.Namespace, config: AppConfig) -> RunRequest:
    if args.request_json:
        request_path = Path(args.request_json).resolve()
        payload = json.loads(request_path.read_text(encoding="utf-8"))
        payload.setdefault("run_id", args.run_id or f"run-{uuid.uuid4().hex[:12]}")
        payload.setdefault("output_dir", str(config.default_output_dir / payload["run_id"]))
        payload.setdefault("source_seed_csv_path", str(config.default_seed_csv_path))
        return RunRequest.model_validate(payload)

    run_id = args.run_id or f"run-{uuid.uuid4().hex[:12]}"
    output_dir = Path(args.output_dir).resolve() if args.output_dir else config.default_output_dir / run_id
    return RunRequest(
        run_id=run_id,
        scenario_id=args.scenario_id,
        report_period=args.report_period or config.default_report_period,
        source_seed_csv_path=str(
            Path(args.seed_csv_path).resolve() if args.seed_csv_path else config.default_seed_csv_path
        ),
        output_dir=str(output_dir),
        source_ref=str(config.default_seed_csv_path.name),
    )


async def _run() -> dict:
    args = parse_args()
    config = AppConfig.load()
    workflow = build_workflow(config)
    request = load_run_request(args, config)
    initial_state = {
        **request.model_dump(),
        "artifacts": [],
        "logs": [],
        "errors": [],
    }
    return await workflow.ainvoke(initial_state)


def main() -> None:
    result = asyncio.run(_run())
    print(f"Run completed: {result['run_id']}")
    if result.get("excel_report_path"):
        print(f"Excel report: {result['excel_report_path']}")
    if result.get("insight_payload_path"):
        print(f"Insights JSON: {result['insight_payload_path']}")
    print("Artifacts:")
    for artifact in result.get("artifacts", []):
        print(f" - {artifact}")


if __name__ == "__main__":
    main()

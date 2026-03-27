from __future__ import annotations

from pathlib import Path

from langgraph.graph import END, START, StateGraph

from llm_financial_workflow.config import AppConfig
from llm_financial_workflow.logging_utils import append_jsonl, make_step_log
from llm_financial_workflow.nodes import (
    aggregate_financials,
    build_excel_report,
    build_insight_payload,
    finalize_run,
    initialize_run,
    join_outputs,
    load_scenario,
    prepare_financial_source,
    validate_financial_source,
)
from llm_financial_workflow.schemas import WorkflowState


def build_workflow(config: AppConfig):
    def bind(node):
        async def wrapped(state):
            try:
                return await node(state, config=config)
            except Exception as exc:
                if state.get("log_path"):
                    append_jsonl(
                        Path(state["log_path"]),
                        make_step_log(
                            run_id=state["run_id"],
                            step_name=node.__name__,
                            status="failed",
                            input_summary={"report_period": state.get("report_period")},
                            output_summary={},
                            error_message=str(exc),
                        ),
                    )
                raise

        return wrapped

    graph = StateGraph(WorkflowState)
    graph.add_node("initialize_run", bind(initialize_run))
    graph.add_node("load_scenario", bind(load_scenario))
    graph.add_node("prepare_financial_source", bind(prepare_financial_source))
    graph.add_node("validate_financial_source", bind(validate_financial_source))
    graph.add_node("aggregate_financials", bind(aggregate_financials))
    graph.add_node("build_excel_report", bind(build_excel_report))
    graph.add_node("build_insight_payload", bind(build_insight_payload))
    graph.add_node("join_outputs", bind(join_outputs))
    graph.add_node("finalize_run", bind(finalize_run))

    graph.add_edge(START, "initialize_run")
    graph.add_edge("initialize_run", "load_scenario")
    graph.add_edge("load_scenario", "prepare_financial_source")
    graph.add_edge("prepare_financial_source", "validate_financial_source")
    graph.add_edge("validate_financial_source", "aggregate_financials")
    graph.add_edge("aggregate_financials", "build_excel_report")
    graph.add_edge("aggregate_financials", "build_insight_payload")
    graph.add_edge("build_excel_report", "join_outputs")
    graph.add_edge("build_insight_payload", "join_outputs")
    graph.add_edge("join_outputs", "finalize_run")
    graph.add_edge("finalize_run", END)
    return graph.compile()

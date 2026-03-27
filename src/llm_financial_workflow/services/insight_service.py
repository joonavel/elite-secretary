from __future__ import annotations

from typing import Any

from llm_financial_workflow.schemas import InsightDocument


class InsightService:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    async def build_insights(self, support_payload: dict[str, Any]) -> dict[str, Any]:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        seed = support_payload["insights_seed"]
        totals = support_payload["totals"]
        llm = ChatOpenAI(model=self.model_name)
        structured_llm = llm.with_structured_output(InsightDocument)

        messages = [
            SystemMessage(
                content=(
                    "You are writing a concise financial analysis memo for an internal Korean operations audience. "
                    "Use only the provided metrics. Do not invent numbers. Keep each item to one sentence."
                )
            ),
            HumanMessage(
                content=(
                    "Generate a structured insight document with exactly 3 insights, 2 patterns, and 3 recommendations.\n"
                    f"Report period: {support_payload['report_period']}\n"
                    f"Total cost USD: {totals['h1_total_cost_usd']}\n"
                    f"Total tokens: {totals['h1_total_tokens']}\n"
                    f"Main tier share percent: {totals['main_tier_share_pct']}\n"
                    f"Top team: {seed['top_team_name']} (${seed['top_team_cost_usd']})\n"
                    f"Top team cost share percent: {seed['top_team_cost_share_pct']}\n"
                    f"Steepest monthly growth: {seed['steepest_growth_from']} -> {seed['steepest_growth_to']} "
                    f"(${seed['steepest_growth_delta_usd']})\n"
                    f"Monthly totals: {seed['monthly_totals']}\n"
                    f"Team H1 summary: {support_payload['team_h1_summary']}"
                )
            ),
        ]

        result = await structured_llm.ainvoke(messages)
        return result.model_dump()

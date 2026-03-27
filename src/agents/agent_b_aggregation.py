from __future__ import annotations

from src.domain.models import AggregatedMetric, AggregationContext, Intent, MeetingContext


class AgentBAggregator:
    def aggregate(self, meeting_context: MeetingContext, intent: Intent) -> AggregationContext:
        _ = (meeting_context, intent)
        sample = [
            AggregatedMetric(team_name="Platform", month="2026-01", token_usage=120000.0, cost_krw=820000.0),
            AggregatedMetric(team_name="Platform", month="2026-02", token_usage=132000.0, cost_krw=860000.0),
            AggregatedMetric(team_name="Product", month="2026-01", token_usage=98000.0, cost_krw=710000.0),
        ]
        return AggregationContext(metrics=sample)

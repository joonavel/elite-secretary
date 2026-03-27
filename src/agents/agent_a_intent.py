from __future__ import annotations

from src.domain.models import Intent, MeetingContext, Transcript


class AgentAIntentExtractor:
    def extract(self, meeting_context: MeetingContext, transcript: Transcript) -> Intent:
        _ = (meeting_context, transcript)
        return Intent(
            request_type="llm_cost_analysis",
            period_type="half",
            period_value="H1",
            year=2026,
            scope_level="organization",
            metrics=["token_usage", "cost"],
            confidence=0.92,
        )

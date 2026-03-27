from __future__ import annotations

from pathlib import Path

from src.domain.models import AggregationContext, ArtifactMetadata, Intent, MeetingContext


class AgentDInsightWriter:
    """Placeholder implementation; full insight generation belongs to T-026."""

    def build(
        self,
        meeting_context: MeetingContext,
        intent: Intent,
        aggregation: AggregationContext,
        run_id: str,
    ) -> ArtifactMetadata:
        output_dir = Path("artifacts") / run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / "insight.md"
        target.write_text(
            "\n".join(
                [
                    f"# Insight ({meeting_context.meeting_id})",
                    f"period={intent.period_value} year={intent.year}",
                    f"metrics_count={len(aggregation.metrics)}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return ArtifactMetadata(artifact_name="insight.md", artifact_path=str(target), artifact_type="document")

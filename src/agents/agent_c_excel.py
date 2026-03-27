from __future__ import annotations

from pathlib import Path

from src.domain.models import AggregationContext, ArtifactMetadata, MeetingContext


class AgentCExcelBuilder:
    """Placeholder implementation; full Excel generation belongs to T-025."""

    def build(self, meeting_context: MeetingContext, aggregation: AggregationContext, run_id: str) -> ArtifactMetadata:
        output_dir = Path("artifacts") / run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / "report.xlsx"
        target.write_text(
            f"placeholder excel rows={len(aggregation.metrics)} meeting={meeting_context.meeting_id}\n",
            encoding="utf-8",
        )
        return ArtifactMetadata(artifact_name="report.xlsx", artifact_path=str(target), artifact_type="excel")

from __future__ import annotations

from datetime import UTC, datetime

from src.app.config import AppConfig
from src.domain.models import MeetingContext
from src.pipeline.orchestrator import build_integration_deps, default_deps, run_pipeline
from src.pipeline.state_store import PipelineStateStore


def main() -> None:
    config = AppConfig.from_env()

    meeting_context = MeetingContext(
        meeting_id="demo-meeting-001",
        chat_id=config.teams_chat_id or "demo-chat",
        meeting_title="H1 LLM Cost Review",
        meeting_time=datetime.now(UTC),
        message_hint="H1 토큰/비용 집계 요청",
    )

    state_store = PipelineStateStore()
    has_integration_env = bool(
        config.azure_tenant_id
        and config.azure_client_id
        and config.azure_client_secret
        and config.azure_speech_key
        and config.azure_speech_region
    )
    deps = build_integration_deps(config) if has_integration_env else default_deps(
        diarization_enabled=config.feature_diarization_enabled
    )
    result = run_pipeline(meeting_context=meeting_context, state_store=state_store, deps=deps)

    print(f"run_id={result.run_id}")
    print(f"status={result.status.value}")
    for artifact in result.artifacts:
        print(f"artifact={artifact.artifact_type}:{artifact.artifact_path}")
    if result.published_result:
        for link in result.published_result.destinations:
            print(f"published={link}")


if __name__ == "__main__":
    main()

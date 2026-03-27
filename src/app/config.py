from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from src.domain.errors import ErrorCode, PipelineError


@dataclass(slots=True)
class AppConfig:
    azure_tenant_id: str | None
    azure_client_id: str | None
    azure_client_secret: str | None
    azure_speech_key: str | None
    azure_speech_region: str | None
    graph_site_id: str | None
    graph_drive_id: str | None
    teams_channel_id: str | None
    feature_diarization_enabled: bool

    @classmethod
    def from_env(cls) -> "AppConfig":
        load_dotenv()
        diarization_raw = os.getenv("FEATURE_DIARIZATION_ENABLED", "true").strip().lower()
        diarization_enabled = diarization_raw in {"1", "true", "yes", "on"}
        return cls(
            azure_tenant_id=os.getenv("AZURE_TENANT_ID"),
            azure_client_id=os.getenv("AZURE_CLIENT_ID"),
            azure_client_secret=os.getenv("AZURE_CLIENT_SECRET"),
            azure_speech_key=os.getenv("AZURE_SPEECH_KEY"),
            azure_speech_region=os.getenv("AZURE_SPEECH_REGION"),
            graph_site_id=os.getenv("GRAPH_SITE_ID"),
            graph_drive_id=os.getenv("GRAPH_DRIVE_ID"),
            teams_channel_id=os.getenv("TEAMS_CHANNEL_ID"),
            feature_diarization_enabled=diarization_enabled,
        )

    def require_keys(self, keys: list[str]) -> None:
        missing = [k for k in keys if not getattr(self, k)]
        if missing:
            raise PipelineError(
                code=ErrorCode.CONFIG_MISSING,
                message=f"Missing required environment variables: {', '.join(missing)}",
                recoverable=False,
                step="CONFIG",
            )

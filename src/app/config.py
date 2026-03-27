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
    teams_chat_id: str | None
    graph_api_base_url: str
    graph_scope: str
    graph_recording_extensions: tuple[str, ...]
    recording_download_dir: str
    feature_audio_preprocess_enabled: bool
    audio_preprocess_target_sample_rate: int
    audio_preprocess_target_channels: int
    feature_diarization_enabled: bool
    stt_language: str
    stt_phrase_list: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "AppConfig":
        load_dotenv()
        def _as_bool(raw: str | None, default: bool) -> bool:
            if raw is None:
                return default
            return raw.strip().lower() in {"1", "true", "yes", "on"}

        def _as_csv_tuple(raw: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
            if raw is None or not raw.strip():
                return default
            return tuple(item.strip() for item in raw.split(",") if item.strip())

        diarization_raw = os.getenv("FEATURE_DIARIZATION_ENABLED", "true").strip().lower()
        diarization_enabled = diarization_raw in {"1", "true", "yes", "on"}
        feature_audio_preprocess_enabled = _as_bool(os.getenv("FEATURE_AUDIO_PREPROCESS_ENABLED"), default=False)
        graph_recording_extensions = _as_csv_tuple(
            os.getenv("GRAPH_RECORDING_EXTENSIONS"),
            default=(".mp4", ".m4a", ".wav"),
        )
        stt_phrase_list = _as_csv_tuple(
            os.getenv("STT_PHRASE_LIST"),
            default=("LLM", "token", "tokens", "cost", "Azure OpenAI"),
        )
        return cls(
            azure_tenant_id=os.getenv("AZURE_TENANT_ID"),
            azure_client_id=os.getenv("AZURE_CLIENT_ID"),
            azure_client_secret=os.getenv("AZURE_CLIENT_SECRET"),
            azure_speech_key=os.getenv("AZURE_SPEECH_KEY"),
            azure_speech_region=os.getenv("AZURE_SPEECH_REGION"),
            graph_site_id=os.getenv("GRAPH_SITE_ID"),
            graph_drive_id=os.getenv("GRAPH_DRIVE_ID"),
            teams_channel_id=os.getenv("TEAMS_CHANNEL_ID"),
            teams_chat_id=os.getenv("TEAMS_CHAT_ID"),
            graph_api_base_url=os.getenv("GRAPH_API_BASE_URL", "https://graph.microsoft.com/v1.0"),
            graph_scope=os.getenv("GRAPH_SCOPE", "https://graph.microsoft.com/.default"),
            graph_recording_extensions=graph_recording_extensions,
            recording_download_dir=os.getenv("RECORDING_DOWNLOAD_DIR", "artifacts/downloads"),
            feature_audio_preprocess_enabled=feature_audio_preprocess_enabled,
            audio_preprocess_target_sample_rate=int(os.getenv("AUDIO_PREPROCESS_TARGET_SAMPLE_RATE", "16000")),
            audio_preprocess_target_channels=int(os.getenv("AUDIO_PREPROCESS_TARGET_CHANNELS", "1")),
            feature_diarization_enabled=diarization_enabled,
            stt_language=os.getenv("STT_LANGUAGE", "ko-KR"),
            stt_phrase_list=stt_phrase_list,
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

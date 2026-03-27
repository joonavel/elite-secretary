from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class PipelineStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class PipelineStep(str, Enum):
    STEP_1_COLLECT = "STEP_1_COLLECT"
    STEP_2_PREPROCESS = "STEP_2_PREPROCESS"
    STEP_3_STT = "STEP_3_STT"
    STEP_4_AGENT_A = "STEP_4_AGENT_A"
    STEP_5_AGENT_B = "STEP_5_AGENT_B"
    STEP_6_AGENT_C = "STEP_6_AGENT_C"
    STEP_6_AGENT_D = "STEP_6_AGENT_D"
    STEP_7_PUBLISH = "STEP_7_PUBLISH"


@dataclass(slots=True)
class MeetingContext:
    meeting_id: str
    chat_id: str | None = None
    meeting_title: str | None = None
    meeting_time: datetime | None = None
    message_hint: str | None = None
    local_recording_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RecordingAsset:
    file_path: str
    file_id: str | None = None
    source_link: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Transcript:
    text: str
    segments: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class Intent:
    request_type: str
    period_type: str
    period_value: str
    year: int
    scope_level: str
    metrics: list[str]
    confidence: float


@dataclass(slots=True)
class AggregatedMetric:
    team_name: str
    month: str
    token_usage: float
    cost_krw: float


@dataclass(slots=True)
class AggregationContext:
    metrics: list[AggregatedMetric]
    validation_warnings: list[str] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ArtifactMetadata:
    artifact_name: str
    artifact_path: str
    artifact_type: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class PublishedResult:
    destinations: list[str]


@dataclass(slots=True)
class StepLogEntry:
    step: PipelineStep
    status: PipelineStatus
    started_at: datetime
    ended_at: datetime | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    recoverable: bool | None = None


@dataclass(slots=True)
class PipelineRun:
    run_id: str
    meeting_context: MeetingContext
    status: PipelineStatus = PipelineStatus.PENDING
    step_logs: list[StepLogEntry] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class PipelineResult:
    run_id: str
    status: PipelineStatus
    artifacts: list[ArtifactMetadata] = field(default_factory=list)
    published_result: PublishedResult | None = None

    @staticmethod
    def new_pending() -> "PipelineResult":
        return PipelineResult(run_id=str(uuid4()), status=PipelineStatus.PENDING)

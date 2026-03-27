from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ErrorCode(str, Enum):
    CONFIG_MISSING = "CONFIG_MISSING"
    RECORDING_NOT_FOUND = "RECORDING_NOT_FOUND"
    STT_FAILED = "STT_FAILED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PIPELINE_STEP_FAILED = "PIPELINE_STEP_FAILED"
    PUBLISH_FAILED = "PUBLISH_FAILED"


@dataclass(slots=True)
class PipelineError(Exception):
    code: ErrorCode
    message: str
    recoverable: bool
    step: str | None = None

    def __str__(self) -> str:
        step_info = f" [step={self.step}]" if self.step else ""
        return f"{self.code}{step_info}: {self.message}"

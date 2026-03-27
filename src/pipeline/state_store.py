from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.domain.models import MeetingContext, PipelineRun, PipelineStatus, PipelineStep, StepLogEntry


class PipelineStateStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path("runtime_logs")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.runs: dict[str, PipelineRun] = {}

    def create_run(self, run_id: str, meeting_context: MeetingContext) -> PipelineRun:
        run = PipelineRun(run_id=run_id, meeting_context=meeting_context)
        self.runs[run_id] = run
        self._flush(run)
        return run

    def mark_run_status(self, run_id: str, status: PipelineStatus) -> None:
        run = self.runs[run_id]
        run.status = status
        self._flush(run)

    def mark_step_running(self, run_id: str, step: PipelineStep, input_summary: str | None = None) -> None:
        run = self.runs[run_id]
        run.step_logs.append(
            StepLogEntry(
                step=step,
                status=PipelineStatus.RUNNING,
                started_at=datetime.now(UTC),
                input_summary=input_summary,
            )
        )
        self._flush(run)

    def mark_step_finished(
        self,
        run_id: str,
        step: PipelineStep,
        status: PipelineStatus,
        output_summary: str | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        run = self.runs[run_id]
        for entry in reversed(run.step_logs):
            if entry.step == step and entry.status == PipelineStatus.RUNNING:
                entry.status = status
                entry.ended_at = datetime.now(UTC)
                entry.output_summary = output_summary
                if error:
                    entry.error_code = error.get("code")
                    entry.error_message = error.get("message")
                    entry.recoverable = error.get("recoverable")
                break
        self._flush(run)

    def _flush(self, run: PipelineRun) -> None:
        def _convert(obj: Any) -> Any:
            if isinstance(obj, datetime):
                return obj.isoformat()
            if hasattr(obj, "value"):
                return obj.value
            if isinstance(obj, dict):
                return {k: _convert(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_convert(v) for v in obj]
            return obj

        run_dict = _convert(asdict(run))
        target = self.base_dir / f"{run.run_id}.json"
        target.write_text(json.dumps(run_dict, ensure_ascii=True, indent=2), encoding="utf-8")

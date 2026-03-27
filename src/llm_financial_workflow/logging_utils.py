from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def make_step_log(
    run_id: str,
    step_name: str,
    status: str,
    input_summary: dict[str, Any] | None = None,
    output_summary: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "step_name": step_name,
        "status": status,
        "timestamp": utc_now(),
        "input_summary": input_summary or {},
        "output_summary": output_summary or {},
        "error_message": error_message,
    }

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    repo_root: Path
    openai_api_key: str
    openai_model: str
    excel_mcp_command: Path
    default_report_period: str
    default_output_dir: Path
    default_seed_csv_path: Path
    default_excel_report_name: str
    default_requests_dir: Path

    @classmethod
    def load(cls, repo_root: Path | None = None) -> "AppConfig":
        resolved_root = (repo_root or Path(__file__).resolve().parents[2]).resolve()
        load_dotenv(resolved_root / ".env")

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required in the environment or .env file.")

        excel_mcp_command = Path(
            os.getenv("EXCEL_MCP_COMMAND", resolved_root / "tools" / "excel-mcp" / "mcp-excel.exe")
        ).resolve()

        return cls(
            repo_root=resolved_root,
            openai_api_key=api_key,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.4").strip(),
            excel_mcp_command=excel_mcp_command,
            default_report_period=os.getenv("REPORT_PERIOD", "2025 H1").strip(),
            default_output_dir=Path(os.getenv("WORKFLOW_OUTPUT_DIR", resolved_root / "workflow_runs")).resolve(),
            default_seed_csv_path=Path(
                os.getenv("SEED_CSV_PATH", resolved_root / "data" / "seed" / "employee_llm_credit_usage.csv")
            ).resolve(),
            default_excel_report_name=os.getenv(
                "EXCEL_REPORT_NAME",
                "employee_llm_financial_report_2025_h1.xlsx",
            ).strip(),
            default_requests_dir=Path(
                os.getenv("WORKFLOW_REQUESTS_DIR", resolved_root / "data" / "requests")
            ).resolve(),
        )

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ExcelMCPService:
    def __init__(self, command_path: Path) -> None:
        self.command_path = command_path

    async def build_report(
        self,
        output_dir: Path,
        report_name: str,
        financial_csv_path: Path,
        cost_csv_path: Path,
        token_csv_path: Path,
        summary_csv_path: Path,
        support_payload: dict[str, Any],
        insight_document: dict[str, Any],
    ) -> Path:
        from langchain_mcp_adapters.client import MultiServerMCPClient
        from langchain_mcp_adapters.tools import load_mcp_tools

        report_path = output_dir / report_name
        client = MultiServerMCPClient(
            {
                "excel": {
                    "transport": "stdio",
                    "command": str(self.command_path),
                    "args": [],
                }
            }
        )

        async with client.session("excel") as session:
            tools = await load_mcp_tools(session)
            tool_map = {tool.name: tool for tool in tools}

            create_result = await self._call(tool_map, "file", {
                "action": "create",
                "path": self._to_windows_path(report_path),
                "show": False,
                "timeout_seconds": 300,
            })
            session_id = create_result["session_id"]

            for sheet_name in ["TeamMonthlyCost", "TeamMonthlyTokens", "TeamH1Summary", "Metadata", "Insights", "RawData"]:
                await self._call(tool_map, "worksheet", {
                    "action": "create",
                    "session_id": session_id,
                    "sheet_name": sheet_name,
                })
            await self._call(tool_map, "worksheet", {
                "action": "delete",
                "session_id": session_id,
                "sheet_name": "Sheet1",
            })

            await self._call(tool_map, "calculation_mode", {
                "action": "set-mode",
                "session_id": session_id,
                "mode": "manual",
            })

            await self._call(tool_map, "range", {
                "action": "set-values",
                "session_id": session_id,
                "sheet_name": "RawData",
                "range_address": "A1:I4801",
                "values_file": self._to_windows_path(financial_csv_path),
            })
            await self._call(tool_map, "range", {
                "action": "set-values",
                "session_id": session_id,
                "sheet_name": "TeamMonthlyCost",
                "range_address": "A1:I6",
                "values_file": self._to_windows_path(cost_csv_path),
            })
            await self._call(tool_map, "range", {
                "action": "set-values",
                "session_id": session_id,
                "sheet_name": "TeamMonthlyTokens",
                "range_address": "A1:I6",
                "values_file": self._to_windows_path(token_csv_path),
            })
            await self._call(tool_map, "range", {
                "action": "set-values",
                "session_id": session_id,
                "sheet_name": "TeamH1Summary",
                "range_address": "A1:E6",
                "values_file": self._to_windows_path(summary_csv_path),
            })

            await self._call(tool_map, "range", {
                "action": "set-values",
                "session_id": session_id,
                "sheet_name": "Metadata",
                "range_address": "A1:B14",
                "values": self._metadata_values(report_name, support_payload),
            })
            await self._call(tool_map, "range", {
                "action": "set-values",
                "session_id": session_id,
                "sheet_name": "Insights",
                "range_address": "A1:B12",
                "values": self._insight_values(support_payload, insight_document),
            })

            for action in [
                ("RawData", "RawFinancialData", "A1:I4801"),
                ("TeamMonthlyCost", "TeamMonthlyCostTable", "A1:I6"),
                ("TeamMonthlyTokens", "TeamMonthlyTokensTable", "A1:I6"),
                ("TeamH1Summary", "TeamH1SummaryTable", "A1:E6"),
            ]:
                await self._call(tool_map, "table", {
                    "action": "create",
                    "session_id": session_id,
                    "sheet_name": action[0],
                    "table_name": action[1],
                    "range_address": action[2],
                    "has_headers": True,
                })

            for sheet_name, range_address, format_code in [
                ("RawData", "H2:H4801", "#,##0"),
                ("RawData", "I2:I4801", "$#,##0.00"),
                ("TeamMonthlyCost", "B2:I6", "$#,##0.00"),
                ("TeamMonthlyTokens", "B2:I6", "#,##0"),
                ("TeamH1Summary", "B2:B6", "$#,##0.00"),
                ("TeamH1Summary", "C2:C6", "#,##0"),
                ("TeamH1Summary", "D2:D6", "0.00%"),
                ("TeamH1Summary", "E2:E6", "$#,##0.00"),
                ("Metadata", "B9:B14", "$#,##0.00"),
            ]:
                await self._call(tool_map, "range", {
                    "action": "set-number-format",
                    "session_id": session_id,
                    "sheet_name": sheet_name,
                    "range_address": range_address,
                    "format_code": format_code,
                })

            for sheet_name, range_address in [
                ("RawData", "A:I"),
                ("TeamMonthlyCost", "A:I"),
                ("TeamMonthlyTokens", "A:I"),
                ("TeamH1Summary", "A:E"),
                ("Metadata", "A:B"),
                ("Insights", "A:B"),
            ]:
                await self._call(tool_map, "range_format", {
                    "action": "auto-fit-columns",
                    "session_id": session_id,
                    "sheet_name": sheet_name,
                    "range_address": range_address,
                })

            await self._call(tool_map, "chart", {
                "action": "create-from-range",
                "session_id": session_id,
                "sheet_name": "TeamH1Summary",
                "chart_type": "ColumnClustered",
                "source_range_address": "A1:B6",
                "target_range": "G2:M18",
            })

            await self._call(tool_map, "calculation_mode", {
                "action": "calculate",
                "scope": "workbook",
                "session_id": session_id,
            })
            await self._call(tool_map, "calculation_mode", {
                "action": "set-mode",
                "session_id": session_id,
                "mode": "automatic",
            })
            await self._call(tool_map, "file", {
                "action": "close",
                "session_id": session_id,
                "save": True,
            })

        return report_path

    async def update_insights(
        self,
        report_path: Path,
        support_payload: dict[str, Any],
        insight_document: dict[str, Any],
    ) -> None:
        from langchain_mcp_adapters.client import MultiServerMCPClient
        from langchain_mcp_adapters.tools import load_mcp_tools

        client = MultiServerMCPClient(
            {
                "excel": {
                    "transport": "stdio",
                    "command": str(self.command_path),
                    "args": [],
                }
            }
        )

        async with client.session("excel") as session:
            tools = await load_mcp_tools(session)
            tool_map = {tool.name: tool for tool in tools}
            open_result = await self._call(tool_map, "file", {
                "action": "open",
                "path": self._to_windows_path(report_path),
                "show": False,
                "timeout_seconds": 300,
            })
            session_id = open_result["session_id"]
            await self._call(tool_map, "range", {
                "action": "set-values",
                "session_id": session_id,
                "sheet_name": "Insights",
                "range_address": "A1:B12",
                "values": self._insight_values(support_payload, insight_document),
            })
            await self._call(tool_map, "range_format", {
                "action": "auto-fit-columns",
                "session_id": session_id,
                "sheet_name": "Insights",
                "range_address": "A:B",
            })
            await self._call(tool_map, "file", {
                "action": "close",
                "session_id": session_id,
                "save": True,
            })

    async def _call(self, tool_map: dict[str, Any], tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        result = await tool_map[tool_name].ainvoke(payload)
        if isinstance(result, list) and result:
            first = result[0]
            if isinstance(first, dict) and "text" in first:
                result = first["text"]
        if isinstance(result, str):
            try:
                parsed = json.loads(result)
            except json.JSONDecodeError:
                return {"raw": result}
            if parsed.get("success") is False:
                raise RuntimeError(parsed.get("errorMessage", f"{tool_name} failed"))
            return parsed
        if isinstance(result, dict):
            if result.get("success") is False:
                raise RuntimeError(result.get("errorMessage", f"{tool_name} failed"))
            return result
        return {"raw": result}

    def _metadata_values(self, report_name: str, support_payload: dict[str, Any]) -> list[list[str]]:
        monthly_totals = support_payload["insights_seed"]["monthly_totals"]
        return [
            ["Field", "Value"],
            ["Report Period", support_payload["report_period"]],
            ["Data Source", support_payload["data_source"]],
            ["Generated By", "LangGraph FR4-FR11 workflow"],
            ["Seed", str(support_payload["seed"])],
            ["Source Workbook", report_name],
            ["", ""],
            ["Month", "All Teams Cost (USD)"],
            *[[month, monthly_totals[month]] for month in support_payload["months"]],
        ]

    def _insight_values(self, support_payload: dict[str, Any], insight_document: dict[str, Any]) -> list[list[str]]:
        return [
            ["Section", "Content"],
            ["Insight 1", insight_document["insights"][0]],
            ["Insight 2", insight_document["insights"][1]],
            ["Insight 3", insight_document["insights"][2]],
            ["Pattern 1", insight_document["patterns"][0]],
            ["Pattern 2", insight_document["patterns"][1]],
            ["Recommendation 1", insight_document["recommendations"][0]],
            ["Recommendation 2", insight_document["recommendations"][1]],
            ["Recommendation 3", insight_document["recommendations"][2]],
            ["", ""],
            ["Report Period", support_payload["report_period"]],
            ["H1 Total Cost", support_payload["totals"]["h1_total_cost_usd"]],
        ]

    def _to_windows_path(self, path: Path) -> str:
        resolved = path.resolve()
        path_str = resolved.as_posix()
        if path_str.startswith("/mnt/") and len(path_str) > 6:
            drive = path_str[5].upper()
            remainder = path_str[6:]
            return f"{drive}:{remainder}".replace("/", "\\")
        return str(resolved)

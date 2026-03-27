# Hackathon Dataset And Reporting Design

## 1. Purpose

This project now uses a two-layer data design instead of a single spreadsheet-friendly table.

- Seed dataset: compact employee-level wide table used to define synthetic usage tendencies.
- Financial source dataset: long-format analytical table used for FR-4 and FR-5.
- Reporting outputs: monthly-wide summary tables and Excel artifacts used for FR-6 and FR-7.

The split exists because database-style querying and human-readable reporting have different optimal shapes.

## 2. Dataset Layers

### 2.1 Seed dataset

Recommended table name: `employee_llm_credit_usage`

This is the original employee-level seed table. It is still kept, but it is no longer the final reporting source.

| Column name | Type | Description |
|---|---|---|
| `employee_id` | `INT` | Unique employee identifier |
| `employee_name` | `TEXT` | Employee name |
| `employee_type` | `TEXT` | `developer` or `non_developer` |
| `openai_main_credit` | `NUMERIC(10,2)` | OpenAI main model credit tendency |
| `openai_small_credit` | `NUMERIC(10,2)` | OpenAI small model credit tendency |
| `google_main_credit` | `NUMERIC(10,2)` | Google main model credit tendency |
| `google_small_credit` | `NUMERIC(10,2)` | Google small model credit tendency |
| `claude_main_credit` | `NUMERIC(10,2)` | Claude main model credit tendency |
| `claude_small_credit` | `NUMERIC(10,2)` | Claude small model credit tendency |
| `xai_main_credit` | `NUMERIC(10,2)` | xAI main model credit tendency |
| `xai_small_credit` | `NUMERIC(10,2)` | xAI small model credit tendency |
| `total_credit` | `NUMERIC(10,2)` | Total seed credit across the eight model columns |

Shape:

- One employee per row
- 100 rows total
- Wide format

Usage:

- Synthetic seed only
- Not the direct FR-4 reporting source

### 2.2 Financial source dataset

Recommended table name: `employee_llm_financial_usage_2025_h1`

This is the actual analytical source used by the workflow for FR-4 and FR-5.

| Column name | Type | Description |
|---|---|---|
| `year_month` | `TEXT` | Month key such as `2025-01` |
| `team_name` | `TEXT` | Synthetic team assignment |
| `employee_id` | `INT` | Employee identifier |
| `employee_name` | `TEXT` | Employee name |
| `employee_type` | `TEXT` | `developer` or `non_developer` |
| `provider` | `TEXT` | `OpenAI`, `Google`, `Claude`, `xAI` |
| `model_tier` | `TEXT` | `main` or `small` |
| `token_usage` | `INT` | Generated token usage |
| `cost_usd` | `NUMERIC(12,2)` | Generated USD cost |

Shape:

- One row per `employee x month x provider x model_tier`
- Current period: `2025 H1`
- 4,800 rows total
- Long format

Why long format was chosen:

- Fits SQL-style aggregation and filtering
- Supports FR-4 team/month lookup cleanly
- Supports FR-5 aggregation and deterministic recomputation
- Extends cleanly if months or providers increase

## 3. Reporting Outputs

The workflow does not present the long-format source directly as the final business report.

Instead, it creates monthly-wide summary artifacts for readability.

### 3.1 Team monthly cost summary

File: `employee_llm_team_monthly_cost_2025_h1.csv`

Columns:

- `team_name`
- `2025-01` to `2025-06`
- `h1_total_cost_usd`
- `monthly_avg_cost_usd`

### 3.2 Team monthly token summary

File: `employee_llm_team_monthly_tokens_2025_h1.csv`

Columns:

- `team_name`
- `2025-01` to `2025-06`
- `h1_total_tokens`
- `monthly_avg_tokens`

### 3.3 Team H1 summary

File: `employee_llm_team_h1_summary_2025_h1.csv`

Columns:

- `team_name`
- `h1_total_cost_usd`
- `h1_total_tokens`
- `cost_share_pct`
- `monthly_avg_cost_usd`

### 3.4 Support payload

File: `employee_llm_report_support_2025_h1.json`

Contains:

- reporting period
- data source metadata
- aggregate totals
- insight seed values
- team summary blocks

### 3.5 Excel report

File: `employee_llm_financial_report_2025_h1.xlsx`

Workbook sheets:

- `RawData`
- `TeamMonthlyCost`
- `TeamMonthlyTokens`
- `TeamH1Summary`
- `Metadata`
- `Insights`

## 4. Generation Rules

### 4.1 Seed generation

- 100 employees are generated deterministically.
- Population split is 50 developers and 50 non-developers.
- Each employee gets a total seed credit first.
- That total is split across eight provider/model columns.
- Developers skew higher and more main-model-heavy.
- Non-developers skew lower and more small-model-heavy.

### 4.2 Financial source generation

- Each employee is assigned to one of five fixed teams:
  - `Platform`
  - `Product`
  - `Data`
  - `Security`
  - `Operations`
- Seed credits are converted into H1 cost tendencies using provider/model multipliers.
- H1 cost is spread across January to June with deterministic month weights.
- Token usage is derived from cost using provider/model tier pricing rules.
- Output is deterministic for a fixed random seed.

## 5. Workflow Relationship

This design is aligned to the implemented workflow boundaries.

- FR-4: reads and validates the long-format financial source
- FR-5: aggregates into monthly-wide summaries
- FR-6: writes the Excel report through Excel MCP
- FR-7: generates structured insights with `gpt-5.4`
- FR-8 to FR-10: handled by the LangGraph orchestration, logs, and failure reporting
- FR-11: Excel generation and insight generation run in parallel branches

FR-1 to FR-3 are intentionally out of scope for this stage.

## 6. Deliverables

### Seed assets

- `data/seed/employee_llm_credit_usage.csv`
- `data/seed/employee_llm_credit_usage.sql`

### Manual sample generation assets

- `data/generated/manual/employee_llm_financial_usage_2025_h1.csv`
- `data/generated/manual/employee_llm_financial_usage_2025_h1.sql`
- `data/generated/manual/employee_llm_team_monthly_cost_2025_h1.csv`
- `data/generated/manual/employee_llm_team_monthly_tokens_2025_h1.csv`
- `data/generated/manual/employee_llm_team_h1_summary_2025_h1.csv`
- `data/generated/manual/employee_llm_report_support_2025_h1.json`
- `data/generated/manual/employee_llm_financial_report_2025_h1.xlsx`

### Generator / workflow code

- `scripts/generate_llm_credit_db.py`
- `src/llm_financial_workflow/`

### Workflow run outputs

- `workflow_runs/<run_id>/...`

## 7. Suggested Usage

- Use the seed dataset when synthetic employee behavior needs to be regenerated.
- Use the long-format financial dataset for database-style queries and aggregation.
- Use the summary CSVs and Excel workbook for human review and demo reporting.
- Use `uv run llm-financial-workflow ...` for end-to-end FR-4 to FR-11 execution.

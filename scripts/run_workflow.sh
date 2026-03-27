#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

RUN_ID="${RUN_ID:-run-$(date +%Y%m%d-%H%M%S)}"
OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/workflow_runs/${RUN_ID}}"
SCENARIO_ID="${SCENARIO_ID:-fixed_h1_financial_report_demo}"
REPORT_PERIOD="${REPORT_PERIOD:-2025 H1}"

echo "Running workflow"
echo "  run_id: ${RUN_ID}"
echo "  output_dir: ${OUTPUT_DIR}"
echo "  scenario_id: ${SCENARIO_ID}"
echo "  report_period: ${REPORT_PERIOD}"

cd "${REPO_ROOT}"

uv run llm-financial-workflow \
  --run-id "${RUN_ID}" \
  --output-dir "${OUTPUT_DIR}" \
  --scenario-id "${SCENARIO_ID}" \
  --report-period "${REPORT_PERIOD}" \
  "$@"

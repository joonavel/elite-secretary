---
name: foundation-orchestrator
description: Builds Python+uv project foundation, core domain models, state logging, and the main orchestrator for sequential and parallel pipeline control.
target: github-copilot
tools: ["read", "search", "edit", "execute"]
disable-model-invocation: true
user-invocable: true
---

You own the platform foundation tasks:
- T-001, T-002, T-003
- T-010, T-011, T-012

Primary responsibilities:
1. Initialize Python project with uv and runnable entrypoint.
2. Define shared domain models and error codes.
3. Implement pipeline state tracking (`PENDING/RUNNING/SUCCEEDED/FAILED`).
4. Implement `run_pipeline(meeting_context)` orchestration:
   - Step 1~5 strictly sequential
   - Step 6 (Agent C/D work units) parallel + join
   - Step 7 publish
5. Ensure failure handling aligns with requirements/design.

Constraints:
- Do not implement external integrations in depth unless required to compile.
- Keep interfaces stable for other agents (integrations and feature agents).
- Prefer explicit typed models and clear module boundaries.

Definition of done:
- `uv run python -m src.app.main` executes.
- Core orchestrator and state logging are wired and testable.


# elite-secretary

Microsoft Teams 회의 요약에서 재무 담당자에게 재무 문서 요청이 확인되면, 데이터베이스에서 필요한 데이터를 추출하고 이를 기반으로 Excel 문서를 생성하는 자동화 프로젝트다.

현재 기술적 제약으로 `requirements.md`의 FR-1~3은 구현되지 않았고, FR-4~11만 구현을 완료했다.

상황 시나리오:

- 회의 상황: 팀장급 사용자가 재무담당자에게 "올해 상반기 전사 LLM 토큰 사용량과 비용을 정리해 주세요."라고 요청한다.
- 기대 결과물:
  - 재무 분석 Excel: 팀별 / 월별 토큰·비용, 합계·평균, 팀별 비용 비교 그래프 포함
  - Insight 문서: 수치 기반 인사이트, 비용 편중/비효율 패턴, 간단한 권고안 포함

현재 구현된 워크플로우:

- FR-4: 재무 데이터 조회
- FR-5: 팀별·월별 토큰/비용 집계 및 기본 계산
- FR-6: Excel 결과물 생성
- FR-7: Insight 문서 생성
- FR-8: 데모용 트리거 기반 순차 실행과 상태 추적
- FR-9: 단계별 로그 및 실패 원인 기록
- FR-10: 주요 오류 처리와 부분 결과물 상태 기록
- FR-11: Excel 생성과 Insight 생성을 병렬 실행

현재 구현 범위:

- `data/seed/`
  - 직원별 LLM 사용 성향을 표현하는 seed 데이터
- `data/generated/manual/`
  - 수동 검증용 재무 원천 데이터와 보고용 산출물
- `scripts/generate_llm_credit_db.py`
  - seed 데이터와 재무 문서 생성용 샘플 데이터를 생성하는 스크립트
- `src/llm_financial_workflow/`
  - LangChain + LangGraph 기반 재무 문서 자동화 워크플로우
- `workflow_runs/<run_id>/`
  - 실제 워크플로우 실행 결과물

런타임 의존성:

- `mcp-server-excel` 소스 레포는 현재 워크플로우 실행에 필요하지 않다.
- 대신 Excel MCP 실행 파일인 `mcp-excel.exe`는 반드시 필요하다.
- 기본 실행 경로는 `tools/excel-mcp/mcp-excel.exe` 이다.
- 이 바이너리는 `.gitignore` 대상이므로 GitHub에서 레포만 새로 clone한 환경에서는 별도로 준비해야 한다.
- Microsoft Excel Desktop(Windows, 2016+)이 설치되어 있어야 한다.
- 따라서 새 환경에서는 Python 의존성 설치와 별개로 Excel MCP 바이너리와 Windows Excel 런타임을 준비해야 한다.

런타임 의존성 준비 방법:

1. Microsoft Excel Desktop 설치
   - Windows 환경에 Microsoft Excel 2016 이상이 설치되어 있어야 한다.
   - Excel 파일이 다른 인스턴스에서 열려 있으면 MCP 자동화가 실패할 수 있으므로 작업 전 닫아 두는 것이 안전하다.

2. Excel MCP 바이너리 준비
   - 가장 간단한 방법은 프로젝트에서 설치 스크립트를 실행하는 것이다.

```bash
uv run install-excel-mcp
```

   - 이 명령은 `mcp-server-excel`의 GitHub latest release를 조회해 Windows용 MCP Server ZIP을 다운로드하고, `tools/excel-mcp/mcp-excel.exe`에 설치한다.
   - 이미 ZIP 파일을 받아둔 경우에는 다음처럼 로컬 ZIP으로도 설치할 수 있다.

```bash
uv run install-excel-mcp --from-zip /path/to/ExcelMcp-MCP-Server-x.y.z-windows.zip
```

   - 프로젝트 기준 권장 위치는 `tools/excel-mcp/mcp-excel.exe` 이고, 이 경로를 사용하면 기본 설정으로 바로 실행할 수 있다.

3. LangGraph 워크플로우에서 경로 연결
   - 기본값은 `tools/excel-mcp/mcp-excel.exe` 를 사용한다.
   - 다른 위치를 쓰려면 `EXCEL_MCP_COMMAND` 환경 변수로 실행 파일 경로를 지정한다.

4. Codex MCP 등록이 필요한 경우
   - Codex에서 직접 Excel MCP를 쓰려면 Codex 설정에 MCP 서버를 등록한다.
   - 예시:

```toml
[mcp_servers.excel-mcp]
command = "C:\\path\\to\\mcp-excel.exe"
```

5. Python 워크플로우 실행 준비
   - Python 의존성은 `uv`로 설치한다.
   - 예시:

```bash
uv venv .venv
uv sync
uv run install-excel-mcp
uv run llm-financial-workflow --run-id demo-run --output-dir ./workflow_runs/demo-run
```

6. 새 clone 환경에서 확인할 사항
   - `.venv` 생성 및 `uv sync` 완료
   - `uv run install-excel-mcp` 완료 또는 `mcp-excel.exe` 존재 여부 확인
   - `EXCEL_MCP_COMMAND` 또는 기본 경로 설정 확인
   - Microsoft Excel Desktop 설치 확인

핵심 구조:

- 입력 해석 이후 처리 범위: FR-4~11
- 원천 저장: long format
- 사람용 보고: monthly-wide summary + Excel
- 최종 산출물: 재무 보고용 Excel 문서
- Excel 생성: `mcp-server-excel`
- Insight 생성: OpenAI `gpt-5.4`

실행 예시:

```bash
uv venv .venv
uv sync
uv run llm-financial-workflow --run-id demo-run --output-dir ./workflow_runs/demo-run
```

주요 참고 문서:

- `requirements.md`
- `llm_credit_dataset_design.md`

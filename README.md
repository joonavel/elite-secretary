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

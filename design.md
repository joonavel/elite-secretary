# Design Specification

## 0. 문서 목적
- `requirements.md`를 구현 가능한 아키텍처/모듈 설계로 구체화한다.
- 구현 언어는 **Python**, 의존성/실행 환경 관리는 **uv**를 기준으로 한다.

## 1. 비판적 검토 결과 (입력안 기준)

### 1.1 Graph 접근 스택
- `[msal | azure-identity] + [requests/httpx | msgraph-sdk]` 조합은 가능하나, 혼용 시 인증/재시도/에러 처리 중복 위험이 있다.
- 해커톤 목표(실동작 데모) 기준으로는:
  - 인증: `azure-identity`
  - 호출: `httpx`
  - 방식이 가장 단순하고 디버깅이 쉽다.
- `msgraph-sdk`는 타입 안정성 장점이 있으나 학습비용/추상화 복잡도가 증가한다.

### 1.2 Teams 녹음 획득
- “meeting recordings API” 단일 경로만 가정하면 실패 가능성이 있다(테넌트 정책/저장 위치 차이).
- 본 설계는 요구사항(FR-1.1)에 맞춰 **Teams 채팅 기반 획득 경로를 기본 경로**로 사용한다.
- 실패 시에는 즉시 실패를 반환하고, 재시도 가능한 에러 코드와 운영 가이드를 함께 기록한다.

### 1.3 STT + Diarization
- `Azure Speech SDK File Input`은 요구사항과 부합.
- diarization은 요구사항과 동일하게 **best-effort + feature flag(기본 on)** 으로 설계한다.

### 1.4 Foundry Agent 오케스트레이션
- 선택 도입은 타당하나, 해커톤 MVP에서는 외부 오케스트레이터 의존성이 실패 요인이 될 수 있다.
- 기본은 **내장 오케스트레이터(Python workflow)** 로 구현하고, Foundry는 어댑터 레이어로 분리한다.

### 1.5 엑셀/문서 생성
- `pandas + openpyxl + python-docx` 조합은 적절.
- 차트는 `openpyxl.chart`로 충족 가능하며, 문서에는 “수치 근거 출처 셀/시트 참조”를 남겨 추적성을 확보한다.

## 2. 아키텍처 개요

파이프라인은 단일 실행 단위 `run_pipeline(meeting_context)`로 시작한다.

1. Recording Collector  
2. Audio Preprocessor (옵션)  
3. STT Processor  
4. Agent A (요약/의도 추출)  
5. Agent B (재무 데이터 로드/집계)  
6. Agent C (Excel 생성) + Agent D (Insight 문서 생성) **병렬**  
7. Publisher (SharePoint 업로드 + Teams 알림)  
8. Run Logger / Artifact Registry

## 3. 런타임 흐름 (FR 매핑)

### Step 1. 회의 녹음 수집 (FR-1)
- 입력: `meeting_id | chat_id | message_hint`
- 출력: `recording_file_path`, `recording_metadata`

### Step 2. 오디오 전처리 (옵션)
- 조건: 포맷/코덱이 STT 요구 조건 미충족일 때만 수행
- 출력: STT 친화 포맷(예: wav/mono/16k)

### Step 3. STT (FR-2)
- Azure Speech SDK File Input으로 텍스트화
- Phrase List 적용
- diarization 설정은 feature flag(기본 on)로 best-effort 적용
- 출력: `transcript.json` (세그먼트, 타임스탬프, 화자정보(옵션))

### Step 4. Agent A: 요약/의도 추출 (FR-3)
- 입력: transcript
- 출력:
  - `meeting_summary.md`
  - `intent.json` (예: `period=H1`, `metric=[token,cost]`, `scope=org/team`)

### Step 5. Agent B: 데이터 조회/집계 (FR-4, FR-5)
- 입력: `intent.json`, 재무 원천 Excel
- 처리:
  - 컬럼 정규화
  - 기간 필터(H1 default)
  - 팀/월 집계, 총합/평균 계산
- 출력:
  - `aggregated_metrics.csv`
  - `aggregation_context.json` (`validation_warnings[]`, `validation_errors[]` 포함)

### Step 6. Agent C/D 병렬 생성 (FR-6, FR-7, FR-11)
- Agent C: Excel 리포트 생성 + 차트
- Agent D: Insight 문서 생성
- 병렬 후 Join 단계에서 결과물 무결성 체크

### Step 7. 배포/공유 (FR-8)
- SharePoint 업로드
- Teams 메시지로 결과 링크 전송

### Step 8. 로깅/상태관리 (FR-9, FR-10)
- 단계별 상태 전이 기록: `PENDING → RUNNING → SUCCEEDED | FAILED`
- 실패 시 단계/원인/재시도 가능 여부 기록

## 4. 모듈 설계 (Python 패키지 구조)

```text
src/
  app/
    main.py                      # 엔트리포인트
    config.py                    # 환경변수/설정 로딩
  integrations/
    graph_client.py              # Graph 인증/호출(httpx)
    teams_recording_resolver.py  # 녹음 파일 위치 탐색
    speech_stt.py                # Azure Speech SDK wrapper
    sharepoint_publisher.py      # 결과 업로드/링크 생성
    teams_notifier.py            # Teams 메시지 전송
  pipeline/
    orchestrator.py              # 전체 단계 제어
    state_store.py               # 실행 상태/로그 저장
  agents/
    agent_a_intent.py            # 요약/의도 추출
    agent_b_aggregation.py       # 데이터 조회/집계
    agent_c_excel.py             # Excel 생성
    agent_d_insight.py           # 문서 생성
  domain/
    models.py                    # dataclass/pydantic 모델
    errors.py                    # 명시적 에러 타입
  io/
    excel_reader.py              # 원천 Excel 로드/검증
    excel_writer.py              # 결과 Excel 작성
    doc_writer.py                # 문서 작성
  utils/
    time_utils.py
    logging_utils.py
```

## 5. 데이터 계약 (Data Contracts)

### 5.1 Intent 스키마 (`intent.json`)
```json
{
  "request_type": "llm_cost_analysis",
  "period": {"type": "half", "value": "H1", "year": 2026},
  "scope": {"level": "organization", "teams": []},
  "metrics": ["token_usage", "cost"],
  "confidence": 0.0
}
```

### 5.2 집계 테이블 컬럼(내부 표준)
- `team_name`
- `month` (`YYYY-MM`)
- `token_usage`
- `cost_krw` (또는 프로젝트 표준 통화)
- `source_row_id`

### 5.3 산출물 메타데이터
- `report_generated_at`
- `source_file_version`
- `period_applied`
- `pipeline_run_id`

## 6. 외부 의존성 설계 (Python + uv)

## 6.1 필수 의존성
- HTTP/인증
  - `httpx`
  - `azure-identity`
- STT
  - `azure-cognitiveservices-speech`
- 데이터 처리/파일
  - `pandas`
  - `openpyxl`
  - `python-docx`
- 설정/모델/유틸
  - `pydantic`
  - `python-dotenv`

## 6.2 선택 의존성
- 오디오 전처리
  - `pydub` (ffmpeg 바이너리 필요)
- 오케스트레이션 확장
  - `langchain-core`
  - `langchain-azure-ai`

## 6.3 의존성 정책
- 패키지 관리는 `uv add`, 실행은 `uv run`, 잠금은 `uv lock` 기준
- 런타임 필수/선택 의존성 분리(`extras`) 권장

## 7. 오케스트레이션 설계

### 7.1 기본 실행 정책
- 순차 단계(고정): 수집 → 전처리 → STT → Agent A → Agent B
- 병렬 단계(유일): Agent C/Agent D
- Join 후 publish

### 7.2 실패 정책
- `Collector/STT/Aggregation` 실패: 파이프라인 실패 종료
- `Publisher` 실패: 파이프라인 실패 처리
- 각 실패는 `error_code`, `error_message`, `recoverable` 플래그 기록
- 검증 정책:
  - `validation_errors[]` 존재 시 실패 종료
  - `validation_warnings[]`만 존재 시 계속 진행

### 7.3 재실행 정책
- `run_id` 기준 멱등성 키 사용
- 이미 생성된 중간 산출물은 checksum 확인 후 재사용 가능

## 8. 보안/권한/설정

### 8.1 환경변수
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET` (또는 Managed Identity)
- `AZURE_SPEECH_KEY`
- `AZURE_SPEECH_REGION`
- `GRAPH_SITE_ID`, `GRAPH_DRIVE_ID`, `TEAMS_CHANNEL_ID` 등

### 8.2 권한 최소화
- Graph API는 파일 읽기/업로드/메시지 전송 최소 scope만 부여
- 비밀정보는 `.env` 또는 배포 환경 secret store 사용

## 9. 테스트 전략

### 9.1 단위 테스트
- 의도 파싱
- 집계 로직(기간 필터, 그룹핑, 합계/평균)
- Excel/Doc 생성 함수

### 9.2 통합 테스트
- 샘플 녹음 + 샘플 재무 Excel로 E2E dry-run
- Graph/Speech는 mock 또는 sandbox 자격 증명 사용

### 9.3 데모 시나리오 검증
- 5~10분 회의 음성 입력 기준 처리 완료
- Excel 그래프 생성 확인
- Insight 문서 생성 확인
- 10분 회의 녹음 기준 파이프라인 10분 이내 완료(외부 API 지연 제외)

## 10. 구현 우선순위 (MVP)
1. 로컬 파일 입력 기반 E2E(Teams/SharePoint 없이)
2. Graph 연동으로 녹음 수집/결과 업로드 추가
3. Teams 알림 자동화 추가
4. Foundry 오케스트레이션 어댑터 추가(선택)

## 11. 결정 사항 요약
- 언어/패키지 관리: **Python + uv**
- 오케스트레이션: 기본 내장 워크플로우, Foundry는 선택 어댑터
- 데이터 원천: 사내 재무 Excel 고정
- FR-6/FR-7: 병렬 실행 설계
- diarization: best-effort

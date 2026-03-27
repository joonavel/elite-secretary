# Tasks Specification

## 0. 목적
`requirements.md`와 `design.md`를 구현 작업 단위로 분해한 실행 계획이다.

## 1. 작업 원칙
- 언어/환경: Python + `uv`
- 실행 흐름: Step 1~5 순차, Step 6(C/D) 병렬, Step 7 배포
- 완료 기준: 각 Task의 DoD(Definition of Done) 충족

## 2. Milestone
- M1: 로컬 E2E 파이프라인 동작(Teams/SharePoint 제외)
- M2: Graph 연동(녹음 수집 + 결과 업로드 + Teams 알림)
- M3: 안정화(오류/로그/테스트/데모 리허설)

## 3. Task Breakdown

### Phase A. 프로젝트 부트스트랩

#### T-001 프로젝트 초기화
- 작업:
  - `uv init` 기반 프로젝트 초기화
  - 기본 디렉터리 구조 생성(`src/app`, `src/pipeline`, `src/agents`, `src/integrations`, `src/io`, `src/domain`, `tests`)
  - 실행 엔트리포인트(`src/app/main.py`) 연결
- DoD:
  - `uv run python -m src.app.main` 실행 가능

#### T-002 의존성 구성
- 작업:
  - 필수 의존성 추가: `httpx`, `azure-identity`, `azure-cognitiveservices-speech`, `pandas`, `openpyxl`, `python-docx`, `pydantic`, `python-dotenv`
  - 선택 의존성(extras) 분리: `pydub`, `langchain-core`, `langchain-azure-ai`
- DoD:
  - `pyproject.toml`/lock 업데이트 완료
  - 설치 후 import smoke test 통과

#### T-003 설정/비밀정보 로더
- 작업:
  - 환경변수 스키마 정의(`src/app/config.py`)
  - 필수/선택 키 검증 로직 구현
- DoD:
  - 누락 시 명확한 에러 메시지 출력

---

### Phase B. 코어 도메인/파이프라인

#### T-010 도메인 모델/에러 모델
- 작업:
  - `meeting_context`, `intent`, `aggregation_context`, `artifact_metadata` 모델 정의
  - 표준 에러 코드/예외 타입 정의
- DoD:
  - 파이프라인 전 단계에서 공통 모델 사용

#### T-011 상태 저장/실행 로깅
- 작업:
  - 상태 전이(`PENDING/RUNNING/SUCCEEDED/FAILED`) 기록 모듈 구현
  - 단계별 입력/출력 요약 및 에러 로그 구조화
- DoD:
  - 실행 후 run log 파일 생성 및 단계별 상태 확인 가능

#### T-012 오케스트레이터 구현
- 작업:
  - `run_pipeline(meeting_context)` 구현
  - Step 1~5 순차 실행
  - Step 6(Agent C/D) 병렬 실행 + join
  - Step 7 배포 실행
- DoD:
  - 정상 실행 시 최종 상태 `SUCCEEDED`
  - 실패 시 실패 단계/원인 기록

---

### Phase C. 기능 구현 (FR 중심)

#### T-020 녹음 파일 수집(Teams 채팅 기반)
- 작업:
  - Graph 인증(`azure-identity`) + `httpx` 클라이언트 구현
  - Teams 채팅 attachment에서 녹음 파일 탐색/다운로드 구현
  - 메타데이터(회의명/시간/링크/파일ID) 저장
- DoD:
  - 샘플 chat 기준 mp4/m4a 파일 다운로드 성공

#### T-021 오디오 전처리(옵션)
- 작업:
  - 포맷/코덱 검사
  - 필요 시 ffmpeg 기반 변환(wav/mono/16k)
- DoD:
  - STT 입력 호환 포맷 보장

#### T-022 STT 처리
- 작업:
  - Azure Speech SDK File Input STT 구현
  - Phrase List 적용
  - diarization feature flag(기본 on), best-effort 로직 구현
- DoD:
  - `transcript.json` 생성
  - diarization 실패 시 STT는 계속 진행 + 로그 기록

#### T-023 Agent A (요약/의도 추출)
- 작업:
  - transcript 요약 생성
  - `intent.json` 구조화(기간/스코프/지표/confidence)
- DoD:
  - H1 요청 케이스에서 `intent.period=H1` 파싱 성공

#### T-024 Agent B (재무 조회/집계)
- 작업:
  - 원천 Excel 로드 및 컬럼 정규화
  - 기간 필터/팀·월 그룹핑/총합·평균 산출
  - `validation_warnings[]`, `validation_errors[]` 생성
- DoD:
  - `aggregated_metrics.csv` 생성
  - 검증 정책 준수(error면 중단, warning만이면 진행)

#### T-025 Agent C (Excel 리포트 생성)
- 작업:
  - 결과 시트 구성(팀별/월별/합계/평균)
  - 그래프 최소 1개 생성
  - 메타정보(기간/원천/생성시각/run_id) 추가
- DoD:
  - 결과 Excel 생성 + 그래프 확인 가능

#### T-026 Agent D (Insight 문서 생성)
- 작업:
  - 집계 근거 기반 인사이트 작성
  - 비용 편중/비효율 패턴 분석 + 권고안 포함
- DoD:
  - 인사이트 최소 2개, 각 인사이트 수치 근거 1개 이상 포함

#### T-027 Publisher (업로드/알림)
- 작업:
  - SharePoint 업로드 구현
  - Teams 결과 메시지 전송 구현(링크 포함)
- DoD:
  - 업로드 URL 및 전송 로그 확인 가능

---

### Phase D. 테스트/검증/데모

#### T-030 단위 테스트
- 작업:
  - 의도 파싱, 집계 로직, Excel/Doc 생성 테스트
- DoD:
  - 핵심 함수 단위 테스트 통과

#### T-031 통합 테스트(E2E dry-run)
- 작업:
  - 샘플 녹음 + 샘플 재무 Excel로 전체 실행 검증
- DoD:
  - Step 1~7 성공 + 최종 `SUCCEEDED`
  - 산출물(Excel/Doc) 생성 확인

#### T-032 성능 검증
- 작업:
  - 10분 녹음 입력 기준 처리시간 측정(외부 API 지연 제외)
- DoD:
  - 10분 이내 완료

#### T-033 데모 시나리오 고정
- 작업:
  - 데모 입력/출력/실행 커맨드/복구 시나리오 정리
- DoD:
  - 해커톤 리허설 1회 이상 통과

## 4. 의존성(선후관계)
- T-001 → T-002 → T-003
- T-010 → T-011 → T-012
- T-020/T-021/T-022 → T-023 → T-024
- T-024 완료 후 T-025, T-026 병렬 가능
- T-025/T-026 완료 후 T-027
- 기능 구현 완료 후 T-030/T-031/T-032/T-033

## 5. 수용 기준 체크리스트(AC 매핑)
- AC-1: T-012 + T-031
- AC-2/AC-3: T-025
- AC-4: T-026
- AC-5: T-011

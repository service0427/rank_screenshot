# API 통합 가이드

## 개요

Coupang Agent V2는 이제 작업 할당 API와 결과 제출 API를 지원합니다.

## API 엔드포인트

### 1. 작업 할당 API
- **URL**: `http://61.84.75.37:3302/api/work/allocate-screenshot`
- **Method**: GET
- **Response**:
```json
{
  "success": true,
  "id": 4948534,
  "work_type": "screenshot",
  "site_code": "topr",
  "keyword": "사운드바",
  "product_id": "7227655664",
  "item_id": "18331882647",
  "vendor_item_id": "85810785808",
  "min_rank": 7
}
```

### 2. 작업 결과 제출 API
- **URL**: `http://localhost:3302/api/work/screenshot-result`
- **Method**: POST
- **Content-Type**: application/json
- **Request Body**:
```json
{
  "id": 4948534,
  "screenshot_url": "https://example.com/screenshot.png"
}
```
- **Response**:
```json
{
  "success": true,
  "message": "Result submitted successfully"
}
```

## 사용 방법

### 1. 작업 API 모드 (자동)
```bash
# Chrome 버전 지정
python3 agent.py --work-api --version 134

# VPN과 함께 사용
python3 agent.py --work-api --version 134 --vpn 1

# 버전 자동 선택 (랜덤)
python3 agent.py --work-api
```

**동작 흐름**:
1. 작업 할당 API에서 작업 정보 수신
2. 해당 키워드 및 상품 ID로 검색 수행
3. 스크린샷 캡처 및 업로드
4. 업로드된 URL을 작업 결과 제출 API로 전송
5. 자동 종료

### 2. 수동 모드 (기존 방식)
```bash
# CLI 파라미터로 직접 지정
python3 agent.py \
  --version 134 \
  --keyword "사운드바" \
  --product_id "7227655664" \
  --item_id "18331882647" \
  --vendor_item_id "85810785808"
```

**특징**:
- 작업 API를 사용하지 않음
- CLI 파라미터로 직접 상품 정보 지정
- 브라우저 수동 종료 (Enter 키 또는 창 닫기)

### 3. 설정 파일 모드
[agent.py](agent.py) 상단의 플래그 수정:
```python
# API 통합 설정
ENABLE_WORK_API = True  # 항상 작업 API 사용
```

이후 `python3 agent.py` 실행 시 자동으로 작업 API 모드로 동작

## 아키텍처

### 모듈 구조
```
agent.py (메인 진입점)
    ↓
run_work_api_mode() ─────┐
    ↓                    │
WorkAPIClient            │
    ↓                    │
allocate_work()          │
    ↓                    │
run_agent_selenium_uc() ←┘
    ↓
SearchWorkflow
    ↓
ScreenshotProcessor
    ↓
ScreenshotUploader ────→ upload.php
    ↓
(local_path, uploaded_url) ← 반환
    ↓
WorkAPIClient.submit_result() → screenshot-result API
```

### 주요 클래스

#### WorkAPIClient
- 위치: [lib/modules/work_api_client.py](lib/modules/work_api_client.py)
- 메서드:
  - `allocate_work()`: 작업 할당 API 호출
  - `submit_result(work_id, screenshot_url)`: 결과 제출

#### ScreenshotProcessor
- 위치: [lib/modules/screenshot_processor.py](lib/modules/screenshot_processor.py)
- 변경사항:
  - `capture_with_overlay()` 메서드 반환 타입 변경
  - **Before**: `Optional[str]` (로컬 경로만)
  - **After**: `tuple` → `(local_path, uploaded_url)`

#### SearchWorkflowResult
- 위치: [lib/workflows/search_workflow.py](lib/workflows/search_workflow.py)
- 추가 필드:
  - `before_screenshot_url`: 업로드된 스크린샷 URL
  - `after_screenshot_url`: 변경 후 스크린샷 URL (순위 변조용)

## 테스트

### 1. API 클라이언트 단위 테스트
```bash
python3 test_work_api.py
```

**확인 사항**:
- 작업 할당 API 연결
- 작업 정보 파싱 (id, keyword, product_id 등)

### 2. 통합 테스트
```bash
# 실제 작업 수행 (주의: 실제 작업이 생성됨)
python3 agent.py --work-api --version 134 --close
```

**확인 사항**:
- 작업 할당 → 검색 → 스크린샷 → 업로드 → 결과 제출 전체 흐름
- 브라우저 자동 종료 (--close 옵션)

## 오류 처리

### 작업 할당 실패
- API 서버 연결 실패 → 프로그램 종료
- 할당 가능한 작업 없음 → 프로그램 종료

### 스크린샷 업로드 실패
- 최대 3회 재시도
- 실패 시에도 로컬에 파일 보존
- 결과 제출 API 호출하지 않음

### 결과 제출 실패
- 경고 메시지 출력
- 작업은 할당된 상태로 남음
- 수동으로 재제출 가능

## 설정

### API URL 변경
[agent.py](agent.py) 상단:
```python
WORK_ALLOCATE_URL = "http://61.84.75.37:3302/api/work/allocate-screenshot"
WORK_RESULT_URL = "http://localhost:3302/api/work/screenshot-result"
```

### 타임아웃 조정
[lib/modules/work_api_client.py](lib/modules/work_api_client.py):
```python
def __init__(
    self,
    allocate_url: str = "...",
    result_url: str = "...",
    timeout: int = 30  # 기본 30초
):
```

## 프로덕션 배포

### 1. systemd 서비스 (권장)
```ini
[Unit]
Description=Coupang Screenshot Agent
After=network.target

[Service]
Type=simple
User=tech
WorkingDirectory=/home/tech/agent
ExecStart=/usr/bin/python3 /home/tech/agent/agent.py --work-api --version 134
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. cron (주기적 실행)
```cron
# 10분마다 실행
*/10 * * * * cd /home/tech/agent && python3 agent.py --work-api --version 134 --close
```

### 3. 무한 루프 (단순)
```bash
#!/bin/bash
while true; do
    python3 agent.py --work-api --version 134 --close
    sleep 60  # 60초 대기 후 다음 작업
done
```

## 모니터링

### 로그 확인
```bash
# systemd 서비스
journalctl -u coupang-agent -f

# 파일 로그 (리다이렉션)
python3 agent.py --work-api --version 134 >> /var/log/coupang-agent.log 2>&1
```

### 성공률 추적
```bash
# 성공 개수
grep -c "✅ 작업 ID .* 결과 제출 완료" /var/log/coupang-agent.log

# 실패 개수
grep -c "⚠️  작업 ID .* 결과 제출 실패" /var/log/coupang-agent.log
```

## 문제 해결

### Q: 작업 할당 API가 "Not found" 오류
A: URL이 올바른지 확인. 서버가 실행 중인지 확인.

### Q: 결과 제출 API가 localhost:3302에 연결 불가
A:
- 로컬 서버가 실행 중인지 확인
- 포트 3302가 열려있는지 확인
- 필요시 URL을 실제 서버 IP로 변경

### Q: 스크린샷 업로드 후 URL이 None
A:
- 업로드 서버 응답에 `url` 필드가 있는지 확인
- [screenshot_uploader.py](lib/modules/screenshot_uploader.py)의 응답 파싱 로직 확인

### Q: VPN과 함께 사용 시 문제
A:
- VPN 모드에서는 `--work-api` 옵션과 함께 사용
- 예: `python3 agent.py --work-api --version 134 --vpn 1`

## 변경 이력

### 2025-11-02
- 작업 API 통합 구현
- `WorkAPIClient` 모듈 추가
- `ScreenshotProcessor` 반환 타입 변경 (tuple)
- `SearchWorkflowResult`에 `before_screenshot_url` 필드 추가
- `--work-api` CLI 옵션 추가

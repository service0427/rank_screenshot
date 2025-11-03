# 작업 결과 제출 API 명세서

## 개요

Coupang Agent가 스크린샷 작업 완료 후 결과를 제출하는 API의 상세 명세입니다.

**업데이트 날짜**: 2025-11-03
**버전**: 2.0

---

## API 엔드포인트

### 작업 결과 제출 (Screenshot Result Submission)

- **URL**: `http://61.84.75.37:3302/api/work/screenshot-result`
- **Method**: `POST`
- **Content-Type**: `application/json`

---

## Request Body 필드

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `id` | integer | ✅ | 작업 ID (allocate-screenshot에서 받은 ID) |
| `screenshot_url` | string | ✅ | 업로드된 스크린샷 URL 또는 "PRODUCT_NOT_FOUND" |
| `keyword` | string | ⚪ | 검색 키워드 |
| `rank` | integer | ⚪ | 발견된 순위 (전체 누적 순위, 1부터 시작) |
| `product_id` | string | ⚪ | 상품 ID (매칭된 경우만 값, 아니면 null) |
| `item_id` | string | ⚪ | 아이템 ID (매칭된 경우만 값, 아니면 null) |
| `vendor_item_id` | string | ⚪ | 판매자 아이템 ID (매칭된 경우만 값, 아니면 null) |
| `filename` | string | ⚪ | 스크린샷 파일명 (경로 제외) |

### 필드 상세 설명

#### `screenshot_url`
- **성공 시**: 실제 업로드된 스크린샷 URL
  - 예: `"https://cdn.example.com/screenshots/2025/11/03/123456_노트북_7227655664_18331882647_85810785808.png"`
- **상품 미발견 시**: `"PRODUCT_NOT_FOUND"` (문자열)
- **차단 감지 시**: 요청 자체를 보내지 않음

#### `rank`
- **타입**: 정수 (1부터 시작)
- **의미**: 전체 검색 결과에서의 누적 순위
- **예제**:
  - 1페이지 3번째 상품 → `rank: 3`
  - 2페이지 8번째 상품 (1페이지 40개) → `rank: 48`
- **null 조건**: 상품을 찾지 못한 경우

#### `product_id`, `item_id`, `vendor_item_id`
- **매칭 조건에 따라 일치한 필드만 값을 가짐**
- **일치하지 않은 필드는 `null`**
- 서버는 각 필드의 null 여부로 매칭 조건을 파악 가능

---

## Response Body

### 성공 응답
```json
{
  "success": true,
  "message": "Result submitted successfully"
}
```
- **HTTP Status**: `200 OK`

### 실패 응답
```json
{
  "success": false,
  "message": "Error message here"
}
```
- **HTTP Status**: `200 OK` (success: false로 구분)
- 또는 `400 Bad Request`, `500 Internal Server Error` 등

---

## Request 예제

### 1. 성공 케이스: 완전 일치 (product_id + item_id + vendor_item_id)

**시나리오**: 작업 할당 시 받은 3가지 ID가 모두 일치하는 상품을 찾음

```json
{
  "id": 4948534,
  "screenshot_url": "https://cdn.example.com/screenshots/123456_사운드바_7227655664_18331882647_85810785808.png",
  "keyword": "사운드바",
  "rank": 7,
  "product_id": "7227655664",
  "item_id": "18331882647",
  "vendor_item_id": "85810785808",
  "filename": "123456_사운드바_7227655664_18331882647_85810785808.png"
}
```

**특징**:
- ✅ `product_id`, `item_id`, `vendor_item_id` 모두 값이 있음
- ✅ `rank`가 7 (7위에서 발견)
- ✅ `screenshot_url`이 실제 업로드된 URL

---

### 2. 성공 케이스: product_id + vendor_item_id 일치

**시나리오**: product_id와 vendor_item_id는 일치하지만 item_id는 다른 상품

```json
{
  "id": 4948535,
  "screenshot_url": "https://cdn.example.com/screenshots/123457_노트북_9876543210_NULL_11122233344.png",
  "keyword": "노트북",
  "rank": 12,
  "product_id": "9876543210",
  "item_id": null,
  "vendor_item_id": "11122233344",
  "filename": "123457_노트북_9876543210_NULL_11122233344.png"
}
```

**특징**:
- ✅ `product_id`, `vendor_item_id`는 값이 있음
- ❌ `item_id`는 `null` (매칭되지 않음)
- ✅ `rank`는 12 (12위에서 발견)

---

### 3. 성공 케이스: product_id만 일치

**시나리오**: product_id만 일치하는 상품 발견

```json
{
  "id": 4948536,
  "screenshot_url": "https://cdn.example.com/screenshots/123458_키보드_1234567890_NULL_NULL.png",
  "keyword": "키보드",
  "rank": 3,
  "product_id": "1234567890",
  "item_id": null,
  "vendor_item_id": null,
  "filename": "123458_키보드_1234567890_NULL_NULL.png"
}
```

**특징**:
- ✅ `product_id`만 값이 있음
- ❌ `item_id`, `vendor_item_id`는 `null`
- ✅ `rank`는 3 (3위에서 발견)

---

### 4. 성공 케이스: vendor_item_id만 일치

**시나리오**: vendor_item_id만 일치하는 상품 발견

```json
{
  "id": 4948537,
  "screenshot_url": "https://cdn.example.com/screenshots/123459_마우스_NULL_NULL_99988877766.png",
  "keyword": "마우스",
  "rank": 25,
  "product_id": null,
  "item_id": null,
  "vendor_item_id": "99988877766",
  "filename": "123459_마우스_NULL_NULL_99988877766.png"
}
```

**특징**:
- ✅ `vendor_item_id`만 값이 있음
- ❌ `product_id`, `item_id`는 `null`
- ✅ `rank`는 25 (25위에서 발견)

---

### 5. 성공 케이스: item_id만 일치

**시나리오**: item_id만 일치하는 상품 발견 (가장 낮은 우선순위)

```json
{
  "id": 4948538,
  "screenshot_url": "https://cdn.example.com/screenshots/123460_모니터_NULL_55566677788_NULL.png",
  "keyword": "모니터",
  "rank": 40,
  "product_id": null,
  "item_id": "55566677788",
  "vendor_item_id": null,
  "filename": "123460_모니터_NULL_55566677788_NULL.png"
}
```

**특징**:
- ✅ `item_id`만 값이 있음
- ❌ `product_id`, `vendor_item_id`는 `null`
- ✅ `rank`는 40 (40위에서 발견)

---

### 6. 실패 케이스: 상품 미발견 (PRODUCT_NOT_FOUND)

**시나리오**: 검색 결과에서 일치하는 상품을 찾지 못함

```json
{
  "id": 4948539,
  "screenshot_url": "PRODUCT_NOT_FOUND",
  "keyword": "희귀상품",
  "rank": null,
  "product_id": null,
  "item_id": null,
  "vendor_item_id": null,
  "filename": null
}
```

**특징**:
- ⚠️ `screenshot_url`이 `"PRODUCT_NOT_FOUND"` (문자열)
- ❌ `rank`는 `null` (순위 없음)
- ❌ `product_id`, `item_id`, `vendor_item_id` 모두 `null`
- ❌ `filename`도 `null` (스크린샷 없음)

---

### 7. 실패 케이스: 차단 감지 (요청 전송 안함)

**시나리오**: IP 차단 또는 네트워크 오류 감지

```
⚠️  차단 감지 - 작업 결과 제출 건너뛰기
   차단 사유: http2_protocol_error 또는 네트워크 차단 감지
   작업 ID 4948540는 제출하지 않습니다
```

**특징**:
- ❌ API 요청 자체를 보내지 않음
- ❌ 작업은 "할당됨" 상태로 남음
- ⚠️ 서버에서 타임아웃 또는 재할당 로직 필요

---

## 매칭 조건 우선순위

Agent는 다음 우선순위로 상품을 검색합니다:

| 순위 | 매칭 조건 | product_id | item_id | vendor_item_id |
|------|-----------|------------|---------|----------------|
| 1 | 완전 일치 | ✅ | ✅ | ✅ |
| 2 | product_id + vendor_item_id | ✅ | ❌ | ✅ |
| 3 | product_id만 | ✅ | ❌ | ❌ |
| 4 | vendor_item_id만 | ❌ | ❌ | ✅ |
| 5 | item_id만 | ❌ | ✅ | ❌ |

---

## 서버 구현 가이드

### 1. 매칭 조건 판별

서버에서는 각 필드의 null 여부로 매칭 조건을 파악할 수 있습니다:

```javascript
// Node.js 예제
function getMatchCondition(result) {
  const hasProductId = result.product_id !== null;
  const hasItemId = result.item_id !== null;
  const hasVendorItemId = result.vendor_item_id !== null;

  if (hasProductId && hasItemId && hasVendorItemId) {
    return "완전 일치";
  } else if (hasProductId && hasVendorItemId) {
    return "product_id + vendor_item_id 일치";
  } else if (hasProductId) {
    return "product_id 일치";
  } else if (hasVendorItemId) {
    return "vendor_item_id 일치";
  } else if (hasItemId) {
    return "item_id 일치";
  } else {
    return "매칭 실패";
  }
}
```

```python
# Python 예제
def get_match_condition(result):
    has_product_id = result.get("product_id") is not None
    has_item_id = result.get("item_id") is not None
    has_vendor_item_id = result.get("vendor_item_id") is not None

    if has_product_id and has_item_id and has_vendor_item_id:
        return "완전 일치"
    elif has_product_id and has_vendor_item_id:
        return "product_id + vendor_item_id 일치"
    elif has_product_id:
        return "product_id 일치"
    elif has_vendor_item_id:
        return "vendor_item_id 일치"
    elif has_item_id:
        return "item_id 일치"
    else:
        return "매칭 실패"
```

### 2. 성공/실패 구분

```javascript
// Node.js 예제
function isSuccess(result) {
  return result.screenshot_url !== "PRODUCT_NOT_FOUND";
}

function isProductNotFound(result) {
  return result.screenshot_url === "PRODUCT_NOT_FOUND";
}
```

### 3. 데이터베이스 스키마 권장사항

```sql
CREATE TABLE screenshot_results (
  id BIGINT PRIMARY KEY,
  screenshot_url VARCHAR(1024),
  keyword VARCHAR(255),
  rank INT,
  product_id VARCHAR(50),
  item_id VARCHAR(50),
  vendor_item_id VARCHAR(50),
  filename VARCHAR(255),
  match_condition VARCHAR(100),  -- 계산된 필드 (선택)
  status VARCHAR(50),  -- 'success' | 'not_found' (선택)
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 권장
CREATE INDEX idx_keyword ON screenshot_results(keyword);
CREATE INDEX idx_rank ON screenshot_results(rank);
CREATE INDEX idx_match_condition ON screenshot_results(match_condition);
CREATE INDEX idx_status ON screenshot_results(status);
```

### 4. 통계 쿼리 예제

```sql
-- 매칭 조건별 성공률
SELECT
  CASE
    WHEN product_id IS NOT NULL AND item_id IS NOT NULL AND vendor_item_id IS NOT NULL THEN '완전 일치'
    WHEN product_id IS NOT NULL AND vendor_item_id IS NOT NULL THEN 'product_id + vendor_item_id'
    WHEN product_id IS NOT NULL THEN 'product_id만'
    WHEN vendor_item_id IS NOT NULL THEN 'vendor_item_id만'
    WHEN item_id IS NOT NULL THEN 'item_id만'
    ELSE '매칭 실패'
  END AS match_condition,
  COUNT(*) AS total_count,
  AVG(rank) AS avg_rank
FROM screenshot_results
WHERE screenshot_url != 'PRODUCT_NOT_FOUND'
GROUP BY match_condition
ORDER BY total_count DESC;

-- 순위 분포
SELECT
  CASE
    WHEN rank <= 10 THEN '1-10위'
    WHEN rank <= 20 THEN '11-20위'
    WHEN rank <= 40 THEN '21-40위'
    ELSE '40위 이상'
  END AS rank_range,
  COUNT(*) AS count
FROM screenshot_results
WHERE rank IS NOT NULL
GROUP BY rank_range
ORDER BY rank_range;

-- 키워드별 성공률
SELECT
  keyword,
  COUNT(*) AS total,
  SUM(CASE WHEN screenshot_url != 'PRODUCT_NOT_FOUND' THEN 1 ELSE 0 END) AS success,
  ROUND(100.0 * SUM(CASE WHEN screenshot_url != 'PRODUCT_NOT_FOUND' THEN 1 ELSE 0 END) / COUNT(*), 2) AS success_rate
FROM screenshot_results
GROUP BY keyword
ORDER BY total DESC;
```

---

## VPN 환경 참고사항

### API 요청 VPN 우회

Agent가 VPN 환경에서 실행되는 경우:
- **브라우저 트래픽**: VPN을 통해 라우팅됨 (IP 우회)
- **API 요청**: 로컬 네트워크를 통해 직접 전송됨 (VPN 우회)

**이유**:
- API 서버가 VPN IP를 차단하거나 느린 경우
- 로컬 네트워크로 우회하여 빠른 응답 시간 확보 (0.024초 vs 15초)

**구현 방식**:
```python
# VPN 환경 감지
if os.environ.get('VPN_EXECUTED'):
    # subprocess로 원래 사용자(tech)로 Python 실행
    # UID 기반 라우팅을 우회하여 로컬 네트워크 사용
    sudo -u tech python3 -c "requests.post(...)"
```

**서버 측 영향**:
- 없음 (Agent 내부 최적화)
- 항상 동일한 형식의 요청을 받음

---

## 오류 처리 권장사항

### 1. 타임아웃 설정
- Agent는 60초 타임아웃 사용
- 서버는 최소 90초 타임아웃 설정 권장

### 2. 중복 제출 방지
- `id` 필드를 Primary Key로 사용
- 중복 제출 시 `409 Conflict` 또는 기존 데이터 업데이트

### 3. 검증 로직
```javascript
// 필수 필드 검증
if (!result.id || !result.screenshot_url) {
  return res.status(400).json({
    success: false,
    message: "Missing required fields: id, screenshot_url"
  });
}

// screenshot_url 포맷 검증
if (result.screenshot_url !== "PRODUCT_NOT_FOUND" &&
    !result.screenshot_url.startsWith("http")) {
  return res.status(400).json({
    success: false,
    message: "Invalid screenshot_url format"
  });
}
```

---

## 변경 이력

### 2025-11-03 (v2.0)
- ✅ `keyword`, `rank`, `filename` 필드 추가
- ✅ `product_id`, `item_id`, `vendor_item_id` 필드 추가
  - 매칭된 필드만 값, 나머지는 null
- ❌ `match_condition` 필드 제거
  - 각 필드의 null 여부로 판별 가능

### 2025-11-02 (v1.0)
- ✅ 초기 API 구현
- `id`, `screenshot_url`만 전송

---

## 문의 및 지원

- **문서**: `/home/tech/agent/docs/`
- **코드**: `/home/tech/agent/lib/modules/work_api_client.py`
- **테스트**: `/home/tech/agent/tests/test_work_api.py`

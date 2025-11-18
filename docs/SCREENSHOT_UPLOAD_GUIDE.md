# 스크린샷 업로드 기능 가이드

## 개요

Coupang Agent V2의 스크린샷 업로드 기능은 캡처한 스크린샷을 자동으로 서버에 업로드하는 기능입니다.

## 주요 기능

### 1. 자동 업로드
- 스크린샷 캡처 후 자동으로 서버에 업로드
- 변경 전(before) 및 변경 후(after) 스크린샷 모두 업로드
- 메타데이터와 함께 전송 (키워드, 버전, VPN, 상품 정보 등)

### 2. 재시도 로직
- 네트워크 오류 시 자동 재시도 (최대 3회)
- 재시도 간 1초 대기
- 타임아웃 30초

### 3. 에러 처리
- 업로드 실패 시 로컬 파일 보존
- 상세 오류 로깅

## 활성화 방법

### 1. agent.py 설정 수정

```python
# 스크린샷 업로드 기능 활성화 플래그 및 설정
ENABLE_SCREENSHOT_UPLOAD = True  # False → True로 변경
UPLOAD_SERVER_URL = "http://localhost:8000/upload"  # 서버 URL 설정
```

### 2. 서버 URL 설정

**실제 서버 (기본):**
```python
UPLOAD_SERVER_URL = "http://toprekr.com/toprekr/upload.php"
```

**로컬 테스트:**
```python
UPLOAD_SERVER_URL = "http://localhost:8000/upload"
```

## 테스트 서버 사용법

### 1. Flask 설치

```bash
pip install flask
```

### 2. 테스트 서버 실행

```bash
python3 test_upload_server.py
```

출력 예시:
```
============================================================
🚀 스크린샷 업로드 테스트 서버 시작
============================================================
서버 주소: http://localhost:8000
업로드 엔드포인트: http://localhost:8000/upload
헬스 체크: http://localhost:8000/health
저장 디렉토리: /home/tech/agent/uploaded_screenshots
============================================================
```

### 3. Agent 실행

```bash
# 테스트 서버가 실행 중인 상태에서
python3 agent.py --version 134 --keyword "노트북"
```

### 4. 업로드 확인

테스트 서버 콘솔에서 업로드 로그 확인:
```
============================================================
📥 파일 업로드 수신
============================================================
파일명: 노트북_before_viewport_20251101_123456.png
크기: 234.56 KB
저장 경로: /home/tech/agent/uploaded_screenshots/chrome-134/local/노트북_before_viewport_20251101_123456.png
키워드: 노트북
버전: 134
VPN: local
상품명: 삼성전자 갤럭시북4 프로 NT960XGQ-A51A...
상품 순위: 15
캡처 타입: before_viewport
타임스탬프: 2025-11-01 12:34:56
============================================================
```

## 업로드 디렉토리 구조

```
uploaded_screenshots/
├── chrome-127/
│   ├── local/
│   │   ├── 노트북_before_viewport_20251101_123456.png
│   │   └── 노트북_after_viewport_20251101_123457.png
│   ├── vpn1/
│   │   └── ...
│   └── vpn2/
│       └── ...
├── chrome-134/
│   └── ...
└── chrome-beta/
    └── ...
```

## 업로드 메타데이터

각 스크린샷과 함께 전송되는 메타데이터:

| 필드 | 설명 | 예시 |
|------|------|------|
| `keyword` | 검색 키워드 | "노트북" |
| `version` | Chrome 버전 | "134" |
| `vpn_num` | VPN 번호 | "1" (local이면 "") |
| `product_name` | 상품명 | "삼성전자 갤럭시북4..." |
| `product_rank` | 상품 순위 | "15" |
| `capture_type` | 캡처 타입 | "before_viewport" / "after_viewport" |
| `timestamp` | 타임스탬프 | "2025-11-01 12:34:56" |

## 실제 서버 API

### toprekr.com 서버

**엔드포인트:** `http://toprekr.com/toprekr/upload.php`

**요청:**
```bash
curl -X POST \
  -F "image=@photo.jpg" \
  -F "keyword=노트북" \
  -F "version=134" \
  -F "product_name=상품명" \
  http://toprekr.com/toprekr/upload.php
```

**응답 예시:**
```json
{
  "success": true,
  "id": 123,
  "url": "http://toprekr.com/toprekr/images/2025/11/01/a3f7e9d2c1b4567890abcdef12345678.jpg",
  "filename": "a3f7e9d2c1b4567890abcdef12345678.jpg",
  "original_name": "photo.jpg",
  "size": 2048576,
  "width": 1920,
  "height": 1080,
  "mime_type": "image/jpeg",
  "uploaded_at": "2025-11-01 23:30:00"
}
```

**참고:**
- 파일 필드명: `image` (NOT `file`)
- 메타데이터는 form data로 함께 전송
- 응답에는 이미지 URL, ID, 크기 등이 포함됨

## 서버 구현 예시

### Flask 서버

```python
from flask import Flask, request, jsonify
from pathlib import Path

app = Flask(__name__)
UPLOAD_DIR = Path("/var/www/screenshots")

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['image']  # 'image' 필드 사용
    keyword = request.form.get('keyword')
    version = request.form.get('version')
    # ... 메타데이터 처리

    # 파일 저장
    save_path = UPLOAD_DIR / file.filename
    file.save(str(save_path))

    return jsonify({
        'success': True,
        'id': 1,
        'url': f'http://localhost:8000/images/{file.filename}',
        'filename': file.filename
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

### Django 서버

```python
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

@csrf_exempt
def upload_screenshot(request):
    if request.method == 'POST':
        file = request.FILES['image']  # 'image' 필드 사용
        keyword = request.POST.get('keyword')
        version = request.POST.get('version')
        # ... 메타데이터 처리

        # 파일 저장
        with open(f'/var/www/screenshots/{file.name}', 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        return JsonResponse({
            'success': True,
            'id': 1,
            'url': f'http://localhost:8000/images/{file.name}',
            'filename': file.name
        })
```

### FastAPI 서버

```python
from fastapi import FastAPI, File, UploadFile, Form
from pathlib import Path

app = FastAPI()
UPLOAD_DIR = Path("/var/www/screenshots")

@app.post("/upload")
async def upload_screenshot(
    image: UploadFile = File(...),  # 'image' 필드 사용
    keyword: str = Form(""),
    version: str = Form(""),
    # ... 기타 메타데이터
):
    save_path = UPLOAD_DIR / image.filename
    with open(save_path, "wb") as buffer:
        buffer.write(await image.read())

    return {
        "success": True,
        "id": 1,
        "url": f"http://localhost:8000/images/{image.filename}",
        "filename": image.filename
    }
```

## 로그 출력 예시

### 업로드 성공

```
============================================================
📤 [변경 전] 스크린샷 업로드
============================================================

📤 스크린샷 업로드 시작...
   파일: 노트북_before_viewport_20251101_123456.png
   크기: 234.56 KB
   서버: http://localhost:8000/upload

   시도 1/3...

✅ 업로드 성공!
   서버 응답: 200
   응답 데이터: {'success': True, 'filename': '노트북_before_viewport_20251101_123456.png'}

✅ [변경 전] 스크린샷 업로드 완료
```

### 업로드 실패 (재시도)

```
============================================================
📤 [변경 전] 스크린샷 업로드
============================================================

📤 스크린샷 업로드 시작...
   파일: 노트북_before_viewport_20251101_123456.png
   크기: 234.56 KB
   서버: http://localhost:8000/upload

   시도 1/3...
   ⚠️  연결 오류: Connection refused
   ⏱️  1초 후 재시도...

   시도 2/3...
   ⚠️  연결 오류: Connection refused
   ⏱️  1초 후 재시도...

   시도 3/3...
   ⚠️  연결 오류: Connection refused

❌ 업로드 실패 (최대 재시도 횟수 초과)
   오류: 연결 오류: Connection refused
   파일은 로컬에 보존됨: /home/tech/agent/screenshots/chrome-134/local/노트북_before_viewport_20251101_123456.png

⚠️  [변경 전] 스크린샷 업로드 실패: 연결 오류: Connection refused
   파일은 로컬에 저장되어 있습니다: /home/tech/agent/screenshots/chrome-134/local/노트북_before_viewport_20251101_123456.png
```

## 보안 고려사항

1. **HTTPS 사용**: 프로덕션 환경에서는 HTTPS 사용 권장
   ```python
   UPLOAD_SERVER_URL = "https://your-server.com/upload"
   ```

2. **인증 토큰**: API 토큰 추가 가능
   ```python
   # screenshot_uploader.py 수정
   headers = {
       'Authorization': f'Bearer {API_TOKEN}'
   }
   response = requests.post(url, files=files, data=data, headers=headers)
   ```

3. **파일 크기 제한**: 서버 측에서 파일 크기 제한 설정

4. **파일 타입 검증**: PNG 파일만 허용

## 문제 해결

### 1. "Connection refused" 오류
- 서버가 실행 중인지 확인
- 방화벽 설정 확인
- URL이 올바른지 확인

### 2. "Timeout" 오류
- 네트워크 연결 상태 확인
- 서버 응답 속도 확인
- `timeout` 값 증가 고려

### 3. "HTTP 500" 오류
- 서버 로그 확인
- 디스크 공간 확인
- 파일 권한 확인

## 비활성화 방법

업로드 기능을 비활성화하려면:

```python
# agent.py
ENABLE_SCREENSHOT_UPLOAD = False  # True → False로 변경
```

비활성화 시 출력:
```
⚠️  스크린샷 업로드가 비활성화되어 있습니다 (ENABLE_SCREENSHOT_UPLOAD=False)
```

## 요약

- ✅ **자동 업로드**: 스크린샷 캡처 후 자동 업로드
- ✅ **재시도 로직**: 최대 3회 자동 재시도
- ✅ **메타데이터**: 키워드, 버전, VPN, 상품 정보 전송
- ✅ **에러 처리**: 실패 시 로컬 파일 보존
- ✅ **테스트 서버**: Flask 기반 테스트 서버 제공
- ✅ **플래그 제어**: 쉬운 활성화/비활성화

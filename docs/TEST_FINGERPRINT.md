# 핑거프린트 랜덤화 테스트 가이드

IP 1개로 무한 우회를 위한 브라우저 핑거프린트 랜덤화 테스트 도구입니다.

## 🎯 목적

- **IP 차단 상태**에서 핑거프린트 랜덤화만으로 검색 차단을 우회할 수 있는지 테스트
- Chrome 130 고정 사용 (기존 agent.py에 영향 없음)
- **시크릿모드** 실행 (프로필 관리 불필요)
- 핑거프린트 변조 기법의 효과 검증

## 📁 파일 구조

```
agent/
├── test_fingerprint.py              # 테스트 실행 스크립트 (독립적)
├── lib/utils/fingerprint_randomizer.py  # 핑거프린트 랜덤화 모듈
└── TEST_FINGERPRINT.md              # 이 파일
```

**기존 파일에 영향 없음**: `agent.py`, `browser_core_uc.py` 등 기존 코드는 수정되지 않았습니다.

**시크릿모드 사용**: 프로필 관리 없이 매번 깨끗한 상태로 테스트합니다.

## 🚀 사용법

### 1. 기본 테스트 (핑거프린트 랜덤화 비활성화)

```bash
# IP 차단 상태에서 Chrome 130으로 기본 테스트
python3 test_fingerprint.py
```

**예상 결과**: IP가 차단된 상태라면 검색 실패

### 2. 핑거프린트 랜덤화 활성화 테스트

```bash
# 핑거프린트 랜덤화를 적용한 테스트
python3 test_fingerprint.py --randomize
```

**예상 결과**: 핑거프린트 랜덤화로 차단 우회 성공 (효과가 있다면)

### 3. 자동 종료 모드

```bash
# 테스트 후 3초 뒤 자동 종료
python3 test_fingerprint.py --randomize --close
```

### 4. 다른 키워드로 테스트

```bash
# "게임" 키워드로 검색 테스트
python3 test_fingerprint.py --randomize --keyword "게임"
```

### 5. VPN과 함께 사용

```bash
# VPN 서버 1 + 핑거프린트 랜덤화
# 주의: VPN 재실행 기능은 agent.py에만 있으므로 수동으로 VPN 실행 필요
vpn 1 python3 test_fingerprint.py --randomize
```

## 📊 테스트 시나리오

### 시나리오 1: IP 차단 상태 확인

```bash
# 1단계: 랜덤화 없이 테스트 (차단 확인)
python3 test_fingerprint.py --close

# 결과가 "차단됨"이면 다음 단계로
```

### 시나리오 2: 핑거프린트 랜덤화 효과 검증

```bash
# 2단계: 랜덤화 활성화 테스트
python3 test_fingerprint.py --randomize --close

# 성공하면 핑거프린트 랜덤화가 효과적
# 실패하면 추가 변조 기법 필요
```

### 시나리오 3: 반복 테스트 (다양성 확인)

```bash
# 여러 번 실행해서 매번 다른 핑거프린트로 우회되는지 확인
for i in {1..5}; do
    echo "=== 테스트 $i ==="
    python3 test_fingerprint.py --randomize --close
    sleep 3
done
```

## 🎭 핑거프린트 랜덤화 적용 항목

`--randomize` 옵션 사용 시 다음 항목들이 랜덤하게 변조됩니다:

### 1. HTTP 헤더
- `Accept-Encoding` 순서 변경 (4가지 조합)
- `sec-ch-ua` 변형 (3가지 조합)
- `sec-ch-ua-platform` 변경 (3가지 조합)

### 2. 화면 해상도 & DPI
- 5가지 해상도 조합 (1366x768 ~ 2560x1440)
- Device Scale Factor (1.0x ~ 1.5x)

### 3. Canvas 핑거프린트
- 픽셀에 랜덤 노이즈 추가 (육안 구분 불가)
- 매번 다른 Canvas 값 생성

### 4. WebGL 핑거프린트
- Vendor: Intel, Google, NVIDIA 중 랜덤 선택
- Renderer: 4가지 GPU 모델 중 랜덤 선택

### 5. Navigator 속성
- CPU 코어 수: 2~16 코어 중 랜덤
- 디바이스 메모리: 2~16GB 중 랜덤
- 배터리 API 차단

## 📈 결과 해석

### ✅ 성공 케이스

```
✅ 성공: 검색이 정상적으로 완료되었습니다!
============================================================
현재 URL: https://www.coupang.com/np/search?component=&q=노트북&...
상태: {'execution_status': 'RESULTS_LOADED', 'action_status': 'SUCCESS', ...}
============================================================

🎉 핑거프린트 랜덤화로 차단 우회 성공!
```

→ **핑거프린트 랜덤화가 효과적으로 작동**

### ❌ 실패 케이스

```
❌ 실패: 검색이 차단되었거나 오류가 발생했습니다
============================================================
현재 URL: https://www.coupang.com/np/error/...
============================================================

🚫 http2_protocol_error 또는 차단 페이지 감지
   → IP 차단 또는 브라우저 핑거프린트 차단
   → 핑거프린트 랜덤화를 사용했지만 여전히 차단됨
   → 추가 변조 기법이 필요할 수 있음
```

→ **추가 변조 기법 필요** (TLS 핑거프린트, User-Agent 등)

## 🔧 고급 사용법

### 핑거프린트 정보만 확인

```python
# Python 대화형 모드에서
from lib.utils.fingerprint_randomizer import FingerprintRandomizer
from lib.core.browser_core_uc import BrowserCoreUC

core = BrowserCoreUC(instance_id=999)
driver = core.launch(version="130", use_profile=True, headless=False)

# 핑거프린트 랜덤화 적용
FingerprintRandomizer.apply_all(driver)

# 핑거프린트 정보 확인
fp_info = FingerprintRandomizer.get_fingerprint_info(driver)
print(fp_info)
```

### 특정 변조만 적용

```python
# HTTP 헤더만 랜덤화
FingerprintRandomizer.randomize_http_headers(driver)

# Canvas만 랜덤화
FingerprintRandomizer.randomize_canvas(driver)

# WebGL만 랜덤화
FingerprintRandomizer.randomize_webgl(driver)
```

## 💡 팁

1. **IP가 차단되지 않은 경우**
   - 먼저 agent.py로 IP를 차단시킨 후 테스트
   - Chrome 127-130 버전을 여러 번 사용하면 IP 차단됨

2. **핑거프린트 랜덤화 효과가 없는 경우**
   - TLS 핑거프린트가 주요 차단 요인일 수 있음
   - 다른 Chrome 버전(131+) 테스트 권장
   - VPN으로 IP 변경 후 재테스트

3. **반복 테스트**
   - 매번 다른 핑거프린트가 생성되는지 확인
   - 5회 이상 반복 실행해서 안정성 검증

## 🐛 문제 해결

### Chrome 130이 설치되지 않은 경우

```bash
./install-chrome-versions.sh 130
```

### 권한 오류 (VPN 사용 시)

```bash
./setup-permissions.sh
```

### 브라우저가 실행되지 않는 경우

```bash
# undetected-chromedriver 재설치
pip install --upgrade undetected-chromedriver
```

## 📝 주의사항

- 이 테스트 스크립트는 **Chrome 130 고정**으로 작동합니다
- 기존 `agent.py`는 **전혀 수정되지 않았습니다**
- 테스트용 Instance ID(999)를 사용하여 기존 프로필과 충돌하지 않습니다
- 핑거프린트 랜덤화는 **완벽한 우회를 보장하지 않습니다**
- 쿠팡의 차단 시스템은 계속 진화하므로 정기적인 업데이트가 필요합니다

## 🎓 추가 학습 자료

- [Browser Fingerprinting](https://en.wikipedia.org/wiki/Device_fingerprint)
- [Canvas Fingerprinting](https://browserleaks.com/canvas)
- [WebGL Fingerprinting](https://browserleaks.com/webgl)
- [HTTP/2 Fingerprinting](https://tlsfingerprint.io/)

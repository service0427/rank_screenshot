# BrowserStack Local + VPN IP 변경 테스트 가이드

BrowserStack Local 터널을 통해 모바일 디바이스가 VPN IP를 사용하는지 확인하는 테스트

## 🎯 목적

- **VPN + BrowserStack Local 조합 검증**
- VPN으로 로컬 IP 변경 시, BrowserStack 모바일 디바이스도 동일한 IP 사용 확인
- IP 레벨에서의 우회 가능성 테스트

## 📦 설치

### 1. Appium 라이브러리 설치

```bash
pip install Appium-Python-Client
```

### 2. BrowserStack 계정 설정

`.env` 파일 또는 환경 변수:

```bash
export BROWSERSTACK_USERNAME="your_username"
export BROWSERSTACK_ACCESS_KEY="your_access_key"
```

### 3. BrowserStack Local 바이너리

- **자동 다운로드**: 첫 실행 시 자동으로 Linux 바이너리 다운로드
- **수동 다운로드**: https://www.browserstack.com/local-testing/automate

## 🚀 사용법

### 1. 로컬 IP 테스트 (VPN 없음)

```bash
python3 test_browserstack_vpn_ip.py
```

**기대 결과**:
- 로컬 IP: 123.45.67.89
- 모바일 IP: 123.45.67.89 (동일)
- ✅ BrowserStack Local 터널이 정상 작동

### 2. VPN IP 테스트 (VPN 1 사용)

```bash
python3 test_browserstack_vpn_ip.py --vpn 1
```

**기대 결과**:
- VPN Server 1 IP: 98.76.54.32
- 모바일 IP: 98.76.54.32 (동일)
- ✅ VPN IP가 모바일 디바이스에 적용됨

### 3. 다른 VPN 서버로 테스트

```bash
python3 test_browserstack_vpn_ip.py --vpn 2
python3 test_browserstack_vpn_ip.py --vpn 3
```

## 📱 테스트 디바이스

**랜덤으로 선택되는 Android 디바이스**:
- Samsung Galaxy S23 (Android 13)
- Samsung Galaxy S24 (Android 14)
- Google Pixel 7 (Android 13)
- OnePlus 11 (Android 13)

**iOS는 제외** (Safari TLS 핑거프린트가 Coupang에서 차단됨)

## 🔍 작동 원리

### BrowserStack Local의 IP 일관성

```
일반 BrowserStack (❌ IP 불일치):
  로컬 PC: 123.45.67.89
  모바일: 98.76.54.32  ← 다른 IP!
  결과: Akamai가 쿠키 차단

BrowserStack Local (✅ IP 일치):
  로컬 PC: 123.45.67.89
  모바일 → Local Tunnel → 123.45.67.89  ← 같은 IP!
  결과: 쿠키 재사용 가능
```

### VPN + BrowserStack Local 조합

```
VPN 없음:
  로컬 PC: 123.45.67.89
  모바일: 123.45.67.89  ← Local Tunnel 통해 동일

VPN 1 사용:
  로컬 PC: 98.76.54.32 (VPN 1 IP)
  모바일: 98.76.54.32  ← Local Tunnel 통해 VPN IP 사용!

VPN 2 사용:
  로컬 PC: 111.222.33.44 (VPN 2 IP)
  모바일: 111.222.33.44  ← VPN IP 변경마다 모바일도 변경
```

**핵심**: VPN으로 IP를 변경하면, BrowserStack 모바일 디바이스도 자동으로 그 IP를 사용합니다!

## 📊 예상 출력

### 성공 케이스

```
============================================================
🌐 BrowserStack Local + VPN IP 변경 테스트
============================================================
VPN: ✅ Server 1
============================================================

============================================================
📍 로컬 IP 주소 확인
============================================================
  VPN Server 1 IP: 98.76.54.32
============================================================

[BrowserStack Local] Starting tunnel...
  Binary: /home/tech/agent/tools/BrowserStackLocal
  Waiting for tunnel connection...
  ✅ Tunnel connected (11s)

============================================================
📱 랜덤 모바일 디바이스 선택
============================================================
  디바이스: Samsung Galaxy S23
  OS: Android 13.0
  브라우저: Chrome
============================================================

[Appium] Creating session for Samsung Galaxy S23 (Android 13.0, Chrome)...
  ✅ Session created: 1234567890abcdef

[Mobile Device] Checking IP address...
  📱 Mobile Device IP: 98.76.54.32
  ✅ Session closed

============================================================
📊 IP 변경 테스트 결과
============================================================
  로컬 IP:      98.76.54.32
  모바일 IP:    98.76.54.32
============================================================

✅ 성공: BrowserStack Local이 VPN IP를 정상적으로 사용합니다!
   → 로컬 IP와 모바일 IP가 동일합니다: 98.76.54.32
   → VPN Server 1의 IP가 모바일 디바이스에 적용되었습니다

[BrowserStack Local] Stopping tunnel...
  ✅ Tunnel stopped
```

## 💡 실전 활용

### 전략 A: VPN + BrowserStack Mobile

**효과**:
```
VPN 서버: N개
모바일 디바이스: 4종류
= N × 4 = 다양한 IP × 디바이스 조합
```

**사용 예시**:
```bash
# VPN 1 + 랜덤 모바일
python3 test_browserstack_vpn_ip.py --vpn 1

# VPN 2 + 랜덤 모바일
python3 test_browserstack_vpn_ip.py --vpn 2

# VPN 3 + 랜덤 모바일
python3 test_browserstack_vpn_ip.py --vpn 3
```

### 전략 B: PC + Mobile 하이브리드

**방법**:
1. PC Selenium으로 TLS 핑거프린트 수집 (Chrome 131+)
2. BrowserStack Mobile로 쿠키 수집 (VPN으로 IP 변경)
3. 수집한 쿠키를 curl-cffi와 조합

**장점**:
- PC의 다양한 Chrome 버전
- Mobile의 실제 디바이스 TLS
- VPN으로 IP 다양성
- = 완벽한 우회 조합

## 🐛 문제 해결

### Appium 라이브러리 설치 오류

```bash
pip uninstall Appium-Python-Client
pip install Appium-Python-Client
```

### BrowserStack Local 바이너리 다운로드 실패

수동 다운로드:
```bash
cd tools
wget https://www.browserstack.com/browserstack-local/BrowserStackLocal-linux-x64.zip
unzip BrowserStackLocal-linux-x64.zip
chmod +x BrowserStackLocal
```

### 세션 생성 실패

- BrowserStack 계정 활성화 확인
- USERNAME, ACCESS_KEY 확인
- 네트워크 연결 확인

### IP가 일치하지 않음

- BrowserStack Local 터널이 제대로 시작되었는지 확인
- 10초 이상 대기 후에도 실패 시, `--verbose` 옵션 추가 (코드 수정 필요)

## 🔗 관련 리소스

- **BrowserStack Local**: https://www.browserstack.com/local-testing/automate
- **Appium**: http://appium.io/
- **tls-1030 프로젝트**: https://github.com/service0427/tls-1030

## 📝 결론

### BrowserStack Local의 강력함

- ✅ **실제 모바일 디바이스** 사용
- ✅ **VPN IP 자동 적용** (Local Tunnel 통해)
- ✅ **IP 일관성 보장** (쿠키 재사용 가능)

### 한계

- ❌ BrowserStack 유료 계정 필요
- ❌ 세션 시작 시간 느림 (30초~1분)
- ❌ 동시 세션 수 제한 (플랜에 따라)

### 최적 전략

**VPN + BrowserStack Mobile + Selenium PC**:
```
VPN (IP 변경)
+ BrowserStack (실제 모바일)
+ Selenium PC (Chrome 버전 다양성)
= 완벽한 우회 조합
```

이 조합으로 **IP 레벨 + TLS 레벨 + JavaScript 레벨**의 3단계 우회가 가능합니다!

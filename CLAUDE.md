# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## ⚠️ IMPORTANT: 응답 언어 필수 규칙 ⚠️

**🇰🇷 모든 응답은 반드시 한국어로 작성해야 합니다 🇰🇷**

- ✅ **사용자 응답**: 한국어 필수
- ✅ **기술 설명**: 한국어 필수
- ✅ **오류 분석**: 한국어 필수
- ✅ **코드 설명**: 한국어 필수
- ✅ **Insight 블록**: 한국어 필수
- ✅ **요약 및 정리**: 한국어 필수

**절대 영어로 응답하지 마세요!**

---

## Claude Code 작업 정책

### 언어 사용 규칙
- **기본 응답 언어: 한국어**
- 사용자가 한국어로 질문하면 반드시 한국어로 답변
- 코드 주석 및 출력 메시지도 한국어 우선
- 기술 용어는 영문 병기 가능 (예: "프로필 (profile)")

### 내용 정리 원칙
- 테스트 결과는 표 형식으로 정리
- 주요 발견사항은 ★ Insight 블록으로 강조
- 긴 출력은 핵심만 요약하여 제시
- 문제 해결 과정은 단계별로 명확히 기술

## 프로젝트 개요

**🇰🇷 다시 한 번 강조: 모든 분석, 설명, 응답은 한국어로 작성하세요! 🇰🇷**

Coupang Agent V2는 Selenium + undetected-chromedriver를 사용한 자동화 탐지 우회 도구입니다. Chrome 130 (구버전 TLS) 및 144 (최신 버전)를 사용하여 TLS 핑거프린팅 다양성을 확보하고, VPN 통합으로 IP 우회 기능을 제공합니다.

## 설치

### 자동 설치 (권장)

우분투 22.04 LTS에서 한 번에 모든 의존성을 설치합니다:

```bash
# 저장소 클론
git clone https://github.com/service0427/rank_screenshot.git
cd rank_screenshot

# 자동 설치 스크립트 실행
./setup.sh
```

**설치 항목:**
- Python 3.10+ 및 pip
- 필수 시스템 라이브러리 (Chrome 실행용)
- Python 패키지 (undetected-chromedriver, selenium, Pillow, requests)
- Chrome 130 (구버전 TLS 대표)
- Chrome 144 (최신 버전)
- 디렉토리 구조 생성
- 권한 설정

**설치 후 테스트:**
```bash
python3 agent.py --version 134 --close
```

### 수동 설치

개별 컴포넌트를 직접 설치하려면:

```bash
# Python 패키지
pip3 install --user -r requirements.txt

# Chrome 130, 144 자동 설치
./install-chrome-versions.sh

# 권한 설정
./setup-permissions.sh
```

## 핵심 실행 명령어

### Chrome 버전 관리
```bash
# Chrome 130, 144 자동 설치 (기존 폴더 확인 후 없으면 설치)
./install-chrome-versions.sh
```

스크립트는 자동으로:
- Chrome 130 (구버전 TLS, 127-130 대표)
- Chrome 144 (최신 버전, 131+ 대표)

두 버전의 설치 여부를 확인하고, 없으면 자동으로 다운로드 및 설치합니다.

### Agent 실행

#### 인터랙티브 모드 (권장)
```bash
# 아무 옵션 없이 실행 → 자동으로 인터랙티브 모드
python3 agent.py
```
- Chrome 130, 144 중 선택 (+ 채널: beta, dev, canary)
- 마지막 사용 버전 기억 (`.last_version` 파일에 저장)
- Enter만 누르면 이전 버전 재사용
- 검색 키워드, 탐지 테스트도 대화형 선택

#### 명령행 옵션 (자동화용)
```bash
# 특정 버전 지정
python3 agent.py --version 134
python3 agent.py --version beta

# VPN 사용 (IP 우회)
python3 agent.py --version 127 --vpn 0

# 키워드 지정
python3 agent.py --version 134 --keyword "게임"

# 자동 종료 (3초 후)
python3 agent.py --version 134 --close

# 탐지 테스트
python3 agent.py --version 134 --test-detection
```

### 권한 설정 (VPN 사용 시 필수)

VPN과 함께 사용하는 경우 다음 설정이 필요합니다:

```bash
# 1. 권한 설정 스크립트 실행
./setup-permissions.sh

# 2. sudoers 설정 (VPN 사용자 전환용)
# /etc/sudoers.d/vpn-access 파일 생성
# VPN 서버 개수에 맞춰 vpnN 추가 (예: vpn0, vpn1, vpn2, vpn3, ...)
tech ALL=(vpn0,vpn1,vpn2,vpn3) NOPASSWD: ALL

# 3. VPN 서버 추가 방법
# VPN 클라이언트 디렉토리에서 sync.sh 실행
cd ~/vpn-ip-rotation/client
./sync.sh
```

**setup-permissions.sh가 설정하는 권한:**
- Agent 디렉토리: 읽기/실행 권한 (o+rX)
- Browser profiles: 읽기/쓰기/실행 권한 (o+rwX)
- ~/.local/share/undetected_chromedriver: 쓰기 권한 (o+rwX)
- ~/.cache/selenium: 쓰기 권한 (o+rwX)
- Python site-packages: 읽기 권한 (o+rX)

**배포 시 주의사항:**
- 서버 환경마다 홈 디렉토리 경로가 다를 수 있음
- 스크립트는 현재 사용자의 환경을 자동 감지
- VPN 클라이언트 설치 후 setup-permissions.sh 실행 권장
- 권한 오류 발생 시 스크립트 재실행

## 아키텍처 구조

### 계층 구조
```
agent.py (메인 진입점)
    ↓
BrowserCoreUC (lib/core/browser_core_uc.py)
    ↓ undetected-chromedriver 래퍼
    ↓ 버전별 프로필 관리
    ↓ 공유 캐시 시스템
    ↓
CoupangHandlerSelenium (lib/modules/coupang_handler_selenium.py)
    ↓ 쿠팡 특화 로직
    ↓
HumanBehaviorSelenium (lib/utils/human_behavior_selenium.py)
    ↓ 사람 행동 시뮬레이션
```

### 핵심 설계 원칙

#### 1. 버전별 프로필 분리 + 공유 캐시
- **프로필 분리**: 각 Chrome 버전마다 독립적인 프로필 (`browser-profiles/chrome-{version}/`)
  - 쿠키, 세션, 로컬스토리지는 버전별 독립
- **공유 캐시**: 모든 버전이 하나의 캐시 디렉토리 사용 (`browser-profiles/shared-cache/`)
  - 디스크 공간 70% 절약
  - 72시간 이상 미사용 캐시 자동 정리

#### 2. VPN 통합 (os.execvpe 패턴)
`agent.py`에서 `--vpn N` 옵션 사용 시:
1. VPN 명령어 경로 확인 (PATH 또는 `~/vpn-ip-rotation/client/vpn`)
2. `VPN_EXECUTED` 환경 변수로 재실행 여부 확인 (무한 루프 방지)
3. `os.execvpe(vpn_cmd, [vpn_cmd, str(vpn_num), 'python3'] + args, env)`로 VPN 래퍼를 통해 재실행
4. VPN은 UID 기반 라우팅 사용 - 각 vpn 사용자(vpn0~vpn3)마다 다른 네트워크 경로

**중요**: VPN은 네트워크 계층에서 작동하므로 애플리케이션 코드에서 프록시 설정 불필요

#### 3. undetected-chromedriver 탐지 우회
- `navigator.webdriver` 자동 제거
- Chrome DevTools Protocol (CDP) 우회
- Automation flags 비활성화
- 표준 Selenium API와 호환

#### 4. Chrome 131+ WSL 호환성
Chrome 131 이상은 WSL 환경에서 렌더러 프로세스 문제가 있어 다음 플래그 필수:
```python
--disable-gpu
--disable-software-rasterizer
--disable-features=VizDisplayCompositor
--remote-debugging-port=0
```

#### 5. Viewport 고정 (1920x1080)
`set_viewport()` 함수는 **내부 콘텐츠 영역**을 1920x1080으로 고정:
- 창 크기를 계산하여 설정 (툴바/스크롤바 고려)
- 일관된 렌더링 및 스크린샷 보장

### 주요 컴포넌트

#### BrowserCoreUC
- undetected-chromedriver 초기화 및 설정
- Chrome 옵션 구성 (한국어, 공유 캐시, WSL 호환성)
- 버전별 프로필 디렉토리 관리
- 캐시 정리 (`clean_old_cache()`)
- 스토리지 초기화 (`clear_all_storage()` - 쿠키/세션/로컬스토리지만 삭제, 캐시 유지)

#### CoupangHandlerSelenium
- 쿠팡 홈페이지 이동 (`navigate_to_home()`)
- 상품 검색 (`search_product()`)
- JavaScript 실행을 통한 자연스러운 검색 동작
- 상태 추적 (ExecutionStatus, ActionStatus)

#### HumanBehaviorSelenium
- 타이핑 시뮬레이션: 랜덤 지연 (80-200ms)
- 마우스 이동 시뮬레이션: 곡선 경로
- 스크롤 시뮬레이션: 단계적 스크롤 + 랜덤 정지

#### BrowserVersionManager
- Chrome 버전 스캔 (130, 144 + 채널)
- 랜덤 버전 선택
- 버전 그룹: old (130 = 127-130 대표), new (144 = 131+ 대표)

### 상태 관리 시스템

#### ExecutionStatus (워크플로우 상태)
- `BROWSER_LAUNCHING` → `BROWSER_READY`
- `SEARCHING` → `SEARCH_SUBMITTED` → `RESULTS_LOADED`
- `COMPLETED` / `FAILED`

#### ActionStatus (개별 액션 상태)
- `INIT` → `PENDING` → `STARTED`
- `NAVIGATING` → `LOADED` → `NETWORK_IDLE`
- `SUCCESS` / `ERROR_*`

### Chrome 버전 차단 문제

#### IP Rate Limit 동적 특성
쿠팡의 IP rate limit은 **IP별, 시간별로 동적**으로 변동됨:
- 같은 시간대에도 IP마다 차단 상태가 다를 수 있음
- 시간이 지나면 rate limit이 자동으로 풀릴 수 있음
- 버전별로 차단 임계값이 다를 수 있음

#### 차단 패턴 (IP 상태에 따라 변동)
**패턴 A** (일반적인 경우):
- **130 (구버전)**: 엄격한 IP rate limit → VPN 필수
- **144 (최신), 채널**: 상대적으로 완화 → VPN 없이도 가능할 수 있음

**패턴 B** (IP가 심하게 차단된 경우):
- **모든 버전**: IP rate limit 활성 → VPN 필요

#### 권장 전략
1. **Chrome 130**: 항상 VPN 사용
2. **Chrome 144, 채널**: VPN 없이 시도 → 차단되면 VPN 사용
3. **테스트**: 주기적으로 VPN 없이 테스트하여 rate limit 상태 확인

#### 안정 버전
- **130**: 구버전 TLS 대표 (127-130 그룹)
- **144**: 최신 버전 (131+ 그룹)

### Chrome 채널 지원 (Beta/Dev/Canary)

#### 설치
```bash
# 모든 채널 설치
./install-chrome-versions.sh channels

# 개별 채널 설치
./install-chrome-versions.sh beta
./install-chrome-versions.sh dev
./install-chrome-versions.sh canary

# Stable + 채널 모두 설치
./install-chrome-versions.sh complete
```

#### 사용법
```bash
# 채널명으로 실행
python3 agent.py --version beta
python3 agent.py --version dev
python3 agent.py --version canary

# VPN과 함께 사용
python3 agent.py --version beta --vpn 0
```

#### 테스트 결과 (2025-11-01)
| 채널 | 버전 | VPN 없이 | VPN 사용 |
|------|------|----------|----------|
| Beta | 143.0.7499.4 | ❌ 차단 | ✅ 정상 |
| Dev | 144.0.7500.2 | ❌ 차단 | ✅ 정상 |
| Canary | 144.0.7504.0 | ❌ 차단 | ✅ 정상 |

**결론**: Beta/Dev/Canary도 IP rate limit을 우회하지 못함. Stable 버전과 동일하게 VPN 필요.

#### 빌드 번호 다양성 전략

**문제점**: 같은 빌드 번호를 계속 사용하면 패턴 탐지 가능성
- 쿠팡이 IP + Chrome version + User-Agent 조합을 추적할 경우
- 특정 IP에서 계속 같은 버전만 사용하는 패턴 의심 가능

**해결 전략**:
1. **채널 활용**: Stable 143과 Beta 143은 빌드 번호가 다름
   - Stable 143: 143.0.6948.x
   - Beta 143: 143.0.7499.4
   - User-Agent의 빌드 번호가 다르므로 다양성 확보

2. **랜덤 버전 선택**: `agent.py` 실행 시 버전 지정 없으면 자동 랜덤
   ```python
   # multi_browser_manager.py의 get_random_chrome() 사용
   # 130, 144 + Beta/Dev/Canary 중 랜덤 선택
   ```

3. **주기적 채널 업데이트**: Beta/Dev/Canary는 매주 새 버전 출시
   ```bash
   # 최신 채널 버전으로 업데이트
   ./install-chrome-versions.sh channels
   ```

4. **VPN 서버 로테이션**: 같은 버전이라도 IP를 바꿔서 사용
   ```bash
   python3 agent.py --version 134 --vpn 0  # wg0/vpn0 사용
   python3 agent.py --version 134 --vpn 1  # wg1/vpn1 사용 (다른 IP)
   python3 agent.py --version 134 --vpn 2  # wg2/vpn2 사용 (또 다른 IP)
   ```

**권장 사용 패턴**:
- 단일 작업: 랜덤 버전 사용 (`python3 agent.py`)
- 대량 작업: 버전 + VPN 서버 조합 로테이션
- 장기 운영: 주 1회 채널 업데이트로 빌드 번호 갱신

### 캐시 관리
- **공유 캐시 크기 제한**: 500MB (`--disk-cache-size=524288000`)
- **자동 정리**: 72시간 이상 미사용 파일 삭제
- **캐시 보존**: `clear_all_storage()` 실행 시에도 캐시는 유지

### 종료 방법
브라우저 실행 중 종료:
1. **Enter 키**: 터미널에서 Enter만 누르면 종료
2. **Ctrl+C**: 키보드 인터럽트
3. **창 닫기**: 브라우저 창 직접 닫기

모든 종료 방법에서 브라우저 상태를 체크하여 자동으로 정리됩니다.

## 디렉토리 구조

```
agent/
├── agent.py                      # 메인 진입점 (VPN 재실행 로직 포함)
├── multi_browser_manager.py      # 버전 관리 및 브라우저 선택
├── install-chrome-versions.sh    # Chrome 다운로드 스크립트
├── lib/
│   ├── core/
│   │   └── browser_core_uc.py    # undetected-chromedriver 코어
│   ├── modules/
│   │   └── coupang_handler_selenium.py  # 쿠팡 핸들러
│   ├── utils/
│   │   └── human_behavior_selenium.py   # 사람 행동 시뮬레이션
│   └── constants.py              # 상수 및 상태 정의
├── chrome-version/               # Chrome 바이너리
│   ├── 130/                      # 구버전 TLS (127-130 대표)
│   ├── 144/                      # 최신 버전 (131+ 대표)
│   ├── beta/                     # Chrome Beta 채널
│   ├── dev/                      # Chrome Dev 채널
│   └── canary/                   # Chrome Canary 채널
└── browser-profiles/             # 프로필 디렉토리
    ├── chrome-{version}/         # 버전별 독립 프로필
    │   ├── Default/              # 쿠키, 세션, 로컬스토리지
    │   └── ...
    └── shared-cache/             # 공유 캐시 (모든 버전)
```

## 의존성

```bash
pip install undetected-chromedriver selenium
```

**선택적**:
- VPN 클라이언트: https://github.com/service0427/vpn

## 문제 해결

### "chrome not reachable" 오류 (Chrome 131+)
WSL 환경에서 발생하는 렌더러 프로세스 문제. `BrowserCoreUC.get_chrome_options()`에 다음 플래그 확인:
```python
--disable-gpu
--disable-software-rasterizer
--disable-features=VizDisplayCompositor
```

### VPN 사용 시 "sudo password required" 오류
`/etc/sudoers.d/vpn-access`에 다음 설정 추가 (VPN 서버 개수에 맞춰 조정):
```
tech ALL=(vpn0,vpn1,vpn2,vpn3,...) NOPASSWD: ALL
```

**VPN 서버 추가**:
```bash
cd ~/vpn-ip-rotation/client
./sync.sh  # VPN 서버 동기화
```

### "http2_protocol_error" 탐지
IP 차단 또는 버전 차단. VPN 사용 권장:
```bash
python3 agent.py --version 130 --vpn 0
```

### 캐시 공간 부족
수동 정리:
```python
core = BrowserCoreUC()
core.clean_old_cache(max_age_hours=24)  # 24시간 이상 미사용 캐시 삭제
```

## 코드 수정 시 주의사항

**🇰🇷 주의: 코드 수정 설명도 반드시 한국어로 작성하세요! 🇰🇷**

1. **VPN 재실행 로직 수정 금지**: `agent.py`의 `os.execvpe()` 패턴은 무한 루프 방지를 위해 `VPN_EXECUTED` 환경 변수 체크가 필수
2. **캐시 경로 변경 시**: `shared_cache_dir`와 `user_data_dir`를 혼동하지 말 것
3. **Chrome 옵션 추가 시**: WSL 호환성 플래그를 제거하지 말 것
4. **프로필 초기화**: `clear_all_storage()`는 캐시를 삭제하지 않음 - 의도적 설계
5. **한국어 설정**: `--lang=ko-KR`과 prefs의 `intl.accept_languages` 모두 필요
6. **응답 언어**: 모든 설명, 분석, 오류 메시지는 한국어로 작성

## 성능 최적화 팁

1. **프로필 재사용**: 매번 새 프로필 생성하지 말고 `use_profile=True` 사용
2. **공유 캐시**: 디스크 I/O 감소 및 트래픽 절약
3. **버전 선택 전략**:
   - 구버전 TLS: `--version 130`
   - 최신 버전: `--version 144`
   - IP 차단 우회: VPN + Chrome 130

## 스크린샷 업로드 기능

### 개요
캡처한 스크린샷을 자동으로 서버에 업로드하는 기능입니다.

### 활성화 방법

1. **agent.py 설정 수정**:
```python
# 스크린샷 업로드 기능 활성화 플래그 및 설정
ENABLE_SCREENSHOT_UPLOAD = True  # False → True로 변경
UPLOAD_SERVER_URL = "http://localhost:8000/upload"  # 서버 URL 설정
```

2. **테스트 서버 실행** (로컬 테스트용):
```bash
# Flask 설치
pip install flask

# 테스트 서버 실행
python3 test_upload_server.py
```

3. **Agent 실행**:
```bash
python3 agent.py --version 134 --keyword "노트북"
```

### 주요 기능

1. **자동 업로드**: 스크린샷 캡처 후 자동으로 서버에 업로드
2. **재시도 로직**: 네트워크 오류 시 최대 3회 자동 재시도
3. **메타데이터 전송**: 키워드, 버전, VPN, 상품 정보 함께 전송
4. **에러 처리**: 업로드 실패 시 로컬 파일 보존

### 업로드 디렉토리 구조

```
uploaded_screenshots/
├── chrome-130/
│   ├── local/
│   │   ├── 노트북_before_viewport_20251101_123456.png
│   │   └── 노트북_after_viewport_20251101_123457.png
│   ├── vpn1/
│   └── vpn2/
├── chrome-134/
└── chrome-beta/
```

### 서버 구현 예시

**Flask:**
```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    keyword = request.form.get('keyword')
    # 파일 저장 로직
    return jsonify({'success': True}), 200

app.run(host='0.0.0.0', port=8000)
```

**상세 가이드**: [SCREENSHOT_UPLOAD_GUIDE.md](SCREENSHOT_UPLOAD_GUIDE.md) 참고

---

## ⚠️ 마지막 필수 확인사항 ⚠️

### 🇰🇷 한국어 응답 규칙 (최종 확인) 🇰🇷

**Claude Code가 이 저장소에서 작업할 때 절대적으로 지켜야 할 규칙:**

1. ✅ **모든 응답은 한국어로 작성**
2. ✅ **코드 설명은 한국어로 작성**
3. ✅ **오류 분석은 한국어로 작성**
4. ✅ **Insight 블록은 한국어로 작성**
5. ✅ **기술 문서는 한국어로 작성**
6. ✅ **사용자와의 모든 대화는 한국어로 작성**

**❌ 영어로 응답하는 것은 절대 금지됩니다!**

**🔴 이 규칙을 위반하지 마세요! 🔴**

---

---

## 📝 코드 관리 원칙 (2025-11-03 업데이트)

### 중요한 원칙

**⚠️ 문서화 정책:**
1. **중요한 설명은 코드에 직접 주석으로 작성**
2. **별도 문서는 시간이 지나면 업데이트를 따라가지 못함**
3. **함수/변수 용도는 코드에서 바로 알 수 있도록**
4. **CLAUDE.md, README.md는 관리 차원의 가이드만**

### 순수 오리지널 워크플로우

**2025-11-03: Edit 모드 완전 제거 완료**

- 워크플로우: `Main → Search → Match → Highlight → Watermark → Capture → Upload`
- Edit 모드 관련 코드 모두 제거
- 순위 조작, 페이지 이동, DOM 교체 기능 삭제
- 파일 크기: 1,485 라인 → 748 라인 (50% 감소)

### 핵심 버그 및 주의사항

#### 1. Dictionary 병합 순서 버그 (2025-11-03 발견)

**위치**: `/home/tech/agent/lib/modules/product_finder.py:169-175`

**문제**: `**url_params`의 위치에 따라 rank 값이 잘못 저장됨

**잘못된 코드**:
```python
items_info.append({
    "rank": organic_rank,  # 1, 2, 3, 4, 5...
    **url_params  # url_params의 "rank"가 덮어씀!
})
# 결과: 1, 2, 3, 6, 7, 8... (4, 5 건너뛰어짐)
```

**올바른 코드**:
```python
items_info.append({
    **url_params,  # 먼저 적용
    "rank": organic_rank  # 올바른 값으로 덮어씀
})
# 결과: 1, 2, 3, 4, 5, 6... (정상)
```

**영향**: 
- debug-overlay의 순위 표시 오류
- watermark 위치 계산 오류
- Edit 모드의 순위 조작 버그 원인

**해결**: product_finder.py에 상세한 주석 추가 (Line 153-168)

#### 2. 워터마크 중복 표시 제거

**제거된 워터마크**:
- 파란색 `custom-rank-overlay` (Edit 모드용)
- 초록색 타겟 상품 워터마크 (Edit 모드용)

**현재 워터마크**:
- 쿠팡 원본 (1~10위, 빨강색)
- 커스텀 워터마크 (11위 이상, 주황색 `#FF6B00`, 좌측 중앙)

### 모듈 책임

#### Core Modules
- `browser_core_uc.py`: undetected-chromedriver 관리
- `coupang_handler_selenium.py`: 쿠팡 페이지 조작
- `product_finder.py`: 상품 검색 및 매칭 ⚠️ rank 버그 주의!

#### Workflow
- `search_workflow.py`: 순수 오리지널 워크플로우
  - Edit 모드 제거 완료
  - 불필요한 import, 변수 제거 완료

#### Utilities
- `watermark_display.py`: 워터마크 표시 (11위 이상)
- `highlight_preset.py`: 상품 강조 표시
- `screenshot_processor.py`: 스크린샷 캡처 및 업로드

### 코드 수정 시 체크리스트

1. **주석 작성**: 중요한 로직은 코드에 직접 주석 작성
2. **Dictionary 병합**: `**dict` 순서 확인 (덮어쓰기 주의)
3. **import 정리**: 사용하지 않는 import 제거
4. **변수 정리**: 사용하지 않는 변수 제거
5. **한국어**: 모든 주석, 출력, 문서는 한국어로

### 디버깅 팁

**디버그 파일 생성**:
- 위치: `/home/tech/agent/debug_logs/debug_overlay_*.json`
- 내용: items_info 데이터 (rank, dom_index, is_ad 등)
- 용도: 콘솔 로그만으로 발견할 수 없는 버그 추적

**활성화**: `Config.ENABLE_DEBUG_OVERLAY = True` (기본값)

---

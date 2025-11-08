# UC Rank Screenshot

undetected-chromedriver + VPN 키 풀을 사용한 쿠팡 자동화 시스템

## 🎯 주요 기능

- ✅ **Chrome 130, 144 버전 지원** (구버전 TLS + 최신 버전)
- ✅ **undetected-chromedriver** - 자동화 탐지 우회
- ✅ **TLS 핑거프린팅 우회** - 버전별 다양성
- ✅ **VPN 키 풀** - 동적 VPN 할당/반납 (50개 용량)
- ✅ **wg101-112 시스템** - UID 기반 정책 라우팅
- ✅ **멀티 워커 지원** - 최대 12개 워커 동시 실행
- ✅ **네트워크 자동 복구** - 와치독 시스템
- ✅ **버전별 프로필 분리** - 쿠키/세션/로컬스토리지
- ✅ **캐시 보존 전략** - 트래픽 32% 절감
- ✅ **한국어 브라우저 설정**
- ✅ **1920x1080 고정 viewport**

## 📦 설치

### ⚡ 자동 설치 (2줄)

**우분투 22.04 LTS에서 한 번에 모든 설정 완료:**

```bash
git clone https://github.com/service0427/rank_screenshot.git
cd rank_screenshot && ./setup.sh
```

**설치되는 항목:**
- ✅ Python 3.10+ 및 pip
- ✅ WireGuard (VPN 키 풀용)
- ✅ 필수 시스템 라이브러리 (Chrome 실행용)
- ✅ Python 패키지 (undetected-chromedriver, selenium, psutil)
- ✅ Chrome 130 (구버전 TLS)
- ✅ Chrome 144 (최신 버전)
- ✅ 시스템 사용자 (wg101 ~ wg112)
- ✅ 정책 라우팅 (Table 101-112)
- ✅ sudoers 권한 설정
- ✅ 네트워크 와치독 자동 실행

**설치 후 바로 실행:**
```bash
# 6개 워커로 멀티 실행
python3 uc_run_workers.py -t 6

# 단일 테스트
python3 uc_agent.py --version 130 --keyword "노트북" --close
```

---

### 🔧 수동 설치 (선택사항)

<details>
<summary>수동 설치 가이드 보기 (클릭)</summary>

#### 1. Chrome 버전 설치

```bash
# Chrome 130, 144 자동 설치
./install-chrome-versions.sh
```

스크립트는 자동으로 두 가지 Chrome 버전을 설치합니다:
- **Chrome 130**: 구버전 TLS (127-130 대표)
- **Chrome 144**: 최신 버전 (131+ 대표)

실행하면 기존 폴더를 확인하고 없는 버전만 자동으로 다운로드 및 설치합니다.

#### 2. Python 패키지 설치

VPN 사용을 위해 시스템 전역 설치 필요:

```bash
sudo pip3 install -r requirements.txt
```

또는 개별 설치:
```bash
sudo pip3 install undetected-chromedriver selenium Pillow requests
```

**참고**: `--user` 플래그를 사용하면 VPN 환경에서 패키지를 찾지 못합니다.

#### 3. 권한 설정 (VPN 사용 시 필수)

VPN과 함께 사용하는 경우 권한 설정이 필요합니다:

```bash
# 권한 설정 스크립트 실행
./setup-permissions.sh
```

이 스크립트는 다음을 설정합니다:
- Agent 디렉토리 읽기 권한
- Browser profiles 쓰기 권한
- ChromeDriver 캐시 쓰기 권한
- Python 패키지 읽기 권한

**배포 시 주의사항:**
- 서버 환경마다 경로가 다를 수 있음
- VPN 클라이언트 설치 후 실행 권장
- 권한 오류 발생 시 재실행

</details>

## 🚀 사용법

### 멀티 워커 실행 (권장)

**VPN 키 풀을 사용한 동시 다중 작업**:

```bash
# 기본 실행 (6개 워커)
python3 uc_run_workers.py -t 6

# 최대 워커 (12개)
python3 uc_run_workers.py -t 12

# 특정 Chrome 버전 지정
python3 uc_run_workers.py -t 6 --version 130
```

**특징**:
- ✅ **VPN 키 풀 자동 할당** - 각 워커마다 독립적인 VPN 연결
- ✅ **wg101-112 시스템** - UID 기반 정책 라우팅
- ✅ **프로세스 격리** - 각 워커는 독립 사용자로 실행
- ✅ **프로필 분리** - 워커별 독립 Chrome 프로필
- ✅ **자동 복구** - 네트워크 와치독 시스템

### 단일 실행 (테스트용)

**개별 Chrome 버전 테스트**:

```bash
# Chrome 130 테스트
python3 uc_agent.py --version 130 --keyword "노트북" --close

# Chrome 144 테스트
python3 uc_agent.py --version 144 --keyword "게임" --close

# 자동 종료 없이 실행
python3 uc_agent.py --version 130 --keyword "노트북"
```

**명령행 옵션**:
```bash
# 특정 버전 지정
python3 uc_agent.py --version 134
python3 uc_agent.py --version beta

# 키워드 지정
python3 uc_agent.py --version 134 --keyword "게임"

# 자동 종료 (3초 후)
python3 uc_agent.py --version 134 --close

# 탐지 테스트 실행
python3 uc_agent.py --version 134 --test-detection
```

### VPN 키 풀 시스템

**자동 VPN 할당 (멀티 워커)**:
- `uc_run_workers.py`는 자동으로 VPN 키 풀에서 VPN을 할당합니다
- 각 워커는 wg101-112 사용자로 실행됩니다
- UID 1101-1112 기반 정책 라우팅이 자동으로 적용됩니다

**wg101-112 시스템**:

| Worker ID | 사용자명 | UID | 라우팅 테이블 | 프로필 경로 |
|-----------|----------|-----|---------------|-------------|
| 1 | wg101 | 1101 | 101 | uc_browser-profiles/wg101/{130,144} |
| 2 | wg102 | 1102 | 102 | uc_browser-profiles/wg102/{130,144} |
| ... | ... | ... | ... | ... |
| 12 | wg112 | 1112 | 112 | uc_browser-profiles/wg112/{130,144} |

**특징**:
- ✅ **메인 이더넷 보존** - VPN 트래픽은 정책 라우팅으로 분리
- ✅ **50개 VPN 용량** - 5개 서버 × 10개 동시 접속
- ✅ **동적 할당/반납** - 워커 시작/종료 시 자동 관리

### 종료 방법

브라우저 실행 중 다음 방법으로 종료할 수 있습니다:
- **Enter 키**: 터미널에서 Enter만 누르면 종료
- **Ctrl+C**: 키보드 인터럽트로 종료
- **창 닫기**: 브라우저 창을 직접 닫기

## 📁 프로젝트 구조

```
rank_screenshot/
├── uc_agent.py                   # 단일 실행 진입점
├── uc_run_workers.py             # 멀티 워커 오케스트레이션
├── setup.sh                      # 자동 설치 스크립트
├── cleanup_all_wg.sh             # VPN 연결 정리 스크립트
├── network_watchdog.sh           # 네트워크 자동 복구
├── install-chrome-versions.sh    # Chrome 설치 스크립트
│
├── common/                       # 🔄 공통 모듈
│   ├── constants.py              # 전역 설정 및 상태
│   ├── vpn_api_client.py         # VPN 키 풀 클라이언트
│   ├── vpn_connection_tracker.py
│   └── utils/                    # 공통 유틸리티
│       ├── human_behavior_selenium.py
│       ├── highlight_preset.py
│       └── ...
│
├── uc_lib/                       # 🔵 UC 시스템 (현재 운영)
│   ├── core/
│   │   └── browser_core_uc.py    # undetected-chromedriver 래퍼
│   ├── modules/
│   │   ├── coupang_handler_selenium.py  # 쿠팡 핸들러
│   │   ├── product_finder.py     # 상품 검색 및 매칭
│   │   └── screenshot_*.py       # 스크린샷 관련
│   └── workflows/
│       └── search_workflow.py    # 검색 워크플로우
│
├── chrome-version/               # Chrome 바이너리
│   ├── 130/                      # 구버전 TLS (127-130 대표)
│   └── 144/                      # 최신 버전 (131+ 대표)
│
└── uc_browser-profiles/          # UC 프로필 디렉토리
    └── wg10N/                    # wg101-112 사용자별 프로필
        ├── 130/                  # Chrome 130 프로필
        │   └── Default/          # 쿠키, 세션, 로컬스토리지
        └── 144/                  # Chrome 144 프로필
            └── Default/
```

## 🔧 Import 경로 규칙

**UC 시스템**:
```python
# UC 전용 모듈
from uc_lib.core.browser_core_uc import BrowserCoreUC
from uc_lib.modules.coupang_handler_selenium import CoupangHandlerSelenium

# 공통 모듈
from common.constants import Config, ExecutionStatus
from common.vpn_api_client import VPNAPIClient
from common.utils.human_behavior_selenium import HumanBehaviorSelenium
```

**특징**:
- ✅ **공통 모듈** (`common/`) - UC와 nodriver(예정) 공유
- ✅ **UC 전용 모듈** (`uc_lib/`) - undetected-chromedriver 전용
- ✅ **절대 import** - 모든 모듈은 절대 경로로 import

## 💡 주요 기능 설명

### 1. 버전별 프로필 분리

각 Chrome 버전마다 독립적인 프로필을 사용합니다:
- **쿠키**: 버전별 독립
- **세션 스토리지**: 버전별 독립
- **로컬 스토리지**: 버전별 독립
- **캐시**: 모든 버전이 공유 (트래픽 절약)

### 2. 공유 캐시 시스템

```
browser-profiles/
├── chrome-127/     (3.6MB - 프로필만)
├── chrome-134/     (3.7MB - 프로필만)
└── shared-cache/   (15MB - 공유 캐시)
```

**절약 효과**:
- 비공유: ~216MB (18 × 12MB)
- 공유: ~78MB (15MB + 18 × 3.5MB)
- **약 70% 절약**

### 3. 자동 캐시 정리

72시간 이상 사용되지 않은 캐시 파일을 자동으로 삭제하여 디스크 공간을 관리합니다.

### 4. 한국어 환경 설정

- `navigator.language`: ko-KR
- Accept-Language 헤더: ko-KR,ko;q=0.9
- 번역 제안 비활성화

### 5. Viewport 고정

내부 콘텐츠 영역을 1920x1080으로 고정하여 일관된 렌더링을 제공합니다.

## 🔧 기술 스택

- **Python 3.12+**
- **Selenium 4.x**
- **undetected-chromedriver 3.x**
- **Chrome for Testing 127~144**

## 📊 실행 예시

### 멀티 워커 실행 (6개 워커)

```bash
$ python3 uc_run_workers.py -t 6

============================================================
🚀 UC Multi-Worker System
============================================================
Target Workers: 6
Chrome Version: Random selection
VPN Key Pool: Enabled (wg101-112)
============================================================

[Worker-1] Starting as wg101 (UID 1101, Table 101)...
[Worker-1] VPN allocated: 10.8.0.14 (Server #1)
[Worker-1] Chrome 130 launching...

[Worker-2] Starting as wg102 (UID 1102, Table 102)...
[Worker-2] VPN allocated: 10.8.0.18 (Server #2)
[Worker-2] Chrome 144 launching...

...

[Worker-6] Starting as wg106 (UID 1106, Table 106)...
[Worker-6] VPN allocated: 10.8.0.26 (Server #1)
[Worker-6] Chrome 130 launching...

============================================================
✅ All 6 workers started successfully
============================================================
```

### 단일 실행 예시

```bash
$ python3 uc_agent.py --version 134 --keyword "노트북" --close

============================================================
🤖 UC Rank Screenshot - Selenium + undetected-chromedriver
============================================================
Instance ID: 1
Keyword: 노트북
Chrome Version: 134
Detection Test: False
============================================================

🧹 Cleaning cache older than 72 hours...
   ✓ No old cache to clean
🚀 Launching Chrome 134 with undetected-chromedriver...
   Path: /home/tech/rank_screenshot/chrome-version/134/chrome-linux64/chrome
   Profile: /home/tech/rank_screenshot/uc_browser-profiles/chrome-134
   ✓ Chrome launched (undetected-chromedriver)
   ✓ Anti-detection: ENABLED by default

============================================================
🔍 Browser Version Information
============================================================
   Chrome Version: 134.0.6998.165
   └─ Major: 134 | Minor: 0 | Build: 6998 | Patch: 165
   User Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36
   Language: ko-KR
   Languages: ['ko-KR']
   Viewport: 1920x1080
============================================================

============================================================
🌐 Checking IP Address
============================================================
   Public IP: 112.161.221.193
============================================================

🧹 Clearing cookies, session & local storage (cache preserved)...
   ✓ All storage cleared (cache preserved)
🏠 Navigating to Coupang home...
   ✓ Home page loaded
🔍 Searching for: 노트북
   ✓ Search script executed for: 노트북
   ✓ Search completed

🔍 Checking for errors...

============================================================
✅ SUCCESS: No errors detected!
============================================================
Current URL: https://www.coupang.com/np/search?component=&q=노트북&traceId=...
Status: {'execution_status': 'RESULTS_LOADED', 'action_status': 'SUCCESS', ...}
============================================================
```

## 📝 라이센스

MIT License

---

## 🎯 순수 오리지널 워크플로우 (2025-11-03 업데이트)

**Edit 모드 완전 제거 완료**

### 워크플로우

```
Main → Search → Match → Highlight → Watermark → Capture → Upload
```

### 핵심 변경사항

1. **코드 크기 감소**: 1,485 라인 → 748 라인 (50% 감소)
2. **Edit 모드 제거**: 순위 조작, 페이지 이동, DOM 교체 기능 삭제
3. **워터마크 단순화**: 
   - 쿠팡 원본 (1~10위) 유지
   - 커스텀 워터마크 (11위 이상) 추가
   - 타겟 상품 구분 제거

### 주요 모듈

| 모듈 | 책임 | 위치 |
|------|------|------|
| `search_workflow.py` | 워크플로우 관리 | `lib/workflows/` |
| `product_finder.py` | 상품 검색 및 매칭 | `lib/modules/` |
| `watermark_display.py` | 워터마크 표시 | `lib/modules/rank/` |
| `screenshot_processor.py` | 캡처 및 업로드 | `lib/utils/` |

### 중요 버그 수정 (2025-11-03)

**Dictionary 병합 순서 버그** - `product_finder.py:169-175`

- **문제**: `**url_params`의 위치에 따라 rank 값이 잘못 저장됨
- **증상**: debug-overlay 순위가 1,2,3,6,7,8... (4,5 건너뛰어짐)
- **해결**: 올바른 순서로 변경 (`**url_params` 먼저, `"rank": organic_rank` 나중)
- **상세**: 코드에 주석으로 상세 설명 추가

### 디버깅

**디버그 파일 생성**:
```bash
# 디버그 파일 위치
/home/tech/agent/debug_logs/debug_overlay_*.json
```

**활성화**: `Config.ENABLE_DEBUG_OVERLAY = True` (기본값)

**용도**: 콘솔 로그만으로 발견할 수 없는 버그 추적

---

## 🔐 VPN 키 풀 시스템 (wg101-112)

### 개요

**VPN 키 풀 (VPN Key Pool)**은 다중 워커 환경에서 VPN 자원을 동적으로 할당/관리하는 시스템입니다.

### 시스템 사양

| 항목 | 사양 |
|------|------|
| VPN 서버 | 5개 |
| 서버당 동시 접속 | 10개 |
| 총 VPN 용량 | 50개 |
| **시스템 사용자** | **wg101 ~ wg112** |
| **UID 범위** | **1101-1112** |
| **라우팅 테이블** | **101-112** |
| 워커 최대 동시 실행 | 12개 |

### wg101-112 통합 네이밍 시스템

**핵심 설계**: 모든 식별자가 하나의 숫자로 통일됨

| Worker ID | 사용자명 | UID | 라우팅 테이블 | 인터페이스 | 프로필 경로 |
|-----------|----------|-----|---------------|------------|-------------|
| 1 | wg101 | 1101 | 101 | wg-10-8-0-14 | uc_browser-profiles/wg101/{130,144} |
| 2 | wg102 | 1102 | 102 | wg-10-8-0-18 | uc_browser-profiles/wg102/{130,144} |
| ... | ... | ... | ... | ... | ... |
| 12 | wg112 | 1112 | 112 | wg-10-8-0-26 | uc_browser-profiles/wg112/{130,144} |

**장점**:
- ✅ **직관적** - 숫자만 보면 모든 정보 파악 가능
- ✅ **충돌 없음** - UID 1101-1112는 시스템 서비스와 충돌하지 않음
- ✅ **단순한 프로필 경로** - wg101 → uc_browser-profiles/wg101/

### 실행 방법

**멀티 워커 실행**:

```bash
# 기본 실행 (6개 워커)
python3 uc_run_workers.py -t 6

# 최대 실행 (12개 워커)
python3 uc_run_workers.py -t 12

# 특정 Chrome 버전 지정
python3 uc_run_workers.py -t 6 --version 130
```

### 주요 특징

- ✅ **동적 VPN 할당**: 워커별로 VPN 키를 자동 할당/반납
- ✅ **정책 라우팅**: UID 1101-1112 기반 라우팅으로 메인 이더넷 보존
- ✅ **프로세스 격리**: 각 워커는 wg10N 사용자로 실행
- ✅ **프로필 분리**: 워커별 독립적인 Chrome 프로필
- ✅ **ChromeDriver 격리**: 사용자별 ChromeDriver 경로로 충돌 방지
- ✅ **네트워크 자동 복구**: 와치독 시스템 (5분마다 체크)

### 아키텍처

```
uc_run_workers.py
    ↓
Worker Thread 1-12
    ↓
VPNConnection (VPN 키 할당)
    ↓
WireGuard (wg-10-8-0-N)
    ↓
Policy Routing (UID 1101-1112 → Table 101-112)
    ↓
sudo -u wg10N python3 uc_agent.py
    ↓
Chrome (uc_browser-profiles/wg10N/)
```

### 정책 라우팅 예시

```bash
# wg101 (UID 1101)의 트래픽은 라우팅 테이블 101 사용
ip rule add uidrange 1101-1101 table 101

# 라우팅 테이블 101은 wg-10-8-0-14 인터페이스를 통해 VPN으로
ip route add default via 10.8.0.1 dev wg-10-8-0-14 table 101
```

### 테스트 검증 (2025-11-07)

**12개 워커 테스트**:
- ✅ VPN 키 할당: 12/12 (100%)
- ✅ VPN 연결: 12/12 (100%)
- ✅ 정책 라우팅: 12/12 (100%)
- ✅ 브라우저 실행: 12/12 (100%)
- ✅ 메인 이더넷: 보존 확인
- ✅ ERR_NETWORK_CHANGED: 0건

### 권장 운영 방식

| 용도 | 워커 수 | 특징 |
|------|---------|------|
| 개발/테스트 | 1-2개 | 빠른 디버깅 |
| 소규모 운영 | 4-8개 | 안정적, 모니터링 쉬움 |
| **대규모 운영** | **12개** | **권장 최대** |

### 필수 스크립트

**VPN 연결 정리**:
```bash
# VPN 연결만 정리
./cleanup_all_wg.sh

# VPN 연결 + Chrome 프로세스 종료
./cleanup_all_wg.sh --kill-chrome
```

**네트워크 자동 복구**:
- `network_watchdog.sh` - 1분마다 네트워크 상태 체크
- Crontab으로 자동 실행 (setup.sh에서 설정)
- 3회 연속 실패 시 자동 복구 시작
- 데몬 방식 대신 1회 실행 방식 (메모리 효율적)

### 문제 해결

**Crontab에 와치독이 등록되지 않은 경우**:

setup.sh 실행 후 와치독이 자동 등록되어야 하지만, 실패한 경우 수동으로 등록할 수 있습니다:

```bash
# 1. Crontab 확인
crontab -l | grep watchdog

# 2. 등록되지 않았다면 수동 등록
(
  crontab -l 2>/dev/null || true
  echo ""
  echo "# 네트워크 와치독 - 1분마다 네트워크 상태 체크"
  echo "* * * * * /home/tech/rank_screenshot/network_watchdog.sh >> /tmp/network_watchdog.log 2>&1"
) | crontab -

# 3. 와치독 즉시 실행
/home/tech/rank_screenshot/network_watchdog.sh >> /tmp/network_watchdog.log 2>&1

# 4. 확인
crontab -l | grep watchdog && echo "✅ Crontab 등록 완료" || echo "❌ 등록 실패"
```

**주의**: 경로 `/home/tech/rank_screenshot/`는 실제 설치 경로에 맞게 수정하세요.

---

## 📖 문서

- **CLAUDE.md**: Claude Code 작업 가이드 및 관리 원칙
- **README.md**: 프로젝트 개요 및 빠른 시작 (이 문서)

**중요**: 함수/변수 용도는 코드에 직접 주석으로 작성되어 있습니다.

---

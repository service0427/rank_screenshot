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

---

## 📁 프로젝트 폴더 구조 (2025-11-07 업데이트)

### 병렬 시스템 구조

현재 프로젝트는 **UC (undetected-chromedriver)** 시스템을 운영하며, 향후 **nodriver** 전환을 위한 병렬 구조를 유지합니다.

```
rank_screenshot/
├── common/                      # 🔄 공통 모듈 (UC + nodriver 공유)
│   ├── vpn_api_client.py        # VPN 키 풀 클라이언트
│   ├── vpn_connection_tracker.py
│   ├── constants.py             # 전역 설정 (Config, ExecutionStatus 등)
│   └── utils/                   # 공통 유틸리티
│       ├── human_behavior_selenium.py
│       ├── highlight_preset.py
│       └── ... (6개 파일)
│
├── uc_lib/                      # 🔵 UC 시스템 (현재 운영 중)
│   ├── core/                    # - undetected-chromedriver 래퍼
│   │   └── browser_core_uc.py
│   ├── modules/                 # - UC 전용 모듈
│   │   ├── coupang_handler_selenium.py
│   │   ├── product_finder.py
│   │   └── screenshot_*.py
│   └── workflows/               # - 검색 워크플로우
│       └── search_workflow.py
│
├── no_lib/                      # 🟢 nodriver 시스템 (개발 예정)
│   ├── core/                    # - 비동기 (async/await)
│   ├── modules/                 # - CDP 직접 통신
│   └── workflows/               # - 탐지율 개선 목표
│
├── uc_agent.py                  # 🔵 UC 메인 진입점 (사용 중)
├── uc_run_workers.py            # 🔵 UC 멀티 워커 (사용 중)
│
├── no_agent.py                  # 🟢 nodriver 진입점 (미작성)
├── no_run_workers.py            # 🟢 nodriver 멀티 워커 (미작성)
│
├── uc_browser-profiles/         # 🔵 UC 프로필 디렉토리
│   └── wg10N/                   # wg101-112 사용자별 프로필
│       ├── 130/                 # Chrome 130 프로필
│       └── 144/                 # Chrome 144 프로필
│
├── no_browser-profiles/         # 🟢 nodriver 프로필 (미사용)
│
└── chrome-version/              # 공유 리소스
    ├── 130/
    └── 144/
```

### Import 경로 규칙

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

**nodriver 시스템** (미래):
```python
# nodriver 전용 모듈
from no_lib.core.browser_core_no import BrowserCoreNo
from no_lib.modules.coupang_handler_no import CoupangHandlerNo

# 공통 모듈 (동일)
from common.constants import Config
from common.vpn_api_client import VPNAPIClient
```

### 폴더 접두사 의미

| 접두사 | 의미 | 상태 | 설명 |
|--------|------|------|------|
| **uc_** | **U**ndetected-**C**hromedriver | 🔵 운영 중 | Selenium 기반, 안정적 |
| **no_** | **no**driver | 🟢 개발 예정 | 비동기, CDP 직접 통신 |
| **common/** | 공통 모듈 | 🔄 공유 | 두 시스템 모두 사용 |

### 주요 파일 설명

**현재 사용 중 (UC 시스템)**:
- `uc_agent.py`: 단일 실행 진입점
- `uc_run_workers.py`: 멀티 워커 오케스트레이션
- `uc_lib/`: 모든 핵심 로직
- `uc_browser-profiles/`: Chrome 프로필 저장소

**미래 계획 (nodriver 시스템)**:
- `no_agent.py`: 비동기 단일 실행
- `no_run_workers.py`: multiprocessing 기반 멀티 워커
- `no_lib/`: CDP 직접 통신 로직

**공통**:
- `common/`: VPN, constants, utils 공유
- `chrome-version/`: Chrome 바이너리 공유
- `screenshots/`, `logs/`: 출력 공유

### 전환 계획

1. **현재**: UC 시스템 안정화 및 개선
2. **Phase 1**: nodriver 프로토타입 작성
3. **Phase 2**: A/B 테스트 (탐지율 비교)
4. **Phase 3**: nodriver 우세 시 완전 전환
5. **정리**: uc_ 제거, no_ → 기본으로 변경

---

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
# Python 패키지 (시스템 전역 설치 - VPN 사용 시 필요)
sudo pip3 install -r requirements.txt

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
BrowserCoreUC (uc_lib/core/browser_core_uc.py)
    ↓ undetected-chromedriver 래퍼
    ↓ 버전별 프로필 관리
    ↓ 공유 캐시 시스템
    ↓
CoupangHandlerSelenium (uc_lib/modules/coupang_handler_selenium.py)
    ↓ 쿠팡 특화 로직
    ↓
HumanBehaviorSelenium (common/utils/human_behavior_selenium.py)
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
rank_screenshot/
├── uc_agent.py                   # 메인 진입점 (VPN 재실행 로직 포함)
├── uc_run_workers.py             # 멀티 워커 오케스트레이션
├── install-chrome-versions.sh    # Chrome 다운로드 스크립트
├── uc_lib/                       # UC 전용 모듈
│   ├── core/
│   │   └── browser_core_uc.py    # undetected-chromedriver 코어
│   ├── modules/
│   │   ├── coupang_handler_selenium.py  # 쿠팡 핸들러
│   │   ├── product_finder.py     # 상품 검색 및 매칭
│   │   └── screenshot_*.py       # 스크린샷 관련
│   └── workflows/
│       └── search_workflow.py    # 검색 워크플로우
├── common/                       # 공통 모듈
│   ├── constants.py              # 상수 및 상태 정의
│   ├── vpn_api_client.py         # VPN 관리
│   └── utils/
│       └── human_behavior_selenium.py   # 사람 행동 시뮬레이션
├── chrome-version/               # Chrome 바이너리
│   ├── 130/                      # 구버전 TLS (127-130 대표)
│   ├── 144/                      # 최신 버전 (131+ 대표)
│   ├── beta/                     # Chrome Beta 채널
│   ├── dev/                      # Chrome Dev 채널
│   └── canary/                   # Chrome Canary 채널
└── uc_browser-profiles/          # UC 프로필 디렉토리
    └── wg10N/                    # wg101-112 사용자별 프로필
        ├── 130/                  # Chrome 130 프로필
        │   └── Default/          # 쿠키, 세션, 로컬스토리지
        └── 144/                  # Chrome 144 프로필
            └── Default/
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

## Import 경로 규칙 (2025-11-07 추가)

### 전역 설정 기반 Import

모든 import 경로는 [common/constants.py](common/constants.py)의 `ImportPaths` 클래스에서 관리됩니다. 프로젝트 구조 변경 시 이 클래스만 수정하면 됩니다.

#### Import 경로 설정

```python
# common/constants.py
class ImportPaths:
    # 기본 모듈 경로
    COMMON = "common"          # 공통 모듈
    UC_LIB = "uc_lib"          # UC 전용 모듈
    NODRIVER_LIB = "nodriver_lib"  # nodriver 전용 모듈

    # 서브 경로
    CORE = "core"
    MODULES = "modules"
    WORKFLOWS = "workflows"
    UTILS = "utils"
```

#### 올바른 Import 예시

```python
# ✅ 공통 모듈 (모든 시스템에서 공유)
from common.constants import Config, ExecutionStatus, ImportPaths
from common.vpn_api_client import VPNAPIClient
from common.utils.human_behavior_selenium import natural_typing

# ✅ UC 전용 모듈
from uc_lib.core.browser_core_uc import BrowserCoreUC
from uc_lib.modules.coupang_handler_selenium import CoupangHandlerSelenium
from uc_lib.modules.product_finder import ProductFinder
from uc_lib.workflows.search_workflow import SearchWorkflow

# ✅ nodriver 전용 모듈 (추후)
from nodriver_lib.core.browser_core_nodriver import BrowserCoreNodriver
from nodriver_lib.modules.coupang_handler_nodriver import CoupangHandlerNodriver
```

#### 잘못된 Import (절대 사용 금지)

```python
# ❌ lib는 이제 존재하지 않음
from lib.constants import Config
from lib.modules.vpn_api_client import VPNAPIClient

# ❌ 상대 import로 공통 모듈 참조 (uc_lib에서 common을 참조할 때)
from ..constants import Config  # 잘못됨!
from ..utils.human_behavior_selenium import natural_typing  # 잘못됨!

# ✅ 올바른 방법: 절대 import 사용
from common.constants import Config
from common.utils.human_behavior_selenium import natural_typing
```

#### Import 경로 변경이 필요한 경우

프로젝트 구조가 변경되어 import 경로를 바꿔야 한다면:

1. **[common/constants.py](common/constants.py) 수정**:
   ```python
   class ImportPaths:
       COMMON = "새로운_경로"  # 여기만 수정
       # ...
   ```

2. **전체 프로젝트에서 일괄 변경**:
   ```bash
   find . -name "*.py" -exec sed -i 's/from common\./from 새로운_경로./g' {} \;
   ```

3. **문서 업데이트**: 이 섹션의 예시도 함께 수정

### 디렉토리 구조별 Import 규칙

| 모듈 위치 | Common 참조 | UC_LIB 참조 | Nodriver 참조 |
|-----------|-------------|-------------|---------------|
| `common/` | 내부 import | ❌ 금지 | ❌ 금지 |
| `uc_lib/` | `from common.` | 내부 import | ❌ 금지 |
| `nodriver_lib/` | `from common.` | ❌ 금지 | 내부 import |
| `tests/` | `from common.` | `from uc_lib.` | `from nodriver_lib.` |

**중요**: `common/`은 UC와 nodriver 양쪽에서 모두 사용하는 공통 모듈이므로, `uc_lib/`나 `nodriver_lib/`를 참조하면 안 됩니다.

---

## 코드 수정 시 주의사항

**🇰🇷 주의: 코드 수정 설명도 반드시 한국어로 작성하세요! 🇰🇷**

1. **Import 경로 규칙 준수**: 위의 "Import 경로 규칙" 섹션을 반드시 따를 것. `from lib.`는 절대 사용 금지.
2. **VPN 재실행 로직 수정 금지**: `agent.py`의 `os.execvpe()` 패턴은 무한 루프 방지를 위해 `VPN_EXECUTED` 환경 변수 체크가 필수
3. **캐시 경로 변경 시**: `shared_cache_dir`와 `user_data_dir`를 혼동하지 말 것
4. **Chrome 옵션 추가 시**: WSL 호환성 플래그를 제거하지 말 것
5. **프로필 초기화**: `clear_all_storage()`는 캐시를 삭제하지 않음 - 의도적 설계
6. **한국어 설정**: `--lang=ko-KR`과 prefs의 `intl.accept_languages` 모두 필요
7. **응답 언어**: 모든 설명, 분석, 오류 메시지는 한국어로 작성

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

## 🔐 VPN 키 풀 시스템 (2025-11-07 업데이트: wg101-112)

### 시스템 개요

**VPN 키 풀 (VPN Key Pool)**은 다중 워커 환경에서 VPN 자원을 동적으로 할당하고 관리하는 시스템입니다.

### wg101-112 통합 네이밍 시스템 (2025-11-07)

**핵심 설계**: 모든 식별자가 하나의 숫자로 통일됨

| Worker ID | 사용자명 | UID | 라우팅 테이블 | 인터페이스 | 프로필 경로 |
|-----------|----------|-----|---------------|------------|-------------|
| 1 | wg101 | 1101 | 101 | wg101 | browser-profiles/wg101/{130,144} |
| 2 | wg102 | 1102 | 102 | wg102 | browser-profiles/wg102/{130,144} |
| ... | ... | ... | ... | ... | ... |
| 12 | wg112 | 1112 | 112 | wg112 | browser-profiles/wg112/{130,144} |

**장점**:
- 숫자만 보면 모든 정보를 알 수 있음 (wg101 → UID 1101, Table 101)
- UID 1101-1112는 시스템 서비스와 충돌하지 않음 (끝 3자리가 101-112로 일치)
- 프로필 경로가 단순하고 직관적

### 시스템 사양

- **VPN 서버 개수**: 5개
- **VPN 서버당 동시 접속**: 10개
- **총 VPN 용량**: 50개 동시 연결 지원
- **시스템 사용자**: wg101 ~ wg112 (12명)
- **워커 최대 이론치**: 20개 (권장: 16개)

**중요**: 하드웨어 제약으로 실제 안정적 운영은 12~16개 워커 권장

### 아키텍처

#### 1. VPN 키 풀 API 서버
- **위치**: 별도 서버 (API 엔드포인트 제공)
- **역할**: VPN 키 할당/반납 관리
- **프로토콜**: HTTP REST API

#### 2. 정책 라우팅 (Policy Routing)
- **UID 기반 라우팅**: 각 wg10N 사용자마다 독립적인 라우팅 테이블
- **UID 범위**: 1101-1112 (wg101 = UID 1101, wg102 = UID 1102, ...)
- **라우팅 테이블**: 101-112 (UID 1101 → Table 101, UID 1102 → Table 102, ...)
- **메인 이더넷 보존**: 일반 사용자(tech)는 메인 라우팅 사용

**예시**:
```bash
# wg101 (UID 1101)의 트래픽은 라우팅 테이블 101 사용
ip rule add uidrange 1101-1101 table 101

# 라우팅 테이블 101은 wg101 인터페이스를 통해 VPN으로
ip route add default via 10.0.X.1 dev wg101 table 101
```

#### 3. WireGuard 인터페이스
- **인터페이스명**: wg-X-X-X-X (내부 IP 기반, 예: wg-10-8-0-14)
- **설정 파일**: /tmp/vpn_configs/wg-X-X-X-X.conf
- **DNS 설정**: 8.8.8.8, 8.8.4.4
- **Table = off**: 커널 자동 라우팅 비활성화 (정책 라우팅 사용)
- **이름 장점**: 인터페이스 이름만 봐도 어떤 IP인지 즉시 파악 가능

#### 4. 프로세스 격리
- **시스템 사용자**: vpn-worker-1 ~ vpn-worker-12
- **실행 방식**: `sudo -u vpn-worker-N python3 agent.py ...`
- **UID 매핑**: vpn-worker-N → UID 2000+N
- **프로필 분리**: 각 워커마다 독립적인 Chrome 프로필
- **ChromeDriver 분리**: `/tmp/chromedriver_{username}_instance_{id}_v{version}/`

### 주요 컴포넌트

#### VPNAPIClient (`common/vpn_api_client.py`)
- VPN 키 풀 API와 통신
- VPN 키 할당/반납 관리
- WireGuard 설정 파일 생성 및 정책 라우팅 적용

#### VPNConnection (`common/vpn_api_client.py`)
- 워커별 VPN 연결 관리
- 자동 할당/해제
- 내부 IP 조회

#### run_workers.py
- 멀티 워커 오케스트레이션
- VPN 키 풀 통합
- X11 권한 부여
- 로그 관리

### 실행 흐름

**워커 시작**:
```
1. run_workers.py가 워커 스레드 생성
2. VPNConnection(worker_id) 초기화
3. VPN 키 풀 API에 키 할당 요청
4. WireGuard 설정 파일 생성 (DNS + 정책 라우팅)
5. wg-quick up으로 VPN 연결
6. sudo -u vpn-worker-N으로 agent.py 실행
7. agent.py가 --vpn-pool-worker N 파라미터 수신
8. Chrome 실행 (UID 2000+N의 트래픽은 자동으로 VPN 라우팅)
```

**워커 종료**:
```
1. agent.py 종료
2. VPNConnection.disconnect() 호출
3. wg-quick down으로 VPN 해제
4. VPN 키 풀 API에 키 반납 요청
```

### agent.py 통합

#### VPN 키 풀 재실행 로직 제거

**이전 방식** (단일 VPN - `--vpn N`):
```python
# os.execvpe()로 vpn 래퍼를 통해 재실행
os.execvpe(vpn_cmd, [vpn_cmd, str(vpn_num), 'python3'] + args, env)
```

**현재 방식** (VPN 키 풀):
```python
# run_workers.py에서 직접 sudo -u vpn-worker-N으로 실행
# agent.py는 재실행하지 않음 (멀티스레드 환경에서 os.execvpe()는 프로세스 교체)
```

**중요**: VPN 키 풀 모드에서는 agent.py에서 `os.execvpe()` 재실행을 하지 않습니다. run_workers.py가 처음부터 올바른 사용자(vpn-worker-N)로 실행하기 때문입니다.

#### 파라미터

- `--vpn-pool-worker N`: VPN 키 풀 워커 ID 지정
- 이 파라미터가 있으면 VPN 디스플레이에 "VPN Pool Worker N" 표시

### 시스템 확장

#### 추가 워커 생성

현재 vpn-worker-1 ~ vpn-worker-12만 존재합니다. 더 많은 워커를 추가하려면:

```bash
# vpn-worker-13 생성
sudo useradd -m -s /bin/bash vpn-worker-13
sudo usermod -u 2013 vpn-worker-13  # UID 2013

# 정책 라우팅 규칙 추가 (VPN 키 풀 API 서버 설정)
ip rule add uidrange 2013-2013 table 212
```

**제약사항**:
- UID 범위: 2001-2050 (50개)
- 라우팅 테이블: 200-249 (50개)
- 시스템 사용자: 필요한 만큼 수동 생성

### 테스트 검증 (2025-11-06)

**50개 워커 테스트 결과**:
- VPN 키 할당: 50/50 (100%)
- VPN 연결: 50/50 (100%)
- 정책 라우팅: 50/50 (100%)
- 프로필 생성: 50/50 (100%)
- 브라우저 실행: 12/50 (시스템 사용자 제약)
- 메인 이더넷: ✅ 보존 확인

**VPN 서버 분포**:
- 5개 서버에 9-11개 워커씩 균등 분배
- IP 중복: 정상 (서버당 10개 동시 접속 허용)

### 필수 설정 스크립트

#### VPN 워커 홈 디렉토리 설정
```bash
./setup_vpn_worker_homes.sh
```
- vpn-worker-1 ~ vpn-worker-12 홈 디렉토리 생성
- `.local`, `.cache` 디렉토리 생성 (undetected-chromedriver용)
- Permission denied 오류 해결

#### 모든 WireGuard 연결 정리

**기본 사용법**:
```bash
# VPN 연결만 정리
./cleanup_all_wg.sh

# VPN 연결 + Chrome 프로세스 종료
./cleanup_all_wg.sh --kill-chrome
```

**정리 대상**:
- `/home/tech/vpn/client` (sync.sh) 방식: wg0~wg36
- VPN 키 풀 방식: wg-10-8-0-14, wg-10-8-0-18 등
- wg101-112 방식: wg101~wg112 (새 시스템)

**정리 단계**:
1. **Phase 0** (선택적): Chrome 프로세스 종료 (`--kill-chrome` 옵션 시)
2. **Phase 1**: wg-quick down으로 정상 종료 시도
3. **Phase 2**: 남은 인터페이스 강제 종료 (ip link delete)
4. **Phase 3**: 정책 라우팅 테이블 정리 (Table 101-112, 200-249)
5. **Phase 4**: /tmp/vpn_configs 설정 파일 삭제
6. **Phase 5**: 메인 라우팅 확인 및 복구

**사용 시나리오**:
- 워커 테스트 후 정리: `./cleanup_all_wg.sh`
- 브라우저까지 완전 정리: `./cleanup_all_wg.sh --kill-chrome`
- 네트워크 오류 복구: `./cleanup_all_wg.sh --kill-chrome` 후 재시작

**초기 시스템 설정** (최초 1회만):
```bash
./cleanup_and_setup_wg101.sh
```
- wg101-112 사용자 생성 및 UID 설정
- 홈 디렉토리 및 권한 설정
- 프로필 디렉토리 생성
- 이후에는 cleanup_all_wg.sh만 사용

#### 네트워크 자동 복구 시스템 (Network Watchdog)
```bash
# 스크립트 위치
/home/tech/rank_screenshot/network_watchdog.sh

# 백그라운드 실행
nohup ./network_watchdog.sh > /tmp/network_watchdog.log 2>&1 &

# 로그 확인
tail -f /tmp/network_watchdog.log
```

**자동 실행 설정 (Crontab)**:
```bash
# 매 5분마다 와치독 프로세스가 살아있는지 확인하고 없으면 재시작
*/5 * * * * pgrep -f "network_watchdog.sh" > /dev/null || nohup /home/tech/rank_screenshot/network_watchdog.sh > /tmp/network_watchdog.log 2>&1 &

# 시스템 재부팅 시 자동 시작
@reboot sleep 30 && nohup /home/tech/rank_screenshot/network_watchdog.sh > /tmp/network_watchdog.log 2>&1 &
```

**기능**:
- 60초마다 네트워크 상태 체크 (8.8.8.8, 메인 게이트웨이)
- 3회 연속 실패 시 자동 복구 시작
- 5회 이상 실패 시 긴급 복구 모드 (모든 VPN 강제 종료)
- wg101-112 인터페이스 인식 및 정리
- 메인 라우팅 자동 복구
- DNS 설정 복구
- 자동 로깅 (/tmp/network_watchdog.log)

**복구 절차**:
1. wg101-112 인터페이스 종료
2. 구버전 VPN 인터페이스 종료 (wg-worker-N, wgs218-190 등)
3. 메인 라우팅 테이블 확인 및 복구
4. DNS 설정 확인 및 복구
5. 메인 인터페이스 재시작
6. DHCP 갱신

### 문제 해결

#### "Permission denied: /home/vpn-worker-N" 오류
- **원인**: VPN 워커 홈 디렉토리 미생성 또는 권한 부족
- **해결**: `./setup_vpn_worker_homes.sh` 실행

#### "unknown user vpn-worker-N" 오류
- **원인**: 시스템 사용자 미생성
- **해결**: useradd로 사용자 추가 후 UID 설정

#### ChromeDriver 권한 오류
- **원인**: 여러 사용자가 같은 ChromeDriver 디렉토리 접근
- **해결**: browser_core_uc.py에서 사용자별 ChromeDriver 경로 사용
  ```python
  instance_driver_dir = Path(f"/tmp/chromedriver_{current_user}_instance_{self.instance_id}_v{version}")
  ```

#### ERR_NETWORK_CHANGED 오류 (2025-11-07 해결 완료)
- **원인**: 8개 워커 동시 실행 시 netlink 이벤트 폭주 + `resolvectl` DNS 설정으로 Chrome이 네트워크 변경 감지
- **해결**:
  1. ✅ **DNS 설정 제거** (가장 큰 효과): `resolvectl` 명령 모두 주석 처리 → UID 정책 라우팅으로 DNS도 자동 VPN 경로 사용
  2. ✅ **워커 시작 지연**: 3초 → 0.3~0.7초 랜덤 지연으로 netlink 이벤트 분산
  3. ✅ **안정 구간 대기**: ping 3회 + 0.5초 대기 후 Chrome 실행
  4. ✅ **rp_filter 완화**: `net.ipv4.conf.all.rp_filter=2` 설정
- **테스트 결과**: 2개 워커 100% 성공 (ERR_NETWORK_CHANGED 0건)
- **상세 문서**: [docs/ERR_NETWORK_CHANGED_ISSUE.md](docs/ERR_NETWORK_CHANGED_ISSUE.md)

#### 이전 VPN 연결 간섭
- **원인**: `/home/tech/vpn/client` (sync.sh)로 생성된 wg0~wg36 연결이 남아있음
- **해결**: `./cleanup_all_wg.sh` 실행하여 모든 WireGuard 연결 정리

#### "Nexthop has invalid gateway" 오류 (2025-11-07 해결)
- **원인**: VPN 서버마다 다른 Gateway 설정, 클라이언트가 `.1`로 하드코딩
- **해결**: VPN API 서버에 `gateway` 필드 추가 (권장)
  - API 응답: `{"gateway": "10.8.0.1", ...}`
  - Fallback: 없으면 `internal_ip` 기반 계산
  - 상세 가이드: `docs/VPN_API_GATEWAY_GUIDE.md`

### 권장 운영 방식

**개발/테스트**:
- 1-2개 워커로 테스트
- VPN 키 할당/반납 로직 확인

**소규모 운영**:
- 4-8개 워커 (안정적)
- 모니터링 쉬움

**대규모 운영**:
- 12-16개 워커 (권장 최대)
- 시스템 리소스 모니터링 필수
- 워커당 Chrome + ChromeDriver 메모리 소비 고려

**이론적 최대**:
- 20개 워커 (하드웨어 여유 있을 때)
- 50개는 불가 (시스템 사용자 부족, 리소스 과부하)

---

## 💾 Cache 보존 전략 (2025-11-07 추가)

### 개요

**트래픽 32% 절감** + **시크릿 모드 효과** 동시 달성

### 핵심 전략

- ✅ **HTTP Cache 보존**: jQuery, Bootstrap 등 정적 리소스 재사용
- ✅ **사용자 데이터 삭제**: Cookies, LocalStorage, History 제거
- ✅ **매번 로그인 안됨**: 시크릿 모드 효과 유지
- ✅ **트래픽 절감**: CSS/JS 재다운로드 불필요 (580KB/회 절약)

### 구현 위치

**파일**: `uc_lib/core/browser_core_uc.py`
**함수**: `cleanup_profile_on_exit()` (Line 826-960)

**변경 내용**:
```python
delete_dirs = [
    # === 캐시는 보존 (트래픽 절감) ===
    # "Cache" - jQuery, Bootstrap 등 재사용
    # "Code Cache" - V8 바이트코드 재사용

    # === GPU 캐시는 삭제 (핑거프린팅 위험) ===
    "GPUCache",
    "Service Worker",

    # === 사용자 식별 정보 삭제 ===
    "Local Storage",
    "Session Storage",
    "Cookies",
    "History",
    ...
]
```

### 안전성 보증

**HTTP Cache와 Cookies는 완전히 분리된 저장소**:
- Cache: `Default/Cache/` (jQuery, CSS 등 정적 파일)
- Cookies: `Default/Cookies` (로그인 세션)
- LocalStorage: `Default/Local Storage/` (사용자 데이터)

Cache를 보존해도 로그인 정보는 삭제됩니다!

### 테스트 검증

**10회 연속 테스트 결과**:
- Cache 보존: 10/10 (100%)
- Cookies 삭제: 10/10 (100%)
- 완벽한 결과: 10/10 (100%)

**스크립트**:
- `test_cleanup_simple.py` - 기본 동작 확인
- `test_10_iterations.py` - 10회 연속 테스트
- `test_no_over_deletion.py` - 과도한 삭제 확인

### 효과 (100회 실행 기준)

| 항목 | 개선 전 | 개선 후 | 절감량 |
|------|---------|---------|--------|
| jQuery | 9.5MB | 95KB | 9.4MB |
| Bootstrap | 23.5MB | 235KB | 23.3MB |
| 기타 CDN | 25MB | 250KB | 24.8MB |
| **총합** | **178MB** | **120.6MB** | **57.4MB (32%)** |

### 상세 문서

전체 기술 배경, FAQ, 테스트 결과는 다음 문서 참조:
- **[docs/CACHE_PRESERVATION_GUIDE.md](docs/CACHE_PRESERVATION_GUIDE.md)**

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

**위치**: `uc_lib/modules/product_finder.py:169-175`

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

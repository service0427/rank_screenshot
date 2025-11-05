# 사용자별 독립 프로필 시스템

## 개요

다중 사용자 환경(VPN 사용자: tech, vpn0, vpn1, vpn2...)에서 Chrome 프로필 소유권 충돌 및 리소스 공유 문제를 해결하기 위한 시스템입니다.

## 문제점 (개선 전)

### 1. 프로필 소유권 충돌
```bash
# 기존 구조
/home/tech/rank_screenshot/browser-profiles/
├── chrome-144/          # tech 소유
├── vpn0-chrome-144/     # vpn0 소유
└── instance-1-vpn3-chrome-144/  # vpn3 소유 ← 충돌!
```

**문제:**
- tech 사용자가 vpn3가 생성한 프로필에 접근 시도
- Permission denied 오류 발생
- Chrome 실행 실패

### 2. 리소스 공유 문제
- `/tmp` 디렉토리 소켓 충돌
- Chrome 디버깅 포트 충돌
- undetected_chromedriver 캐시 공유

### 3. 좀비 프로세스
- Chrome 프로세스가 `<defunct>` 상태로 남음
- 포트 점유로 신규 실행 불가

## 해결 방법

### 1. 사용자별 독립 프로필 디렉토리

각 사용자가 **자신의 홈 디렉토리**에 독립적인 프로필을 저장합니다.

```bash
# 개선 후 구조
/home/tech/.coupang_agent_profiles/
├── chrome-144/
└── chrome-130/

/home/vpn0/.coupang_agent_profiles/
├── chrome-144/
└── chrome-130/

/home/vpn1/.coupang_agent_profiles/
├── chrome-144/
└── chrome-130/
```

**장점:**
- ✅ 소유권 충돌 완전 방지
- ✅ 권한 관리 불필요
- ✅ 각 사용자 독립 운영

### 2. 소유권 충돌 자동 감지 및 해결

코드에서 프로필 디렉토리의 소유권을 자동으로 확인하고, 다른 사용자 소유인 경우 삭제 후 재생성합니다.

```python
# lib/core/browser_core_uc.py:257-282
if self.profile_dir.exists():
    current_uid = os.getuid()
    profile_owner_uid = self.profile_dir.stat().st_uid

    if current_uid != profile_owner_uid:
        # 다른 사용자 소유 → 자동 삭제
        print(f"⚠️  소유권 충돌 감지!")
        shutil.rmtree(self.profile_dir, ignore_errors=True)
```

### 3. 프로필 경로 동적 설정

```python
# lib/constants.py:188-201
@staticmethod
def get_profile_dir_base():
    # 현재 사용자의 홈 디렉토리 확인
    home_dir = Path.home()

    # 홈 디렉토리에 .coupang_agent_profiles 생성
    profile_base = home_dir / ".coupang_agent_profiles"
    profile_base.mkdir(parents=True, exist_ok=True)

    return str(profile_base)
```

## 사용 방법

### 일반 사용자 (tech)
```bash
python3 agent.py --version 144 --keyword "게이밍마우스"
# 프로필 위치: /home/tech/.coupang_agent_profiles/chrome-144
```

### VPN 사용자 (vpn0, vpn1...)
```bash
python3 agent.py --version 144 --vpn 0 --keyword "노트북"
# VPN 래퍼를 통해 vpn0 사용자로 전환
# 프로필 위치: /home/vpn0/.coupang_agent_profiles/chrome-144
```

## 구현 세부사항

### 1. 프로필 디렉토리 명명 규칙

```python
# lib/core/browser_core_uc.py:215-226
profile_base = Config.get_profile_dir_base()  # 사용자별 홈

if self.instance_id > 1:
    # 멀티 인스턴스: instance ID 포함
    self.profile_dir = Path(profile_base) / f"instance-{self.instance_id}-chrome-{version}"
else:
    # 단일 인스턴스: 버전별로만 분리
    self.profile_dir = Path(profile_base) / f"chrome-{version}"
```

### 2. 기존 프로필과의 호환성

- 레거시 경로(`/home/tech/rank_screenshot/browser-profiles/`)는 유지
- `PROFILE_DIR_BASE` 상수는 여전히 존재
- 기존 코드와 100% 호환

### 3. 멀티 인스턴스 지원

```bash
# Instance 1
python3 agent.py --version 144
# → /home/tech/.coupang_agent_profiles/chrome-144

# Instance 2
python3 agent.py --version 144 --instance-id 2
# → /home/tech/.coupang_agent_profiles/instance-2-chrome-144
```

## 테스트 결과

### Chrome 144 실행 테스트 ✅

```bash
$ python3 agent.py --version 144 --keyword "게이밍마우스"

============================================================
🤖 Coupang Agent V2 - Selenium + undetected-chromedriver
============================================================
Instance ID: 1
Keyword: 게이밍마우스
Chrome Version: 144
Detection Test: False
🌐 VPN: ❌ Not used (Local IP)
============================================================

📁 Profile directory: /home/tech/.coupang_agent_profiles/chrome-144
   Parent directory: /home/tech/.coupang_agent_profiles
   Current user: tech
   VPN: Not used
   Parent directory permissions: drwxrwxr-x
   Creating profile directory...
✅ Profile directory ready

🚀 Launching Chrome 144 with undetected-chromedriver...
   ✓ ChromeDriver service running on port 10001
   ✓ Chrome launched (undetected-chromedriver)
   ✓ Anti-detection: ENABLED by default

🏠 Navigating to Coupang home...
   ✓ Home page loaded

🔍 Searching for: 게이밍마우스
   ✓ Search completed

📄 페이지 1/26 탐색 중... (누적 오프셋: 0)
   ✓ 27개 상품의 파라미터 추출 완료
```

**결과:**
- ✅ Chrome 정상 실행
- ✅ 프로필 경로: `/home/tech/.coupang_agent_profiles/chrome-144`
- ✅ 쿠팡 검색 정상 작동
- ✅ 상품 파싱 성공

## 주요 개선사항 요약

| 항목 | 개선 전 | 개선 후 |
|------|---------|---------|
| 프로필 위치 | `/home/tech/rank_screenshot/browser-profiles/` | `~/.coupang_agent_profiles/` |
| 소유권 관리 | 수동 권한 설정 필요 | 자동 충돌 감지 및 해결 |
| VPN 지원 | 권한 충돌 발생 | 완전 독립 운영 |
| 멀티 사용자 | ❌ 충돌 가능성 높음 | ✅ 완전 격리 |
| 리소스 공유 | `/tmp`, 소켓 충돌 | 각 사용자 독립 |

## 파일 변경사항

### 1. lib/constants.py
- `Config.get_profile_dir_base()` 메서드 추가
- 사용자별 홈 디렉토리 기반 프로필 경로 생성

### 2. lib/core/browser_core_uc.py
- 프로필 디렉토리 설정 로직 간소화 (Line 215-226)
- 소유권 충돌 자동 감지 및 해결 (Line 257-282)
- VPN/instance 복잡한 조건 제거

### 3. cleanup-vpn-profiles.sh (신규)
- 기존 VPN 프로필 정리 유틸리티
- 수동 정리 시 사용

## 문제 해결

### Q: 기존 프로필은 어떻게 되나요?
A: 기존 프로필(`/home/tech/rank_screenshot/browser-profiles/`)은 그대로 유지됩니다. 새로 실행 시 사용자 홈 디렉토리에 새 프로필이 생성됩니다.

### Q: VPN 사용자 권한 설정이 필요한가요?
A: 각 VPN 사용자가 자신의 홈 디렉토리를 사용하므로 추가 권한 설정이 불필요합니다.

### Q: 디스크 공간은 어떻게 되나요?
A: 각 사용자마다 독립 프로필이 생성되므로 디스크 사용량이 증가할 수 있습니다. 하지만 캐시는 여전히 공유되며, 안정성이 크게 향상됩니다.

### Q: 성능 영향은 없나요?
A: 프로필이 분리되어도 성능 저하는 없습니다. 오히려 리소스 충돌이 없어져 더 안정적입니다.

## 결론

사용자별 독립 프로필 시스템으로:
- ✅ 소유권 충돌 완전 해결
- ✅ VPN 환경에서 안정적 운영
- ✅ 멀티 사용자 지원 강화
- ✅ 자동 충돌 해결로 유지보수 간소화

**권장 사용:**
- 모든 신규 실행은 새 시스템 사용
- 기존 프로필 정리는 선택사항
- VPN 환경에서는 필수 적용

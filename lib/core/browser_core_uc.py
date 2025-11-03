#!/usr/bin/env python3
"""
Browser Core - undetected-chromedriver 기반
Selenium + 탐지 우회 최적화
"""

import os
import time
import random
import shutil
from pathlib import Path
from typing import Optional, Dict, Tuple

try:
    import undetected_chromedriver as uc
except ImportError:
    print("❌ undetected-chromedriver가 설치되어 있지 않습니다")
    print("   pip install undetected-chromedriver")
    raise

from ..constants import Config
from ..utils.network_filter import NetworkFilter


class BrowserCoreUC:
    """undetected-chromedriver 기반 브라우저 코어 - Selenium + 탐지 우회"""

    def __init__(self, instance_id: int = 1):
        """
        Args:
            instance_id: 인스턴스 ID
        """
        self.instance_id = instance_id
        self.driver = None
        self.profile_dir = None  # launch()에서 버전별로 설정

        # Network filter (광고/트래킹 차단)
        self.network_filter = NetworkFilter()

        # Chrome Extension 경로 (네트워크 필터용)
        project_root = Path(__file__).parent.parent.parent
        self.extension_dir = project_root / "chrome-extension" / "network-filter"

        # Statistics
        self.stats = {
            "instances_created": 0,
            "instances_reused": 0,
            "instances_closed": 0,
            "active": False
        }

    def _scan_chrome_versions(self) -> dict:
        """chrome-version/ 폴더를 스캔하여 설치된 버전 목록 반환"""
        chrome_dir = Path(__file__).parent.parent.parent / "chrome-version"
        versions = {}

        if not chrome_dir.exists():
            return versions

        for version_dir in chrome_dir.iterdir():
            if version_dir.is_dir():
                chrome_bin = version_dir / "chrome-linux64" / "chrome"
                if chrome_bin.exists():
                    versions[version_dir.name] = str(chrome_bin)

        return versions

    def get_chrome_options(self, use_profile: bool = True, window_position: str = None, enable_network_filter: bool = False):
        """
        Chrome 옵션 설정

        Args:
            use_profile: 프로필 사용 여부
            window_position: 창 위치 (예: "100,200")
            enable_network_filter: 네트워크 필터 활성화 여부

        Returns:
            Chrome Options
        """
        options = uc.ChromeOptions()

        # 기본 인자
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")

        # 네트워크 필터 (Chrome Extension - declarativeNetRequest)
        if enable_network_filter:
            if self.extension_dir.exists():
                # Extension 로드
                options.add_argument(f'--load-extension={str(self.extension_dir)}')
                print(f"   🛡️  네트워크 필터 활성화 (Chrome Extension)")
            else:
                print(f"   ⚠️  네트워크 필터 Extension 없음: {self.extension_dir}")

        # 창 위치 지정 (WSL 환경에서 set_window_position 무시 문제 해결)
        if window_position:
            options.add_argument(f"--window-position={window_position}")

        # Chrome for Testing 경고 메시지 제거
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-features=ChromeForTestingWarning")

        # Chrome 131+ WSL 호환성 플래그
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-features=VizDisplayCompositor")

        # 각 instance별 고유 포트 할당 (멀티 워커 충돌 방지)
        debug_port = 9222 + self.instance_id
        options.add_argument(f"--remote-debugging-port={debug_port}")

        # Extension 사용 시 --disable-extensions 비활성화
        if not enable_network_filter:
            options.add_argument("--disable-extensions")
        options.add_argument("--disable-background-networking")

        # 한국어 설정
        options.add_argument("--lang=ko-KR")
        options.add_argument("--accept-lang=ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7")

        # 시크릿 모드 (프로필 사용 시 비활성화 - Chrome 131+ 호환성)
        # options.add_argument("--incognito")

        # 최대화 비활성화 (viewport 크기 제어를 위해)
        # options.add_argument("--start-maximized")

        # User data dir (프로필)
        if use_profile:
            options.add_argument(f"--user-data-dir={self.profile_dir}")

        # 한국어 설정 (Preferences)
        prefs = {
            "intl.accept_languages": "ko-KR,ko,en-US,en",
            "translate_whitelists": {"ko": "ko"},
            "translate": {"enabled": False}
        }
        options.add_experimental_option("prefs", prefs)

        # Performance 로그 활성화 (네트워크 필터 디버깅용)
        options.add_experimental_option("perfLoggingPrefs", {
            "enableNetwork": True,
            "enablePage": False,
        })
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

        return options

    def get_random_viewport(self) -> Dict[str, int]:
        """랜덤 viewport 크기"""
        base_width = 1920
        base_height = 1080
        ratio = random.uniform(0.80, 0.90)

        return {
            "width": int(base_width * ratio),
            "height": int(base_height * ratio)
        }

    def launch(
        self,
        version: Optional[str] = None,
        use_profile: bool = True,
        fresh_profile: bool = False,
        headless: bool = False,
        window_width: int = 1300,
        window_height: int = 1200,
        window_x: int = 10,
        window_y: int = 10,
        enable_network_filter: bool = False
    ):
        """
        Chrome 실행 (undetected-chromedriver)

        Args:
            version: Chrome 버전 (None이면 랜덤)
            use_profile: 프로필 사용 여부
            fresh_profile: True면 프로필 완전 삭제 후 재생성 (기본: False)
            headless: 헤드리스 모드 (권장: False)
            window_width: 창 너비 (기본: 1300)
            window_height: 창 높이 (기본: 1200)
            window_x: 창 X 위치 (기본: 10)
            window_y: 창 Y 위치 (기본: 10)

        Returns:
            WebDriver 객체
        """
        # Chrome 버전 선택
        if version:
            # Check if it's a channel (beta, dev, canary)
            if version.lower() in ['beta', 'dev', 'canary']:
                channel_dir = Path(Config.PROFILE_DIR_BASE).parent / "chrome-version" / version.lower()
                chrome_path = channel_dir / "chrome-linux64" / "chrome"

                if not chrome_path.exists():
                    raise ValueError(f"Chrome {version} not found. Run: ./install-chrome-channels.sh {version.lower()}")

                chrome_path = str(chrome_path)
                # Keep version as channel name for profile directory
            else:
                # Regular version number
                versions = self._scan_chrome_versions()
                chrome_path = versions.get(version)
                if not chrome_path:
                    raise ValueError(f"Chrome {version} not found")
        else:
            # Random version
            import random
            versions = self._scan_chrome_versions()
            if not versions:
                raise ValueError("Chrome이 설치되어 있지 않습니다")
            version = random.choice(list(versions.keys()))
            chrome_path = versions[version]

        # 버전별 + 사용자별 프로필 디렉토리 설정
        # 우선순위 (소유권 문제 해결):
        # 1. VPN + instance: instance + VPN 조합 (run_workers.py 멀티워커 + VPN 랜덤)
        # 2. VPN만: vpn 번호 기반 (레거시, 직접 실행)
        # 3. 일반 + 멀티 instance: instance 기반
        # 4. 일반 + 단일: 공통 프로필
        vpn_num = os.getenv('VPN_EXECUTED')
        if vpn_num and self.instance_id >= 1:
            # VPN + instance 조합: 소유권 충돌 방지를 위해 instance+VPN 모두 사용
            # run_workers.py에서 VPN 랜덤 선택 시 같은 instance가 다른 VPN으로 실행될 수 있음
            self.profile_dir = Path(Config.PROFILE_DIR_BASE) / f"instance-{self.instance_id}-vpn{vpn_num}-chrome-{version}"
        elif vpn_num:
            # VPN만 (직접 실행): vpn 번호 기반 (레거시)
            self.profile_dir = Path(Config.PROFILE_DIR_BASE) / f"vpn{vpn_num}-chrome-{version}"
        elif self.instance_id > 1:
            # 일반 + 멀티 인스턴스: instance 기반
            self.profile_dir = Path(Config.PROFILE_DIR_BASE) / f"instance-{self.instance_id}-chrome-{version}"
        else:
            # 일반 + 단일: 공통 프로필
            self.profile_dir = Path(Config.PROFILE_DIR_BASE) / f"chrome-{version}"

        # 프로필 디렉토리 처리
        # VPN 번호별로 이미 분리되어 있으므로 각 사용자가 자신의 디렉토리만 사용
        print(f"📁 Profile directory: {self.profile_dir}")
        print(f"   Parent directory: {self.profile_dir.parent}")
        print(f"   Current user: {os.getenv('USER', 'unknown')}")
        print(f"   VPN user: vpn{vpn_num}" if vpn_num else "   VPN: Not used")

        # 상위 디렉토리 존재 및 권한 확인
        parent_dir = self.profile_dir.parent
        if not parent_dir.exists():
            print(f"   ❌ Parent directory does not exist: {parent_dir}")
            raise ValueError(f"Parent directory does not exist: {parent_dir}")

        import stat
        parent_stat = parent_dir.stat()
        parent_mode = stat.filemode(parent_stat.st_mode)
        print(f"   Parent directory permissions: {parent_mode}")

        print(f"   Creating profile directory...")

        try:
            if fresh_profile and self.profile_dir.exists():
                # 옵션 1: 프로필 완전 삭제 후 재생성
                import shutil
                print(f"🗑️  Deleting old profile: {self.profile_dir}")
                shutil.rmtree(self.profile_dir, ignore_errors=True)
                self.profile_dir.mkdir(parents=True, exist_ok=True)
                print(f"✅ Fresh profile created")
            else:
                # 옵션 2 (기본): 프로필 유지
                self.profile_dir.mkdir(parents=True, exist_ok=True)
                print(f"✅ Profile directory ready")
        except Exception as e:
            print(f"   ❌ Failed to create profile directory: {e}")
            print(f"   Directory: {self.profile_dir}")
            print(f"   Parent: {parent_dir}")
            print(f"   Parent exists: {parent_dir.exists()}")
            print(f"   Parent permissions: {oct(parent_stat.st_mode)[-3:]}")
            raise

        print(f"🚀 Launching Chrome {version} with undetected-chromedriver...")
        print(f"   Path: {chrome_path}")
        print(f"   Instance ID: {self.instance_id}")
        print(f"   Debug Port: {9222 + self.instance_id}")
        if use_profile:
            print(f"   Profile: {self.profile_dir}")
            if fresh_profile:
                print(f"   Mode: Fresh profile (완전 삭제 후 재생성)")
            else:
                print(f"   Mode: Reuse profile (쿠키/세션/스토리지만 삭제 예정)")

        # Chrome 옵션
        # 프로필 사용 시: 저장된 창 위치 자동 복원 (window_position 인자 없음)
        # 프로필 미사용 시: 지정된 위치로 창 열기
        if use_profile:
            options = self.get_chrome_options(use_profile=True, window_position=None, enable_network_filter=enable_network_filter)
        else:
            window_position_arg = f"{window_x},{window_y}"
            options = self.get_chrome_options(use_profile=False, window_position=window_position_arg, enable_network_filter=enable_network_filter)

        # Major version 추출 (channels의 경우 MAJOR_VERSION 파일에서 읽기)
        if version.lower() in ['beta', 'dev', 'canary']:
            channel_dir = Path(Config.PROFILE_DIR_BASE).parent / "chrome-version" / version.lower()
            major_version_file = channel_dir / "MAJOR_VERSION"
            if major_version_file.exists():
                version_main = int(major_version_file.read_text().strip())
            else:
                # Fallback: VERSION 파일에서 메이저 버전 추출
                version_file = channel_dir / "VERSION"
                full_version = version_file.read_text().strip()
                version_main = int(full_version.split('.')[0])
        else:
            version_main = int(version)

        # ChromeDriver 서비스 포트 설정 (instance별 고유 포트)
        driver_port = 10000 + self.instance_id

        # undetected-chromedriver 시작 (자동 ChromeDriver 다운로드)
        print(f"   Starting undetected-chromedriver (version_main={version_main})...")
        print(f"   Driver port: {driver_port}")
        print(f"   This may take a while if downloading ChromeDriver...")

        self.driver = uc.Chrome(
            browser_executable_path=chrome_path,
            options=options,
            headless=headless,
            use_subprocess=True,
            version_main=version_main,  # Major version
            driver_executable_path=None,  # 자동 다운로드
            port=driver_port  # ChromeDriver 서비스 포트
        )

        print(f"   ✓ ChromeDriver service running on port {driver_port}")

        # Viewport 설정 (파라미터 사용) - 내부 콘텐츠 영역
        viewport_width = window_width
        viewport_height = window_height

        # 브라우저 창 크기 (툴바/스크롤바 등을 고려)
        # 세로: 8% 여유 (툴바용)
        actual_window_width = window_width
        actual_window_height = int(window_height * 1.08)

        # 창 크기 설정
        self.driver.set_window_size(actual_window_width, actual_window_height)
        time.sleep(0.3)  # 창 크기 적용 대기

        # 창 위치: 프로필 사용 시 자동 복원, 미사용 시 --window-position 인자로 설정됨

        # 그 다음 viewport 설정 (내부 콘텐츠 영역)
        try:
            self.driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
                'width': viewport_width,
                'height': viewport_height,
                'deviceScaleFactor': 1,
                'mobile': False
            })
        except Exception:
            # CDP 실패 시 경고만 출력 (이미 창 크기는 설정됨)
            print(f"   ⚠️  CDP viewport override failed, using window size instead")

        # 네트워크 모니터링 활성화
        try:
            self.driver.execute_cdp_cmd('Network.enable', {})
            print(f"   ✓ 네트워크 모니터링 활성화\n")
        except Exception as e:
            print(f"   ⚠️  네트워크 모니터링 활성화 실패: {e}")

        # Fetch 도메인 활성화 (Request Interception용)
        try:
            self.driver.execute_cdp_cmd('Fetch.enable', {
                'patterns': []  # 빈 패턴으로 시작 (필터 활성화 시 추가)
            })
            print(f"   ✓ Fetch 도메인 활성화 (Request Interception 준비)\n")
        except Exception as e:
            print(f"   ⚠️  Fetch 활성화 실패: {e}")

        self.stats["active"] = True
        self.stats["instances_created"] += 1

        print(f"   ✓ Chrome launched (undetected-chromedriver)")
        print(f"   ✓ Anti-detection: ENABLED by default")

        return self.driver

    def test_detection(self) -> Dict:
        """
        자동화 탐지 테스트

        Returns:
            탐지 결과
        """
        if not self.driver:
            return {"error": "No driver available"}

        print("🔍 Testing automation detection...")

        result = self.driver.execute_script("""
        return {
            webdriver: navigator.webdriver,
            chrome: !!window.chrome,
            permissions: !!navigator.permissions,
            plugins: navigator.plugins.length,
            languages: navigator.languages,
            platform: navigator.platform,
            userAgent: navigator.userAgent.substring(0, 100)
        };
        """)

        print(f"   webdriver: {result.get('webdriver')}")
        print(f"   chrome: {result.get('chrome')}")
        print(f"   plugins: {result.get('plugins')}")
        print(f"   platform: {result.get('platform')}")
        print(f"   languages: {result.get('languages')}")

        return result

    def clear_cookies(self):
        """쿠키 삭제"""
        if not self.driver:
            return

        print("🧹 Clearing cookies...")

        try:
            self.driver.delete_all_cookies()
            print("   ✓ Cookies cleared")
        except Exception as e:
            print(f"   ⚠️  Cookie clear failed: {e}")

    def clear_session_storage(self):
        """세션 스토리지 삭제"""
        if not self.driver:
            return

        try:
            self.driver.execute_script("sessionStorage.clear();")
            print("   ✓ Session storage cleared")
        except Exception as e:
            print(f"   ⚠️  Session storage clear failed: {e}")

    def clear_local_storage(self):
        """로컬 스토리지 삭제"""
        if not self.driver:
            return

        try:
            self.driver.execute_script("localStorage.clear();")
            print("   ✓ Local storage cleared")
        except Exception as e:
            print(f"   ⚠️  Local storage clear failed: {e}")

    def clear_all_storage(self):
        """쿠키, 세션 스토리지, 로컬 스토리지 모두 삭제 (캐시는 유지)"""
        if not self.driver:
            return

        print("🧹 Clearing cookies, session & local storage (cache preserved)...")

        try:
            # 현재 URL 확인
            current_url = self.driver.current_url

            # 쿠팡 도메인이 아니면 쿠팡으로 이동
            if "coupang.com" not in current_url:
                print("   ℹ️  쿠팡 도메인으로 이동 중...")
                self.driver.get("https://www.coupang.com")
                import time
                time.sleep(1)

            # 쿠키 삭제
            self.driver.delete_all_cookies()

            # JavaScript로 스토리지 삭제 (여러 번 시도)
            for attempt in range(3):
                try:
                    # sessionStorage와 localStorage 삭제
                    self.driver.execute_script("""
                        try {
                            sessionStorage.clear();
                            localStorage.clear();
                            console.log('Storage cleared');
                        } catch (e) {
                            console.error('Storage clear failed:', e);
                        }
                    """)

                    # 삭제 확인
                    storage_check = self.driver.execute_script("""
                        return {
                            sessionLength: sessionStorage.length,
                            localLength: localStorage.length
                        };
                    """)

                    if storage_check['sessionLength'] == 0 and storage_check['localLength'] == 0:
                        print("   ✓ All storage cleared (cache preserved)")
                        return

                except Exception as e:
                    if attempt == 2:
                        print(f"   ⚠️  Storage clear failed after {attempt + 1} attempts: {e}")

            print("   ⚠️  Storage may not be fully cleared")

        except Exception as e:
            print(f"   ⚠️  Storage clear failed: {e}")

    def get_cookies(self) -> list:
        """현재 쿠키 가져오기"""
        if not self.driver:
            return []

        try:
            return self.driver.get_cookies()
        except Exception as e:
            print(f"   ⚠️  Get cookies failed: {e}")
            return []

    def set_cookies(self, cookies: list):
        """쿠키 설정"""
        if not self.driver:
            return

        try:
            for cookie in cookies:
                self.driver.add_cookie(cookie)
            print(f"   ✓ Set {len(cookies)} cookies")
        except Exception as e:
            print(f"   ⚠️  Set cookies failed: {e}")

    def enable_network_filter(self):
        """
        네트워크 필터 활성화 (호환성 유지)

        주의: 실제 필터는 Chrome 시작 시 --host-rules 플래그로 적용됩니다.
        이 메서드는 호환성을 위해 남겨두었으며, 아무 동작도 하지 않습니다.
        """
        pass  # Chrome 시작 시 이미 --host-rules로 적용됨

    def _monitor_network_requests(self, duration: int = 5):
        """네트워크 요청 모니터링 (디버깅용)"""
        import time
        import json
        from urllib.parse import urlparse

        # requestId → URL 매핑
        request_map = {}
        blocked_urls = []
        allowed_external_urls = []

        print(f"      (다음 {duration}초간 네트워크 요청 기록)\n")

        start_time = time.time()

        while time.time() - start_time < duration:
            try:
                # 개발자 도구 로그 가져오기
                logs = self.driver.get_log('performance')

                for entry in logs:
                    log = json.loads(entry['message'])
                    message = log.get('message', {})
                    method = message.get('method', '')

                    # 요청 시작 시 URL 저장
                    if method == 'Network.requestWillBeSent':
                        params = message.get('params', {})
                        request_id = params.get('requestId')
                        request = params.get('request', {})
                        url = request.get('url', '')
                        resource_type = params.get('type', 'Other')

                        # 내부 리소스 제외 (chrome://, data:, chrome-extension:)
                        if url and not url.startswith('data:') and not url.startswith('chrome-extension:') and not url.startswith('chrome://'):
                            request_map[request_id] = {
                                'url': url,
                                'type': resource_type
                            }

                            # 외부 도메인 (쿠팡 아닌 것)
                            parsed = urlparse(url)
                            if parsed.netloc and 'coupang' not in parsed.netloc.lower():
                                if len(allowed_external_urls) < 30:
                                    allowed_external_urls.append({
                                        'url': url,
                                        'domain': parsed.netloc,
                                        'type': resource_type
                                    })

                    # 차단된 요청
                    elif method == 'Network.loadingFailed':
                        params = message.get('params', {})
                        request_id = params.get('requestId')
                        error = params.get('errorText', '')

                        if 'BLOCKED_BY_CLIENT' in error or 'ERR_BLOCKED_BY_CLIENT' in error:
                            if request_id in request_map:
                                blocked_urls.append(request_map[request_id])
                            else:
                                blocked_urls.append({'url': f'Unknown (ID: {request_id})', 'type': 'Unknown'})

                time.sleep(0.1)

            except Exception as e:
                # 로그 파싱 실패는 무시
                pass

        # 결과 출력
        print(f"\n   📊 네트워크 모니터링 결과 ({duration}초):")
        print(f"      - 🚫 차단된 요청: {len(blocked_urls)}개")
        print(f"      - ✅ 허용된 외부 요청: {len(allowed_external_urls)}개")

        if blocked_urls:
            print(f"\n   🚫 차단된 요청 (처음 10개):")
            for i, item in enumerate(blocked_urls[:10], 1):
                url = item['url']
                url_short = url[:80] + '...' if len(url) > 80 else url
                print(f"      {i:2d}. [{item['type']}] {url_short}")
            if len(blocked_urls) > 10:
                print(f"      ... (총 {len(blocked_urls)}개)")

        if allowed_external_urls:
            print(f"\n   ⚠️  허용된 외부 요청 (처음 10개):")
            for i, item in enumerate(allowed_external_urls[:10], 1):
                url = item['url']
                url_short = url[:80] + '...' if len(url) > 80 else url
                print(f"      {i:2d}. [{item['type']}] {item['domain']}")
                print(f"          {url_short}")
            if len(allowed_external_urls) > 10:
                print(f"      ... (총 {len(allowed_external_urls)}개)")

        print()

    def disable_network_filter(self):
        """
        네트워크 필터 비활성화 (호환성 유지)

        주의: --host-rules로 설정된 필터는 런타임에 비활성화할 수 없습니다.
        """
        pass  # --host-rules는 런타임에 변경 불가

    def close_browser(self):
        """브라우저 종료"""
        print(f"👋 Closing browser...")

        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

        self.stats["active"] = False
        self.stats["instances_closed"] += 1

        print(f"   ✓ Browser closed")

    def shutdown(self):
        """완전 종료"""
        self.close_browser()

    def is_browser_alive(self) -> bool:
        """브라우저 활성 상태 확인"""
        if not self.driver:
            return False

        try:
            # 현재 URL을 가져와서 브라우저가 살아있는지 확인
            _ = self.driver.current_url
            return True
        except:
            return False

    def clean_profile(self):
        """프로필 디렉토리 정리"""
        if self.profile_dir.exists():
            print(f"🗑️  Cleaning profile...")
            shutil.rmtree(self.profile_dir)
            self.profile_dir.mkdir(parents=True, exist_ok=True)
            print(f"   ✓ Profile cleaned")

    def take_screenshot(
        self,
        keyword: str = "",
        version: str = "",
        full_page: bool = False
    ) -> Optional[str]:
        """
        현재 페이지 스크린샷 캡처 (레거시 호환성 유지)

        Args:
            keyword: 검색 키워드 (파일명에 포함)
            version: Chrome 버전 (디렉토리 구분용)
            full_page: 전체 페이지 캡처 여부 (기본: False, viewport만)

        Returns:
            저장된 파일 경로 (실패 시 None)

        Note:
            이 메서드는 호환성을 위해 유지되며, ScreenshotCapturer 모듈 사용을 권장합니다.
        """
        from lib.modules.screenshot_capturer import ScreenshotCapturer

        base_dir = Path(__file__).parent.parent.parent / "screenshots"
        capturer = ScreenshotCapturer(self.driver, base_dir=str(base_dir))
        return capturer.capture(keyword=keyword, version=version, full_page=full_page)

    def print_stats(self):
        """통계 출력"""
        print("\n" + "=" * 60)
        print("📊 Browser Core Statistics (undetected-chromedriver)")
        print("=" * 60)
        print(f"Instance ID: {self.instance_id}")
        print(f"Active: {self.stats['active']}")
        print(f"Instances Created: {self.stats['instances_created']}")
        print(f"Instances Reused: {self.stats['instances_reused']}")
        print(f"Instances Closed: {self.stats['instances_closed']}")
        print("=" * 60 + "\n")


# ===================================================================
# Selenium WebDriver API (표준 Selenium 인터페이스)
# ===================================================================

class UCDriverAdapter:
    """
    undetected-chromedriver를 표준 Selenium WebDriver처럼 사용
    기존 Selenium 코드와 호환성 제공
    """

    def __init__(self, driver):
        self._driver = driver

    def get(self, url: str):
        """페이지 이동"""
        self._driver.get(url)

    def find_element(self, by, value):
        """요소 찾기"""
        return self._driver.find_element(by, value)

    def find_elements(self, by, value):
        """요소들 찾기"""
        return self._driver.find_elements(by, value)

    def execute_script(self, script, *args):
        """JavaScript 실행"""
        return self._driver.execute_script(script, *args)

    @property
    def current_url(self):
        """현재 URL"""
        return self._driver.current_url

    @property
    def page_source(self):
        """페이지 소스"""
        return self._driver.page_source

    def delete_all_cookies(self):
        """모든 쿠키 삭제"""
        self._driver.delete_all_cookies()

    def get_cookies(self):
        """쿠키 가져오기"""
        return self._driver.get_cookies()

    def add_cookie(self, cookie):
        """쿠키 추가"""
        self._driver.add_cookie(cookie)

    def quit(self):
        """드라이버 종료"""
        self._driver.quit()

    def close(self):
        """현재 창 닫기"""
        self._driver.close()

    def __getattr__(self, name):
        """기타 속성은 원본 driver에 위임"""
        return getattr(self._driver, name)

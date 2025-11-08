#!/usr/bin/env python3
"""
Coupang Agent V2 - Selenium + undetected-chromedriver
Chrome 전용, Selenium 기반 탐지 우회
"""

import os
import sys
import time
import shutil
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# UC 시스템 모듈 (lib/ → uc_lib/ 심볼릭 링크)
from uc_lib.core.browser_core_uc import BrowserCoreUC
from uc_lib.modules.coupang_handler_selenium import CoupangHandlerSelenium
from uc_lib.modules.product_finder import ProductFinder
from uc_lib.modules.work_api_client import WorkAPIClient
from uc_lib.workflows.search_workflow import SearchWorkflow

# 공통 모듈 (common/)
from common.vpn_api_client import VPNAPIClient
from common.utils.network_validator import verify_vpn_connection, print_verification_result
from common.fingerprint_spoofer import FingerprintSpoofer

# UC 전용 모듈
from uc_lib.modules.screenshot_processor import ScreenshotProcessor

# 마지막 사용 버전 저장 파일
LAST_VERSION_FILE = Path(__file__).parent / ".last_version"

# 기능 활성화 플래그
ENABLE_RANK_MANIPULATION = False
ENABLE_SCREENSHOT_UPLOAD = True
UPLOAD_SERVER_URL = "http://220.121.120.83/toprekr/upload.php"

# API 통합 설정
# 작업 할당/결과 제출 API 사용 여부
# URL은 common.constants.Config에서 중앙 관리
ENABLE_WORK_API = False

# 기본 상품 파라미터
TARGET_PRODUCT = {
    "keyword": "노트북",
    "product_id": "9128826497",
    "item_id": "29152685095",
    "vendor_item_id": "92854175064"
}


def save_last_version(version: str):
    """마지막 사용 버전 저장"""
    try:
        with open(LAST_VERSION_FILE, 'w') as f:
            f.write(version)
    except Exception:
        pass


def load_last_version() -> str:
    """마지막 사용 버전 로드"""
    try:
        if LAST_VERSION_FILE.exists():
            with open(LAST_VERSION_FILE, 'r') as f:
                return f.read().strip()
    except Exception:
        pass
    return None


def wait_for_user_or_close(driver, core, close_after: bool = False):
    """사용자 입력 또는 브라우저 종료 대기"""
    if close_after:
        print(f"\n⏱️  Closing browser in 3 seconds... (close_after={close_after})\n")
        time.sleep(3)
        print("   ✅ 3초 대기 완료, 브라우저 종료 진행 중...\n")
    else:
        print("\n💡 Browser is running. Press Enter or Ctrl+C to close, or close the window manually.\n")
        try:
            import threading
            import select

            browser_closed = threading.Event()

            def check_browser():
                while not browser_closed.is_set():
                    time.sleep(1)
                    if not core.is_browser_alive():
                        browser_closed.set()
                        break

            check_thread = threading.Thread(target=check_browser, daemon=True)
            check_thread.start()

            while not browser_closed.is_set():
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    sys.stdin.readline()
                    print("\n⚠️  Enter detected. Shutting down...\n")
                    break

            if browser_closed.is_set():
                print("\n⚠️  Browser was closed. Cleaning up...\n")

        except KeyboardInterrupt:
            print("\n⚠️  Ctrl+C detected. Shutting down...\n")


def run_agent_selenium_uc(
    instance_id: int = 1,
    keyword: str = "노트북",
    product_id: str = None,
    item_id: str = None,
    vendor_item_id: str = None,
    version: str = None,
    test_detection: bool = False,
    close_after: bool = False,
    fresh_profile: bool = False,
    screenshot_id: int = None,
    api_client: WorkAPIClient = None,
    check_ip: bool = False,
    window_width: int = 1300,
    window_height: int = 1200,
    window_x: int = 10,
    window_y: int = 10,
    enable_rank_adjust: bool = False,  # Adjust 모드 (미래 개발용)
    adjust_mode: str = None,  # "adjust" 또는 "adjust2" (미래 개발용)
    min_rank: int = None,  # Adjust 모드용 최소 순위 (미래 개발용)
    enable_main_filter: bool = False,
    vpn_pool_worker: int = None,  # VPN 키 풀 워커 ID
    enable_fingerprint_spoof: bool = False,  # 핑거프린트 스푸핑 활성화
    fingerprint_preset: str = 'full'  # 스푸핑 프리셋 (full 권장)
):
    """
    Selenium + undetected-chromedriver 에이전트 실행 (리팩토링 버전)

    Args:
        instance_id: 인스턴스 ID
        keyword: 검색 키워드
        product_id: 상품 ID
        item_id: 아이템 ID
        vendor_item_id: 판매자 아이템 ID
        version: Chrome 버전
        test_detection: 탐지 테스트 모드
        close_after: 검사 후 3초 뒤 자동 종료
        screenshot_id: 작업 ID (API 모드)
        api_client: API 클라이언트
        check_ip: IP 확인 여부
        window_width: 창 너비 (기본: 1300)
        window_height: 창 높이 (기본: 1200)
        window_x: 창 X 위치 (기본: 10)
        window_y: 창 Y 위치 (기본: 10)
    """
    # === 헤더 출력 ===
    print("\n" + "=" * 60)
    print("🤖 Coupang Agent V2 - Selenium + undetected-chromedriver")
    print("=" * 60)
    print(f"Instance ID: {instance_id}")
    print(f"Keyword: {keyword}")
    print(f"Chrome Version: {version if version else 'Random'}")
    print(f"Detection Test: {test_detection}")

    vpn_num = os.environ.get('VPN_EXECUTED')

    # Worker ID 생성 (네트워크 에러 로깅용)
    if vpn_pool_worker is not None:
        worker_id = f"Worker-{vpn_pool_worker}"
    elif vpn_num is not None:
        worker_id = f"VPN-{vpn_num}"
    else:
        worker_id = f"Local-{instance_id}"

    # VPN 인터페이스 정보 가져오기 (환경 변수에서)
    vpn_interface = os.environ.get('VPN_INTERFACE', None)

    if vpn_num is not None:
        print(f"🌐 VPN: ✅ wg{vpn_num}/vpn{vpn_num} (Enabled)")
    elif vpn_pool_worker is not None:
        print(f"🌐 VPN: ✅ VPN Pool Worker {vpn_pool_worker} (vpn-worker-{vpn_pool_worker})")
    else:
        print(f"🌐 Network: ❌ Local IP (Direct)")
    print("=" * 60 + "\n")

    core = None
    try:
        # === 1. 브라우저 초기화 ===
        core = BrowserCoreUC(instance_id=instance_id, worker_id=worker_id, vpn_interface=vpn_interface)

        driver = core.launch(
            version=version,
            use_profile=True,
            fresh_profile=fresh_profile,
            headless=False,
            window_width=window_width,
            window_height=window_height,
            enable_network_filter=enable_main_filter,
            window_x=window_x,
            window_y=window_y
        )
        if not driver:
            print("❌ Failed to launch browser")
            return

        # 버전 저장
        if version:
            save_last_version(version)

        # === 1-1. 핑거프린트 스푸핑 (옵션) ===
        if enable_fingerprint_spoof:
            print("\n" + "=" * 60)
            print(f"🎭 브라우저 핑거프린트 스푸핑 활성화 (Preset: {fingerprint_preset})")
            print("=" * 60)

            try:
                spoofer = FingerprintSpoofer(preset=fingerprint_preset)
                spoof_script, spoof_config = spoofer.generate_spoof_script()

                # CDP로 스크립트 주입 (페이지 로드 전)
                driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': spoof_script
                })

                print("   ✅ 핑거프린트 스푸핑 스크립트 주입 완료")
                spoofer.print_config(spoof_config)
                print("=" * 60 + "\n")

            except Exception as e:
                print(f"   ⚠️  핑거프린트 스푸핑 실패: {e}")
                print("   계속 진행합니다...\n")

        # === 2. IP 확인 (옵션) ===
        if check_ip:
            print("\n" + "=" * 60)
            print("🌐 IP 주소 확인")
            print("=" * 60)
            try:
                driver.get("https://api.ipify.org?format=text")
                time.sleep(1)
                ip_address = driver.find_element("tag name", "body").text.strip()

                vpn_num = os.environ.get('VPN_EXECUTED')
                if vpn_num is not None:
                    print(f"   📍 wg{vpn_num}/vpn{vpn_num} IP: {ip_address}")
                else:
                    print(f"   📍 Local IP: {ip_address}")

                if not close_after:
                    print("\n⏸️  Press Enter to continue...")
                    input()
                else:
                    print("   ✅ IP 확인 완료 (자동 진행)")
                    time.sleep(1)
            except Exception as e:
                print(f"   ⚠️  IP 확인 실패: {e}")

        # === 3. 탐지 테스트 (옵션) ===
        if test_detection:
            print("\n" + "=" * 60)
            print("🧪 Detection Test Mode")
            print("=" * 60)
            if not close_after:
                print("\n⏸️  Press Enter to continue after manual inspection...")
                input()
            else:
                print("   ✅ 탐지 테스트 모드 (자동 진행)")
                time.sleep(3)

        # === 4. 네트워크 모드 결정 ===
        network_mode = "Local"
        # VPN 사용자인지 확인
        # - vpn0, vpn1, ... (구버전)
        # - vpn-worker-N (VPN 키 풀 - 구버전)
        # - wg101-112 (VPN 키 풀 - 신버전, wg101-112 시스템)
        current_user = os.getenv('USER', '')
        is_vpn_pool_worker = current_user.startswith('vpn-worker-')
        is_wg_user = current_user.startswith('wg') and len(current_user) >= 5 and current_user[2:].isdigit()

        if current_user.startswith('vpn') and not is_vpn_pool_worker:
            vpn_num = current_user[3:]  # "vpn0" -> "0"
            network_mode = f"VPN {vpn_num}"
        elif is_vpn_pool_worker:
            # VPN 키 풀 워커 (WireGuard 외부에서 관리됨)
            worker_id = current_user.split('-')[-1]  # "vpn-worker-1" -> "1"
            network_mode = f"VPN Pool (Worker {worker_id})"
        elif is_wg_user:
            # wg101-112 시스템 (VPN 키 풀 - 신버전)
            worker_id = int(current_user[2:]) - 100  # "wg101" -> 1, "wg102" -> 2
            network_mode = f"VPN Pool (Worker {worker_id})"

        # === 4-1. VPN 연결 검증 (패킷 방식) ===
        # ⚠️ VPN 키 풀 워커는 검증 건너뛰기 (외부에서 WireGuard 관리)
        # wg101-112 시스템도 VPN 키 풀이므로 검증 건너뛰기
        if network_mode.startswith("VPN") and network_mode != "Local" and not is_vpn_pool_worker and not is_wg_user:
            print("\n" + "=" * 60)
            print("🔐 네트워크 연결 검증 (패킷 방식)")
            print("=" * 60)

            verification_passed = False

            # VPN 모드 검증
            try:
                vpn_num_str = network_mode.split(' ')[1]  # "VPN 0" -> "0"
                vpn_num = int(vpn_num_str)

                vpn_client = VPNAPIClient()
                result = verify_vpn_connection(
                    vpn_number=vpn_num,
                    vpn_client=vpn_client,
                    timeout=10
                )
                verification_passed = print_verification_result(result, mode=f"VPN {vpn_num}")

            except Exception as e:
                print(f"   ❌ VPN 검증 중 오류: {e}")
                verification_passed = False

            # 검증 실패 시 즉시 종료
            if not verification_passed:
                print("\n" + "=" * 60)
                print("🚨 네트워크 연결 검증 실패!")
                print("=" * 60)
                print("   VPN이 올바르게 작동하지 않습니다.")
                print("   쿠팡 접속을 중단하고 종료합니다.")
                print("=" * 60 + "\n")

                # 브라우저 종료
                if core and hasattr(core, 'close_browser'):
                    core.close_browser()

                return  # Agent 종료

            print("   ✅ 네트워크 연결 검증 통과! 쿠팡 접속을 시작합니다.\n")

        # === 5. 모듈 초기화 ===
        handler = CoupangHandlerSelenium(
            driver,
            network_mode=network_mode,
            worker_id=worker_id,
            vpn_interface=vpn_interface
        )
        finder = ProductFinder(driver)
        screenshot_processor = ScreenshotProcessor(
            driver=driver,
            base_dir=str(Path(__file__).parent / "screenshots"),
            upload_url=UPLOAD_SERVER_URL if ENABLE_SCREENSHOT_UPLOAD else None,
            enable_upload=ENABLE_SCREENSHOT_UPLOAD
        )

        # === 6. 워크플로우 실행 ===
        workflow = SearchWorkflow(
            driver=driver,
            handler=handler,
            finder=finder,
            screenshot_processor=screenshot_processor,
            core=core,  # 네트워크 필터 제어를 위해 core 객체 전달
            enable_main_filter=enable_main_filter  # 메인 페이지 필터 활성화 여부
        )

        result = workflow.execute(
            keyword=keyword,
            product_id=product_id,
            item_id=item_id,
            vendor_item_id=vendor_item_id,
            version=version if version else "unknown",
            min_rank=min_rank,  # Adjust 모드 개발용 인터페이스 (현재 미사용)
            screenshot_id=screenshot_id  # 작업 ID 전달 (업로드 시 screenshot_id로 사용)
        )

        # === 6. 결과 출력 ===
        if result.success:
            print("\n" + "=" * 60)
            print("✅ 워크플로우 완료")
            print("=" * 60)
            print(f"매칭 조건: {result.match_condition}")
            print(f"스크린샷: {result.before_screenshot}")
            if result.before_screenshot_url:
                print(f"파일 경로: {result.before_screenshot_url}")

            # 탐색 정보 출력
            if result.pages_searched > 0:
                print(f"\n📊 탐색 정보:")
                print(f"   발견 위치: 페이지 {result.found_on_page} (전체 {result.matched_product.get('rank', '?')}등)")
                print(f"   탐색 범위: 1~{result.pages_searched}페이지")
                print(f"   확인 상품 수: {result.total_products_checked}개")
        else:
            print("\n" + "=" * 60)
            print("⚠️  워크플로우 실패")
            print("=" * 60)
            print(f"오류: {result.error_message}")

            # 탐색 정보 출력 (실패 시)
            if result.pages_searched > 0:
                print(f"\n📊 탐색 정보:")
                print(f"   탐색 페이지: 1~{result.pages_searched}페이지")
                print(f"   확인 상품 수: {result.total_products_checked}개")

                # 페이지별 상세 정보 (최대 5개)
                if result.page_history:
                    print(f"\n📋 페이지별 상세:")
                    for page_info in result.page_history[:5]:
                        print(f"   페이지 {page_info['page']}: "
                              f"{page_info['rank_range'][0]}~{page_info['rank_range'][1]}등 "
                              f"({page_info['product_count']}개 상품)")
                    if len(result.page_history) > 5:
                        print(f"   ... (총 {len(result.page_history)}개 페이지)")

        # === 7. API 결과 제출 (활성화된 경우) ===
        if api_client and screenshot_id:
            # 차단된 경우 작업 결과 제출 건너뛰기
            if result.error_message and "차단" in result.error_message:
                print("\n" + "=" * 60)
                print("⚠️  차단 감지 - 작업 결과 제출 건너뛰기")
                print("=" * 60)
                print(f"   차단 사유: {result.error_message}")
                print(f"   작업 ID {screenshot_id}는 제출하지 않습니다\n")
                # 차단 감지 시 자동 종료 플래그 설정
                close_after = True
            else:
                print("\n" + "=" * 60)
                print("📤 작업 결과 제출")
                print("=" * 60 + "\n")

                # 성공 시: 스크린샷 URL 선택, 실패 시: "PRODUCT_NOT_FOUND"
                if result.success:
                    # Adjust 모드에서 after 스크린샷이 있으면 after 사용, 아니면 before 사용
                    if result.after_screenshot_url:
                        screenshot_url = result.after_screenshot_url
                        print(f"📤 스크린샷 URL: {screenshot_url}")
                        print(f"   타입: 순위 조작 후 (after)")
                    else:
                        screenshot_url = result.before_screenshot_url
                        print(f"📤 스크린샷 URL: {screenshot_url}")
                        print(f"   타입: 순위 조작 없음 (before)")
                else:
                    screenshot_url = "PRODUCT_NOT_FOUND"

                # 파일명 추출 (URL에서 파일명만)
                filename = Path(screenshot_url).name if screenshot_url and screenshot_url != "PRODUCT_NOT_FOUND" else None

                # 순위 정보 추출
                rank = None
                if result.success and hasattr(result, 'matched_product') and result.matched_product:
                    rank = result.matched_product.get('rank')

                # 매칭 조건을 boolean 필드로 변환
                api_product_id = None
                api_item_id = None
                api_vendor_item_id = None
                match_product_id = False
                match_item_id = False
                match_vendor_item_id = False

                if result.success and hasattr(result, 'match_condition') and result.match_condition:
                    match_cond = result.match_condition

                    if "완전 일치" in match_cond:
                        # 모두 일치
                        api_product_id = product_id
                        api_item_id = item_id
                        api_vendor_item_id = vendor_item_id
                        match_product_id = True
                        match_item_id = True
                        match_vendor_item_id = True
                    elif "product_id + vendor_item_id 일치" in match_cond:
                        # product_id + vendor_item_id만 일치
                        api_product_id = product_id
                        api_vendor_item_id = vendor_item_id
                        match_product_id = True
                        match_vendor_item_id = True
                    elif "product_id 일치" in match_cond:
                        # product_id만 일치
                        api_product_id = product_id
                        match_product_id = True
                    elif "vendor_item_id 일치" in match_cond:
                        # vendor_item_id만 일치
                        api_vendor_item_id = vendor_item_id
                        match_vendor_item_id = True
                    elif "item_id 일치" in match_cond:
                        # item_id만 일치
                        api_item_id = item_id
                        match_item_id = True

                submit_success = api_client.submit_result(
                    screenshot_id=screenshot_id,
                    screenshot_url=screenshot_url,
                    keyword=keyword,
                    rank=rank,
                    product_id=api_product_id,
                    item_id=api_item_id,
                    vendor_item_id=api_vendor_item_id,
                    filename=filename,
                    match_product_id=match_product_id,
                    match_item_id=match_item_id,
                    match_vendor_item_id=match_vendor_item_id
                )

                if submit_success:
                    print(f"✅ 작업 ID {screenshot_id} 결과 제출 완료")
                    if not result.success:
                        print(f"   📋 상태: 상품 미발견 (PRODUCT_NOT_FOUND)")
                else:
                    print(f"⚠️  작업 ID {screenshot_id} 결과 제출 실패")

        # === 8. 대기 및 종료 ===
        wait_for_user_or_close(driver, core, close_after)

        # 성공 여부 반환
        return result.success

    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user\n")
        return False

    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 브라우저 종료
        if core:
            try:
                core.close_browser()
                print("✅ Browser closed successfully\n")
            except Exception as e:
                print(f"⚠️  Error closing browser: {e}\n")


def run_work_api_mode(
    instance_id: int = 1,
    version: str = None,
    close_after: bool = True,
    fresh_profile: bool = False,
    check_ip: bool = False,
    window_width: int = 1300,
    window_height: int = 1200,
    window_x: int = 10,
    window_y: int = 10,
    enable_rank_adjust: bool = False,
    adjust_mode: str = None,
    enable_main_filter: bool = False,
    specified_screenshot_id: int = None,
    vpn_pool_worker: int = None,  # VPN 키 풀 워커 ID
    enable_fingerprint_spoof: bool = False,  # 핑거프린트 스푸핑
    fingerprint_preset: str = 'full'  # 스푸핑 프리셋 (full 권장)
):
    """
    작업 API 모드 실행
    - 작업 할당 API로부터 작업을 받아옴
    - 스크린샷 작업 수행
    - 결과를 API에 제출

    Args:
        instance_id: 인스턴스 ID
        version: Chrome 버전
        close_after: 작업 완료 후 자동 종료 여부
        window_width: 창 너비 (기본: 1300)
        window_height: 창 높이 (기본: 1200)
        window_x: 창 X 위치 (기본: 10)
        window_y: 창 Y 위치 (기본: 10)
        enable_rank_adjust: 순위 조작 활성화 여부 (기본: False)
        enable_main_filter: 메인 페이지 네트워크 필터 활성화 여부 (기본: False)
        specified_screenshot_id: 지정된 작업 ID (None이면 자동 할당)
    """
    print("\n" + "=" * 60)
    print("🔄 작업 API 모드 시작")
    print("=" * 60 + "\n")

    # API 클라이언트 초기화 (URL은 Config에서 자동으로 가져옴)
    api_client = WorkAPIClient()

    # 작업 할당 요청 (지정된 ID가 있으면 해당 ID로 요청)
    if specified_screenshot_id:
        print(f"📌 지정된 작업 ID로 할당 요청: {specified_screenshot_id}")
        work_data = api_client.allocate_work(screenshot_id=specified_screenshot_id)
    else:
        print("🔄 자동 작업 할당 요청")
        work_data = api_client.allocate_work()

    if not work_data or not work_data.get("success"):
        print("❌ 작업 할당 실패 - 프로그램 종료")
        return False

    # 작업 정보 추출
    screenshot_id = work_data.get("id")
    keyword = work_data.get("keyword")
    product_id = work_data.get("product_id")
    item_id = work_data.get("item_id")
    vendor_item_id = work_data.get("vendor_item_id")
    min_rank = work_data.get("min_rank")  # 최소 순위 (순위 조작용)

    print(f"\n✅ 작업 할당 완료 - 에이전트 실행")
    print("=" * 60 + "\n")

    # 에이전트 실행 (창 위치는 명령행 옵션 그대로 사용)
    # run_workers.py에서 이미 계산된 위치를 전달받음
    success = run_agent_selenium_uc(
        instance_id=instance_id,
        keyword=keyword,
        product_id=product_id,
        item_id=item_id,
        vendor_item_id=vendor_item_id,
        version=version,
        test_detection=False,
        close_after=close_after,
        fresh_profile=fresh_profile,
        screenshot_id=screenshot_id,
        api_client=api_client,
        check_ip=check_ip,
        window_width=window_width,
        window_height=window_height,
        window_x=window_x,
        window_y=window_y,
        enable_rank_adjust=enable_rank_adjust,
        adjust_mode=adjust_mode,
        min_rank=min_rank,
        enable_main_filter=enable_main_filter,
        vpn_pool_worker=vpn_pool_worker,
        enable_fingerprint_spoof=enable_fingerprint_spoof,
        fingerprint_preset=fingerprint_preset
    )

    return success


def scan_chrome_versions() -> dict:
    """chrome-version/ 폴더를 스캔하여 설치된 버전 목록 반환"""
    chrome_dir = Path(__file__).parent / "chrome-version"
    versions = {}

    if not chrome_dir.exists():
        return versions

    for version_dir in chrome_dir.iterdir():
        if version_dir.is_dir():
            chrome_bin = version_dir / "chrome-linux64" / "chrome"
            if chrome_bin.exists():
                versions[version_dir.name] = str(chrome_bin)

    return versions


def get_random_chrome_version() -> str:
    """설치된 Chrome 버전 중 랜덤으로 선택"""
    import random

    versions = scan_chrome_versions()
    if not versions:
        print("\n❌ Chrome이 설치되어 있지 않습니다!")
        return None

    selected = random.choice(list(versions.keys()))
    print(f"🎲 랜덤 버전 선택: Chrome {selected}")
    return selected


def select_chrome_version() -> str:
    """Chrome 버전 선택 인터랙티브 모드"""
    versions = scan_chrome_versions()
    if not versions:
        print("\n❌ Chrome이 설치되어 있지 않습니다!")
        return None

    last_version = load_last_version()

    print("\n" + "=" * 60)
    print("🔍 Chrome 버전 선택")
    print("=" * 60)

    # 버전 리스트 정렬
    numeric_versions = [v for v in versions.keys() if v not in ['beta', 'dev', 'canary']]
    channel_versions = [v for v in versions.keys() if v in ['beta', 'dev', 'canary']]

    try:
        numeric_versions.sort(key=lambda x: int(x))
    except:
        numeric_versions.sort()

    channel_order = {'beta': 1, 'dev': 2, 'canary': 3}
    channel_versions.sort(key=lambda x: channel_order.get(x, 99))

    all_versions = numeric_versions + channel_versions

    # 버전 출력
    for i, version in enumerate(all_versions, 1):
        prefix = "➤" if version == last_version else " "
        print(f"{prefix} {i:2d}. Chrome {version}")

    # 프롬프트
    if last_version:
        prompt = f"\n선택 (1-{len(all_versions)}, Enter=마지막 사용: {last_version}): "
    else:
        prompt = f"\n선택 (1-{len(all_versions)}, Enter=랜덤): "

    version_choice = input(prompt).strip()

    if version_choice:
        try:
            idx = int(version_choice) - 1
            if 0 <= idx < len(all_versions):
                return all_versions[idx]
            else:
                print("❌ 잘못된 선택입니다")
                return None
        except ValueError:
            print("❌ 숫자를 입력하세요")
            return None
    elif last_version:
        print(f"✓ 마지막 사용 버전 선택: Chrome {last_version}")
        return last_version

    return None


def main():
    """메인 진입점"""
    parser = argparse.ArgumentParser(
        description="Coupang Agent V2 - Selenium + undetected-chromedriver (Chrome only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 인터랙티브 모드 (버전 선택)
  python3 agent.py

  # 특정 버전 지정
  python3 agent.py --version 134 --keyword "노트북"

  # VPN 사용
  python3 agent.py --version 134 --vpn 0

  # 작업 API 모드 (서버에서 작업 받기)
  python3 agent.py --work-api

  # 디버그 모드
  python3 agent.py --debug --keyword "키보드"
        """
    )

    # ===================================================================
    # 🎯 핵심 옵션
    # ===================================================================
    core_group = parser.add_argument_group('🎯 Core Options', '핵심 실행 옵션')

    core_group.add_argument(
        "--version",
        type=str,
        default=None,
        metavar="VER",
        help="Chrome version (127-144, beta, dev, canary, or 'random')"
    )

    core_group.add_argument(
        "--keyword",
        type=str,
        default="노트북",
        metavar="TEXT",
        help="Search keyword (default: 노트북)"
    )

    core_group.add_argument(
        "--vpn",
        type=int,
        default=None,
        metavar="N",
        help="VPN server number (0=wg0/vpn0, 1=wg1/vpn1, etc.)"
    )

    core_group.add_argument(
        "--vpn-pool-worker",
        type=int,
        default=None,
        metavar="N",
        help=(
            "VPN Pool worker ID (1-20 theoretical, 1-12 practical). "
            "Uses vpn-worker-N system user. "
            "VPN key is allocated/released automatically by run_workers.py. "
            "Example: --vpn-pool-worker 1 (uses vpn-worker-1, UID 2001)"
        )
    )

    core_group.add_argument(
        "--work-api",
        nargs="?",
        const=True,
        default=False,
        metavar="ID",
        help="Work API mode - fetch tasks from server. Optional: specify work ID"
    )

    # ===================================================================
    # 🎨 상품 매칭 설정
    # ===================================================================
    product_group = parser.add_argument_group('🎨 Product Matching', '타겟 상품 설정')

    product_group.add_argument(
        "--product_id",
        type=str,
        default=TARGET_PRODUCT['product_id'],
        metavar="ID",
        help=f"Product ID (default: {TARGET_PRODUCT['product_id']})"
    )

    product_group.add_argument(
        "--item_id",
        type=str,
        default=TARGET_PRODUCT['item_id'],
        metavar="ID",
        help=f"Item ID (default: {TARGET_PRODUCT['item_id']})"
    )

    product_group.add_argument(
        "--vendor_item_id",
        type=str,
        default=TARGET_PRODUCT['vendor_item_id'],
        metavar="ID",
        help=f"Vendor Item ID (default: {TARGET_PRODUCT['vendor_item_id']})"
    )

    product_group.add_argument(
        "--screenshot-id",
        type=int,
        default=None,
        metavar="ID",
        help="Screenshot work ID (from Work API)"
    )

    # ===================================================================
    # 🪟 브라우저 설정
    # ===================================================================
    browser_group = parser.add_argument_group('🪟 Browser Settings', '브라우저 창 설정')

    browser_group.add_argument(
        "-W", "--width",
        type=int,
        default=1300,
        dest="window_width",
        metavar="PX",
        help="Window width in pixels (default: 1300)"
    )

    browser_group.add_argument(
        "-H", "--height",
        type=int,
        default=1200,
        dest="window_height",
        metavar="PX",
        help="Window height in pixels (default: 1200)"
    )

    browser_group.add_argument(
        "-X", "--x-pos",
        type=int,
        default=10,
        dest="window_x",
        metavar="PX",
        help="Window X position (default: 10)"
    )

    browser_group.add_argument(
        "-Y", "--y-pos",
        type=int,
        default=10,
        dest="window_y",
        metavar="PX",
        help="Window Y position (default: 10)"
    )

    browser_group.add_argument(
        "--close",
        action="store_true",
        help="Auto-close browser after 3 seconds"
    )

    browser_group.add_argument(
        "--fresh-profile",
        action="store_true",
        default=False,
        help="Delete old profile and start fresh (기본: 프로필 유지 + 쿠키/세션만 삭제)"
    )

    # ===================================================================
    # 🔧 고급 옵션
    # ===================================================================
    advanced_group = parser.add_argument_group('🔧 Advanced Options', '고급 설정')

    advanced_group.add_argument(
        "--instance",
        type=int,
        default=1,
        metavar="N",
        help="Instance ID for multi-instance setup (default: 1)"
    )

    advanced_group.add_argument(
        "--enable-main-filter",
        action="store_true",
        default=False,
        help="Enable network filter on main page (차단: 광고/트래킹)"
    )

    advanced_group.add_argument(
        "--adjust",
        action="store_true",
        default=False,
        help="[개발중] Enable rank adjustment (순위 조정 - 미구현)"
    )

    advanced_group.add_argument(
        "--enable-fingerprint-spoof",
        action="store_true",
        default=False,
        help="Enable browser fingerprint spoofing (Canvas, WebGL, Hardware 등 랜덤 변조)"
    )

    advanced_group.add_argument(
        "--fingerprint-preset",
        type=str,
        choices=['minimal', 'light', 'medium', 'full'],
        default='full',
        help="Fingerprint spoofing preset (minimal=GPU+Canvas+Audio, light=+Hardware, medium=+Screen, full=+Touch 권장)"
    )

    # ===================================================================
    # 🐛 디버그 & 테스트
    # ===================================================================
    debug_group = parser.add_argument_group('🐛 Debug & Testing', '디버깅 및 테스트')

    debug_group.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Enable debug mode (상세 로그 + 파일 저장)"
    )

    debug_group.add_argument(
        "--test-detection",
        action="store_true",
        help="Run bot detection test before main task"
    )

    debug_group.add_argument(
        "--ip-check",
        action="store_true",
        help="Display current IP address (uses api.ipify.org)"
    )

    debug_group.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode - manually select options"
    )

    args = parser.parse_args()

    # === 디버그 모드 설정 ===
    from common.constants import Config
    Config.DEBUG_MODE = args.debug
    if args.debug:
        print("🐛 디버그 모드 활성화")

    # === 버전 선택 (최우선 처리) ===
    # --version random 처리
    if args.version and args.version.lower() == 'random':
        args.version = get_random_chrome_version()
        if not args.version:
            return
        print()
    # 옵션 없을 때 인터랙티브 선택 (단, --work-api나 --interactive가 아닐 때만)
    elif not args.version and not args.interactive and not (args.work_api or ENABLE_WORK_API):
        args.version = select_chrome_version()
        if not args.version:
            return
        print("=" * 60 + "\n")

    # === VPN 재실행 로직 ===
    if args.vpn is not None:
        if not os.environ.get('VPN_EXECUTED'):
            # VPN 전환 전에 tech 사용자 권한으로 X11 권한 부여
            vpn_user = f"vpn{args.vpn}"
            try:
                import subprocess
                display = os.environ.get('DISPLAY', ':0')
                cmd = ['xhost', f'+SI:localuser:{vpn_user}']
                env = os.environ.copy()
                env['DISPLAY'] = display

                result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print(f"   ✓ X11 권한 부여: {vpn_user}\n")
            except Exception:
                pass  # 실패해도 계속 진행

            vpn_cmd = shutil.which('vpn')

            if not vpn_cmd:
                local_vpn = os.path.expanduser('~/vpn-ip-rotation/client/vpn')
                if os.path.isfile(local_vpn) and os.access(local_vpn, os.X_OK):
                    vpn_cmd = local_vpn

            if not vpn_cmd:
                print("❌ Error: 'vpn' command not found. Please install VPN client first.")
                print("   GitHub: https://github.com/service0427/vpn")
                return

            print(f"🔄 Restarting with VPN {args.vpn} (wg{args.vpn}/vpn{args.vpn})...\n")

            new_args = []
            skip_next = False
            for arg in sys.argv:
                if skip_next:
                    skip_next = False
                    continue
                if arg == '--vpn':
                    skip_next = True
                    continue
                if arg.startswith('--vpn='):
                    continue
                new_args.append(arg)

            # VPN_EXECUTED 환경 변수를 명시적으로 전달 (sudo -u 전환 시에도 유지)
            # XDG 환경 변수로 ChromeDriver 캐시를 agent 소유자의 홈 디렉토리로 설정
            # → VPN 사용자가 agent 소유자의 ChromeDriver 캐시를 공유 (중복 다운로드 방지)
            current_user_home = os.path.expanduser('~')
            cmd = [vpn_cmd, str(args.vpn), 'env',
                   f'VPN_EXECUTED={args.vpn}',
                   f'XDG_CACHE_HOME={current_user_home}/.cache',
                   f'XDG_DATA_HOME={current_user_home}/.local/share',
                   'python3'] + new_args
            os.execvpe(vpn_cmd, cmd, os.environ.copy())
            return

    # === VPN 키 풀 재실행 로직 (제거됨) ===
    # ⚠️ VPN 키 풀 모드에서는 agent.py에서 os.execvpe() 재실행하지 않음
    #
    # 이유:
    # 1. run_workers.py에서 이미 sudo -u vpn-worker-N으로 올바른 사용자로 시작
    # 2. 멀티스레드 환경에서 os.execvpe()는 전체 프로세스를 교체하여 문제 발생
    # 3. VPN 연결은 run_workers.py의 VPNConnection 클래스가 관리
    #
    # VPN 키 풀 흐름:
    # run_workers.py → VPNConnection.connect() → WireGuard 연결
    # → sudo -u vpn-worker-N python3 agent.py --vpn-pool-worker N
    # → agent.py는 이미 vpn-worker-N 사용자로 실행 중 (UID 2000+N)
    # → 해당 UID의 모든 네트워크 트래픽은 정책 라우팅으로 VPN 경로 사용
    #
    # 단일 VPN 모드 (--vpn N)와의 차이:
    # - 단일 VPN: agent.py가 os.execvpe()로 vpn 래퍼 통해 재실행
    # - VPN 키 풀: run_workers.py가 처음부터 올바른 사용자로 실행

    # === 작업 API 모드 ===
    if args.work_api or ENABLE_WORK_API:
        print("\n🔄 작업 API 모드 활성화")

        # work_api 값 파싱 (True면 자동 할당, 숫자면 해당 ID 지정)
        specified_screenshot_id = None
        if args.work_api is not True:
            try:
                specified_screenshot_id = int(args.work_api)
                print(f"   📌 지정된 작업 ID: {specified_screenshot_id}")
            except (ValueError, TypeError):
                print(f"   ⚠️  잘못된 work ID 형식: {args.work_api}, 자동 할당으로 진행")

        success = run_work_api_mode(
            instance_id=args.instance,
            version=args.version,
            close_after=True,  # work-api 모드에서는 항상 자동 종료
            fresh_profile=args.fresh_profile,
            check_ip=args.ip_check,
            window_width=args.window_width,
            window_height=args.window_height,
            window_x=args.window_x,
            window_y=args.window_y,
            enable_rank_adjust=args.adjust,
            adjust_mode="adjust" if args.adjust else None,
            enable_main_filter=args.enable_main_filter,
            specified_screenshot_id=specified_screenshot_id,
            vpn_pool_worker=args.vpn_pool_worker,
            enable_fingerprint_spoof=args.enable_fingerprint_spoof,
            fingerprint_preset=args.fingerprint_preset
        )
        sys.exit(0 if success else 1)


    # === 인터랙티브 모드 ===
    if args.interactive:
        args.version = select_chrome_version()
        if not args.version:
            return

        print("\n검색 키워드를 입력하세요 (Enter=노트북): ", end="")
        keyword_input = input().strip()
        if keyword_input:
            args.keyword = keyword_input

        print("\n탐지 테스트를 실행하시겠습니까? (y/N): ", end="")
        test_input = input().strip().lower()
        args.test_detection = (test_input == 'y')

    # === 에이전트 실행 ===
    run_agent_selenium_uc(
        instance_id=args.instance,
        keyword=args.keyword,
        product_id=args.product_id,
        item_id=args.item_id,
        vendor_item_id=args.vendor_item_id,
        version=args.version,
        test_detection=args.test_detection,
        close_after=args.close,
        fresh_profile=args.fresh_profile,
        check_ip=args.ip_check,
        window_width=args.window_width,
        window_height=args.window_height,
        window_x=args.window_x,
        window_y=args.window_y,
        enable_rank_adjust=args.adjust,
        adjust_mode="adjust" if args.adjust else None,
        enable_main_filter=args.enable_main_filter,
        enable_fingerprint_spoof=args.enable_fingerprint_spoof,
        fingerprint_preset=args.fingerprint_preset
    )


if __name__ == "__main__":
    main()

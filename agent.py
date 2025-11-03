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

from lib.core.browser_core_uc import BrowserCoreUC
from lib.modules.coupang_handler_selenium import CoupangHandlerSelenium
from lib.modules.product_finder import ProductFinder
from lib.modules.screenshot_processor import ScreenshotProcessor
from lib.modules.work_api_client import WorkAPIClient
from lib.workflows.search_workflow import SearchWorkflow

# 마지막 사용 버전 저장 파일
LAST_VERSION_FILE = Path(__file__).parent / ".last_version"

# 기능 활성화 플래그
ENABLE_RANK_MANIPULATION = False
ENABLE_SCREENSHOT_UPLOAD = True
UPLOAD_SERVER_URL = "http://220.121.120.83/toprekr/upload.php"

# API 통합 설정
ENABLE_WORK_API = False  # 작업 할당/결과 제출 API 사용 여부
WORK_ALLOCATE_URL = "http://61.84.75.37:3302/api/work/allocate-screenshot?site_code=topr"
WORK_RESULT_URL = "http://61.84.75.37:3302/api/work/screenshot-result"

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
        print("\n⏱️  Closing browser in 3 seconds...\n")
        time.sleep(3)
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
    screenshot_id: int = None,
    api_client: WorkAPIClient = None,
    check_ip: bool = False,
    window_width: int = 1300,
    window_height: int = 1200,
    window_x: int = 10,
    window_y: int = 10,
    enable_rank_edit: bool = False,
    edit_mode: str = None,
    min_rank: int = None,
    highlight_preset: str = "default",
    enable_main_filter: bool = False
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
    if vpn_num is not None:
        print(f"🌐 VPN: ✅ wg{vpn_num}/vpn{vpn_num} (Enabled)")
    else:
        print(f"🌐 VPN: ❌ Not used (Local IP)")
    print("=" * 60 + "\n")

    core = None
    try:
        # === 1. 브라우저 초기화 ===
        core = BrowserCoreUC(instance_id=instance_id)

        driver = core.launch(
            version=version,
            use_profile=True,
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

        # === 4. 모듈 초기화 ===
        handler = CoupangHandlerSelenium(driver)
        finder = ProductFinder(driver)
        screenshot_processor = ScreenshotProcessor(
            driver=driver,
            base_dir=str(Path(__file__).parent / "screenshots"),
            upload_url=UPLOAD_SERVER_URL if ENABLE_SCREENSHOT_UPLOAD else None,
            enable_upload=ENABLE_SCREENSHOT_UPLOAD
        )

        # === 5. 워크플로우 실행 ===
        workflow = SearchWorkflow(
            driver=driver,
            handler=handler,
            finder=finder,
            screenshot_processor=screenshot_processor,
            core=core,  # 네트워크 필터 제어를 위해 core 객체 전달
            enable_rank_manipulation=enable_rank_edit,  # 파라미터로 전달받은 값 사용
            edit_mode=edit_mode,  # 순위 조작 모드 ("edit" 또는 "edit2")
            highlight_preset=highlight_preset,
            enable_main_filter=enable_main_filter  # 메인 페이지 필터 활성화 여부
        )

        result = workflow.execute(
            keyword=keyword,
            product_id=product_id,
            item_id=item_id,
            vendor_item_id=vendor_item_id,
            version=version if version else "unknown",
            min_rank=min_rank,  # 최소 순위 전달
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
            else:
                print("\n" + "=" * 60)
                print("📤 작업 결과 제출")
                print("=" * 60 + "\n")

                # 성공 시: 스크린샷 URL 선택, 실패 시: "PRODUCT_NOT_FOUND"
                if result.success:
                    # Edit 모드에서 after 스크린샷이 있으면 after 사용, 아니면 before 사용
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

                # 매칭 조건에 따라 실제로 일치한 필드만 전달
                api_product_id = None
                api_item_id = None
                api_vendor_item_id = None

                if result.success and hasattr(result, 'match_condition') and result.match_condition:
                    match_cond = result.match_condition

                    if "완전 일치" in match_cond:
                        # 모두 일치
                        api_product_id = product_id
                        api_item_id = item_id
                        api_vendor_item_id = vendor_item_id
                    elif "product_id + vendor_item_id 일치" in match_cond:
                        # product_id + vendor_item_id만 일치
                        api_product_id = product_id
                        api_vendor_item_id = vendor_item_id
                    elif "product_id 일치" in match_cond:
                        # product_id만 일치
                        api_product_id = product_id
                    elif "vendor_item_id 일치" in match_cond:
                        # vendor_item_id만 일치
                        api_vendor_item_id = vendor_item_id
                    elif "item_id 일치" in match_cond:
                        # item_id만 일치
                        api_item_id = item_id

                submit_success = api_client.submit_result(
                    screenshot_id=screenshot_id,
                    screenshot_url=screenshot_url,
                    keyword=keyword,
                    rank=rank,
                    product_id=api_product_id,
                    item_id=api_item_id,
                    vendor_item_id=api_vendor_item_id,
                    filename=filename
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
    check_ip: bool = False,
    window_width: int = 1300,
    window_height: int = 1200,
    window_x: int = 10,
    window_y: int = 10,
    highlight_preset: str = "default",
    enable_rank_edit: bool = False,
    edit_mode: str = None,
    enable_main_filter: bool = False,
    specified_screenshot_id: int = None
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
        highlight_preset: 하이라이트 프리셋
        enable_rank_edit: 순위 조작 활성화 여부 (기본: False)
        enable_main_filter: 메인 페이지 네트워크 필터 활성화 여부 (기본: False)
        specified_screenshot_id: 지정된 작업 ID (None이면 자동 할당)
    """
    print("\n" + "=" * 60)
    print("🔄 작업 API 모드 시작")
    print("=" * 60 + "\n")

    # API 클라이언트 초기화
    api_client = WorkAPIClient(
        allocate_url=WORK_ALLOCATE_URL,
        result_url=WORK_RESULT_URL
    )

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

    # Instance별로 창 위치 자동 조정 (멀티 워커 지원)
    # Instance 1: (10, 10), Instance 2: (10 + 1300, 10), Instance 3: (10, 10 + 1200), ...
    calc_x = window_x + ((instance_id - 1) % 2) * window_width
    calc_y = window_y + ((instance_id - 1) // 2) * window_height

    # 에이전트 실행
    success = run_agent_selenium_uc(
        instance_id=instance_id,
        keyword=keyword,
        product_id=product_id,
        item_id=item_id,
        vendor_item_id=vendor_item_id,
        version=version,
        test_detection=False,
        close_after=close_after,
        screenshot_id=screenshot_id,
        api_client=api_client,
        check_ip=check_ip,
        window_width=window_width,
        window_height=window_height,
        window_x=calc_x,
        window_y=calc_y,
        highlight_preset=highlight_preset,
        enable_rank_edit=enable_rank_edit,
        edit_mode=edit_mode,
        min_rank=min_rank,
        enable_main_filter=enable_main_filter
    )

    return success


def get_random_chrome_version() -> str:
    """설치된 Chrome 버전 중 랜덤으로 선택"""
    from multi_browser_manager import BrowserVersionManager
    import random

    manager = BrowserVersionManager()
    if not manager.chrome_versions:
        print("\n❌ Chrome이 설치되어 있지 않습니다!")
        return None

    all_versions = list(manager.chrome_versions.keys())
    selected = random.choice(all_versions)
    print(f"🎲 랜덤 버전 선택: Chrome {selected}")
    return selected


def select_chrome_version() -> str:
    """Chrome 버전 선택 인터랙티브 모드"""
    from multi_browser_manager import BrowserVersionManager

    manager = BrowserVersionManager()
    if not manager.chrome_versions:
        print("\n❌ Chrome이 설치되어 있지 않습니다!")
        return None

    last_version = load_last_version()

    print("\n" + "=" * 60)
    print("🔍 Chrome 버전 선택")
    print("=" * 60)

    # 버전 리스트 정렬
    numeric_versions = [v for v in manager.chrome_versions.keys() if v not in ['beta', 'dev', 'canary']]
    channel_versions = [v for v in manager.chrome_versions.keys() if v in ['beta', 'dev', 'canary']]

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
        description="Coupang Agent V2 - Selenium + undetected-chromedriver (Chrome only)"
    )

    parser.add_argument(
        "--instance",
        type=int,
        default=1,
        help="Instance ID (default: 1)"
    )

    parser.add_argument(
        "--keyword",
        type=str,
        default="노트북",
        help="Search keyword (default: 노트북)"
    )

    parser.add_argument(
        "--product_id",
        type=str,
        default=TARGET_PRODUCT['product_id'],
        help=f"Product ID for matching (default: {TARGET_PRODUCT['product_id']})"
    )

    parser.add_argument(
        "--item_id",
        type=str,
        default=TARGET_PRODUCT['item_id'],
        help=f"Item ID for matching (default: {TARGET_PRODUCT['item_id']})"
    )

    parser.add_argument(
        "--vendor_item_id",
        type=str,
        default=TARGET_PRODUCT['vendor_item_id'],
        help=f"Vendor Item ID for matching (default: {TARGET_PRODUCT['vendor_item_id']})"
    )

    parser.add_argument(
        "--version",
        type=str,
        default=None,
        help="Chrome version (127-144, beta, dev, canary, or 'random')"
    )

    parser.add_argument(
        "--test-detection",
        action="store_true",
        help="Run detection test first"
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode - select version manually"
    )

    parser.add_argument(
        "--close",
        action="store_true",
        help="Close browser automatically after 3 seconds"
    )

    parser.add_argument(
        "--vpn",
        type=int,
        default=None,
        help="VPN server number (0=wg0/vpn0, 1=wg1/vpn1, etc.)"
    )

    parser.add_argument(
        "--work-api",
        nargs="?",  # 옵션 값이 있을 수도, 없을 수도 있음
        const=True,  # 값 없이 --work-api만 쓰면 True
        default=False,
        help="Work API mode - fetch work from allocation API. Use --work-api=123 to specify work ID"
    )

    parser.add_argument(
        "--ip-check",
        action="store_true",
        help="Check IP address before running (uses api.ipify.org)"
    )

    # 창 크기 및 위치 설정
    parser.add_argument(
        "-W", "--width",
        type=int,
        default=1300,
        dest="window_width",
        help="Browser window width (default: 1300)"
    )

    parser.add_argument(
        "-H", "--height",
        type=int,
        default=1200,
        dest="window_height",
        help="Browser window height (default: 1200)"
    )

    parser.add_argument(
        "-X", "--x-pos",
        type=int,
        default=10,
        dest="window_x",
        help="Browser window X position (default: 10)"
    )

    parser.add_argument(
        "-Y", "--y-pos",
        type=int,
        default=10,
        dest="window_y",
        help="Browser window Y position (default: 10)"
    )

    parser.add_argument(
        "--highlight",
        type=str,
        default="default",
        choices=["default"],
        help="Highlight preset for matched product (default: default)"
    )

    parser.add_argument(
        "--edit",
        action="store_true",
        default=False,
        help="Enable rank manipulation (순위 조작 활성화 - 복잡한 DOM 재구성, 기본: False)"
    )

    parser.add_argument(
        "--edit2",
        action="store_true",
        default=False,
        help="Enable rank manipulation v2 (순위 조작 활성화 - Simple Swap, 기본: False)"
    )

    parser.add_argument(
        "--enable-main-filter",
        action="store_true",
        default=False,
        help="Enable network filter on Coupang main page (메인 페이지 광고/트래킹 차단, 기본: False)"
    )

    args = parser.parse_args()

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
            env = os.environ.copy()
            env['VPN_EXECUTED'] = str(args.vpn)

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

            cmd = [vpn_cmd, str(args.vpn), 'python3'] + new_args
            os.execvpe(vpn_cmd, cmd, env)
            return
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
            close_after=args.close,
            check_ip=args.ip_check,
            window_width=args.window_width,
            window_height=args.window_height,
            window_x=args.window_x,
            window_y=args.window_y,
            highlight_preset=args.highlight,
            enable_rank_edit=args.edit or args.edit2,
            edit_mode="edit2" if args.edit2 else ("edit" if args.edit else None),
            enable_main_filter=args.enable_main_filter,
            specified_screenshot_id=specified_screenshot_id
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
        check_ip=args.ip_check,
        window_width=args.window_width,
        window_height=args.window_height,
        window_x=args.window_x,
        window_y=args.window_y,
        highlight_preset=args.highlight,
        enable_rank_edit=args.edit or args.edit2,
        edit_mode="edit2" if args.edit2 else ("edit" if args.edit else None),
        enable_main_filter=args.enable_main_filter
    )


if __name__ == "__main__":
    main()

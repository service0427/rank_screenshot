#!/usr/bin/env python3
"""
핑거프린트 랜덤화 테스트 스크립트
Chrome 130 전용, IP 차단 상태에서 검색 통과 테스트

기존 agent.py에 영향 없이 독립적으로 실행 가능
"""

import os
import sys
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.core.browser_core_uc import BrowserCoreUC
from lib.modules.coupang_handler_selenium import CoupangHandlerSelenium
from lib.utils.fingerprint_randomizer import FingerprintRandomizer
from lib.constants import ExecutionStatus, ActionStatus


def test_fingerprint_bypass(
    use_randomization: bool = True,
    keyword: str = "노트북",
    close_after: bool = False
):
    """
    핑거프린트 랜덤화 우회 테스트

    Args:
        use_randomization: 핑거프린트 랜덤화 사용 여부
        keyword: 검색 키워드
        close_after: 테스트 후 자동 종료
    """
    print("\n" + "=" * 60)
    print("🧪 핑거프린트 우회 테스트 - Chrome 130")
    print("=" * 60)
    print(f"Chrome Version: 130 (고정)")
    print(f"핑거프린트 랜덤화: {'✅ 활성화' if use_randomization else '❌ 비활성화'}")
    print(f"검색 키워드: {keyword}")

    # VPN 정보 표시
    vpn_num = os.environ.get('VPN_EXECUTED')
    if vpn_num and vpn_num != '0':
        print(f"VPN: ✅ Server {vpn_num}")
    else:
        print(f"VPN: ❌ 로컬 IP (차단된 상태)")

    print("=" * 60 + "\n")

    # Browser Core 초기화
    core = BrowserCoreUC(instance_id=999)  # 테스트용 ID

    try:
        # Chrome 130 시크릿모드로 브라우저 실행 (프로필 사용 안 함)
        print("🚀 Chrome 130 실행 중 (시크릿모드)...")
        driver = core.launch(
            version="130",  # 하드코딩
            use_profile=False,  # 시크릿모드 (프로필 사용 안 함)
            headless=False
        )
        print("   ✓ Chrome 130 실행 완료 (시크릿모드)\n")

        # 핑거프린트 랜덤화 적용
        if use_randomization:
            FingerprintRandomizer.apply_all(driver)
        else:
            print("⚠️  핑거프린트 랜덤화 비활성화 (기본 상태)\n")

        # 핑거프린트 정보 출력
        print("=" * 60)
        print("📊 현재 브라우저 핑거프린트 정보")
        print("=" * 60)
        fp_info = FingerprintRandomizer.get_fingerprint_info(driver)
        if fp_info:
            print(f"   User Agent: {fp_info.get('userAgent', 'N/A')[:80]}...")
            print(f"   Platform: {fp_info.get('platform', 'N/A')}")
            print(f"   Language: {fp_info.get('language', 'N/A')}")
            print(f"   CPU Cores: {fp_info.get('hardwareConcurrency', 'N/A')}")
            print(f"   Device Memory: {fp_info.get('deviceMemory', 'N/A')} GB")
            screen = fp_info.get('screen', {})
            print(f"   Screen: {screen.get('width', 'N/A')}x{screen.get('height', 'N/A')}")
            viewport = fp_info.get('viewport', {})
            print(f"   Viewport: {viewport.get('width', 'N/A')}x{viewport.get('height', 'N/A')}")
        print("=" * 60 + "\n")

        # IP 주소 확인
        print("=" * 60)
        print("🌐 IP 주소 확인")
        print("=" * 60)

        try:
            driver.get("https://api.ipify.org?format=json")
            time.sleep(1)
            ip_json = driver.find_element("tag name", "pre").text

            import json
            ip_data = json.loads(ip_json)
            ip_address = ip_data.get('ip', 'Unknown')

            if vpn_num and vpn_num != '0':
                print(f"   📍 VPN Server {vpn_num} IP: {ip_address}")
            else:
                print(f"   📍 로컬 IP: {ip_address}")
        except Exception as e:
            print(f"   ⚠️  IP 확인 실패: {e}")

        print("=" * 60 + "\n")

        # 쿠팡 핸들러 초기화
        handler = CoupangHandlerSelenium(driver)

        # 시크릿모드는 자동으로 쿠키/세션이 초기화되므로 별도 작업 불필요
        print("📝 시크릿모드: 쿠키/세션 자동 초기화됨\n")

        # 쿠팡 홈 이동
        print("🏠 쿠팡 홈페이지 이동 중...")
        if not handler.navigate_to_home():
            print("   ❌ 홈페이지 이동 실패")
            return
        print("   ✓ 홈페이지 로드 완료\n")

        # 상품 검색
        print(f"🔍 '{keyword}' 검색 중...")
        if not handler.search_product(keyword):
            print("   ❌ 검색 실패")
            return
        print("   ✓ 검색 완료\n")

        # 오류 체크
        print("🔍 차단 여부 확인 중...")
        time.sleep(2)

        status = handler.get_status()
        current_url = driver.current_url

        # 결과 판정
        print("\n" + "=" * 60)
        if status['action_status'] == ActionStatus.SUCCESS:
            print("✅ 성공: 검색이 정상적으로 완료되었습니다!")
            print("=" * 60)
            print(f"현재 URL: {current_url}")
            print(f"상태: {status}")
            print("=" * 60)

            if use_randomization:
                print("\n🎉 핑거프린트 랜덤화로 차단 우회 성공!")
            else:
                print("\n⚠️  핑거프린트 랜덤화 없이도 통과 (차단되지 않은 상태)")
        else:
            print("❌ 실패: 검색이 차단되었거나 오류가 발생했습니다")
            print("=" * 60)
            print(f"현재 URL: {current_url}")
            print(f"상태: {status}")
            print("=" * 60)

            # 오류 메시지 상세 출력
            if 'http2_protocol_error' in current_url.lower() or 'error' in current_url.lower():
                print("\n🚫 http2_protocol_error 또는 차단 페이지 감지")
                print("   → IP 차단 또는 브라우저 핑거프린트 차단")

                if use_randomization:
                    print("   → 핑거프린트 랜덤화를 사용했지만 여전히 차단됨")
                    print("   → 추가 변조 기법이 필요할 수 있음")
                else:
                    print("   → 핑거프린트 랜덤화를 사용하지 않음")
                    print("   → --randomize 옵션으로 재시도 권장")

        # 자동 종료 처리
        if close_after:
            print("\n⏳ 3초 후 자동 종료...")
            time.sleep(3)
        else:
            print("\n⏸️  브라우저를 열어둡니다. 확인 후 Enter를 누르면 종료합니다...")
            input()

    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 테스트를 중단했습니다\n")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}\n")
        import traceback
        traceback.print_exc()
    finally:
        # 브라우저 정리
        if 'driver' in locals():
            try:
                driver.quit()
                print("\n🧹 브라우저 종료 완료\n")
            except:
                pass


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="핑거프린트 랜덤화 테스트 - Chrome 130 전용"
    )

    parser.add_argument(
        "--randomize",
        action="store_true",
        help="핑거프린트 랜덤화 활성화 (기본: 비활성화)"
    )

    parser.add_argument(
        "--keyword",
        type=str,
        default="노트북",
        help="검색 키워드 (기본: 노트북)"
    )

    parser.add_argument(
        "--close",
        action="store_true",
        help="테스트 후 3초 뒤 자동 종료"
    )

    args = parser.parse_args()

    # 테스트 실행
    test_fingerprint_bypass(
        use_randomization=args.randomize,
        keyword=args.keyword,
        close_after=args.close
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n프로그램이 종료되었습니다\n")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}\n")
        import traceback
        traceback.print_exc()

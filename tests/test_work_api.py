#!/usr/bin/env python3
"""
작업 API 클라이언트 테스트
"""

from lib.modules.work_api_client import WorkAPIClient


def test_allocate_work():
    """작업 할당 API 테스트"""
    print("\n" + "=" * 60)
    print("🧪 작업 할당 API 테스트")
    print("=" * 60 + "\n")

    client = WorkAPIClient(
        allocate_url="http://61.84.75.37:3302/api/work/allocate-screenshot",
        result_url="http://localhost:3302/api/work/screenshot-result"
    )

    # 작업 할당 요청
    work_data = client.allocate_work()

    if work_data and work_data.get("success"):
        print("\n✅ 작업 할당 성공!")
        print(f"\n작업 정보:")
        print(f"  - ID: {work_data.get('id')}")
        print(f"  - 키워드: {work_data.get('keyword')}")
        print(f"  - 상품 ID: {work_data.get('product_id')}")
        print(f"  - 아이템 ID: {work_data.get('item_id')}")
        print(f"  - 판매자 아이템 ID: {work_data.get('vendor_item_id')}")
        print(f"  - 최소 순위: {work_data.get('min_rank')}")
        return work_data
    else:
        print("\n❌ 작업 할당 실패")
        return None


def test_submit_result():
    """작업 결과 제출 API 테스트"""
    print("\n" + "=" * 60)
    print("🧪 작업 결과 제출 API 테스트")
    print("=" * 60 + "\n")

    client = WorkAPIClient(
        allocate_url="http://61.84.75.37:3302/api/work/allocate-screenshot",
        result_url="http://localhost:3302/api/work/screenshot-result"
    )

    # 테스트용 데이터
    test_work_id = 4948534
    test_screenshot_url = "https://example.com/test.png"

    print(f"테스트 데이터:")
    print(f"  - 작업 ID: {test_work_id}")
    print(f"  - 스크린샷 URL: {test_screenshot_url}\n")

    # 결과 제출
    success = client.submit_result(
        work_id=test_work_id,
        screenshot_url=test_screenshot_url
    )

    if success:
        print("\n✅ 작업 결과 제출 성공!")
    else:
        print("\n❌ 작업 결과 제출 실패")

    return success


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 작업 API 클라이언트 테스트")
    print("=" * 60)

    # 1. 작업 할당 테스트
    work_data = test_allocate_work()

    # 2. 작업 결과 제출 테스트 (주석 처리 - 실제 작업 ID가 필요)
    # test_submit_result()

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60 + "\n")

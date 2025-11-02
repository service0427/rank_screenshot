#!/usr/bin/env python3
"""
창 위치 테스트 스크립트
여러 위치에서 창을 열어서 실제 위치가 적용되는지 확인
"""

import sys
sys.path.insert(0, '/home/tech/agent')

from lib.core.browser_core_uc import BrowserCoreUC
import time

def test_position(x, y):
    """특정 위치에서 브라우저를 열고 실제 위치 확인"""
    print(f"\n{'='*60}")
    print(f"테스트: X={x}, Y={y}")
    print('='*60)

    core = BrowserCoreUC(instance_id=1)

    try:
        # 브라우저 실행
        driver = core.launch(
            version="134",
            use_profile=True,
            headless=False,
            window_width=800,
            window_height=600,
            window_x=x,
            window_y=y
        )

        # 실제 적용된 위치 확인
        time.sleep(1)
        actual_pos = driver.get_window_position()
        actual_size = driver.get_window_size()

        print(f"\n✅ 브라우저 시작 성공:")
        print(f"   요청 위치: X={x}, Y={y}")
        print(f"   실제 위치: X={actual_pos['x']}, Y={actual_pos['y']}")
        print(f"   창 크기: {actual_size['width']}x{actual_size['height']}")

        # 위치 일치 여부
        if actual_pos['x'] == x and actual_pos['y'] == y:
            print(f"   ✅ 위치 정확히 일치!")
        else:
            print(f"   ⚠️  위치 불일치 (차이: X={abs(actual_pos['x']-x)}, Y={abs(actual_pos['y']-y)})")

        # 3초 대기 (사용자가 확인할 시간)
        time.sleep(3)

        # 종료
        driver.quit()

        return True

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        time.sleep(1)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 창 위치 테스트 시작")
    print("="*60)

    # 다양한 위치 테스트
    test_cases = [
        (0, 0),      # 좌측 상단
        (100, 200),  # 약간 오른쪽 아래
        (500, 300),  # 중간쯤
        (0, 0),      # 다시 좌측 상단 (이전 위치 기억 여부 확인)
    ]

    results = []
    for x, y in test_cases:
        success = test_position(x, y)
        results.append((x, y, success))

    # 최종 결과
    print("\n" + "="*60)
    print("📊 최종 결과")
    print("="*60)
    for x, y, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"   X={x:4d}, Y={y:4d}: {status}")
    print("="*60 + "\n")

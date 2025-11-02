#!/usr/bin/env python3
"""
쿠팡 검색창 요소 확인 테스트
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from lib.core.browser_core_uc import BrowserCoreUC
import time


def test_search_input():
    """검색 입력창 요소 확인"""
    print("\n" + "=" * 60)
    print("🔍 쿠팡 검색창 요소 확인 테스트")
    print("=" * 60 + "\n")

    core = BrowserCoreUC(instance_id=1)

    try:
        driver = core.launch(version="134", use_profile=True, headless=False)

        if not driver:
            print("❌ 브라우저 실행 실패")
            return

        # 쿠팡 홈페이지 이동
        print("🏠 쿠팡 홈페이지로 이동...")
        driver.get("https://www.coupang.com")
        time.sleep(3)

        print("✅ 페이지 로드 완료\n")

        # 검색창 확인 스크립트
        check_script = """
        console.log("=== 쿠팡 검색창 요소 확인 ===");

        // 1. 기존 셀렉터
        const oldInput = document.querySelector('input.is-speech[name="q"]');
        console.log("1. input.is-speech[name='q']:", oldInput);

        // 2. name="q"만
        const nameQ = document.querySelector('input[name="q"]');
        console.log("2. input[name='q']:", nameQ);

        // 3. 모든 input 태그
        const allInputs = document.querySelectorAll('input');
        console.log("3. 전체 input 개수:", allInputs.length);

        // 4. 검색 관련 input
        const searchInputs = Array.from(allInputs).filter(inp =>
            inp.type === 'search' ||
            inp.placeholder?.includes('검색') ||
            inp.name === 'q'
        );
        console.log("4. 검색 관련 input 개수:", searchInputs.length);
        searchInputs.forEach((inp, i) => {
            console.log(`   [${i}] type="${inp.type}" name="${inp.name}" class="${inp.className}" placeholder="${inp.placeholder}"`);
        });

        // 5. 검색 버튼
        const searchBtn = document.querySelector('button.headerSearchBtn[type="submit"]');
        console.log("5. button.headerSearchBtn[type='submit']:", searchBtn);

        // 6. 모든 submit 버튼
        const allSubmitBtns = document.querySelectorAll('button[type="submit"]');
        console.log("6. 전체 submit 버튼 개수:", allSubmitBtns.length);

        // 7. form 태그
        const forms = document.querySelectorAll('form');
        console.log("7. 전체 form 개수:", forms.length);
        forms.forEach((f, i) => {
            console.log(`   [${i}] role="${f.role}" action="${f.action}"`);
        });

        return {
            oldInput: oldInput ? true : false,
            nameQ: nameQ ? true : false,
            allInputsCount: allInputs.length,
            searchInputsCount: searchInputs.length,
            searchBtn: searchBtn ? true : false,
            formsCount: forms.length
        };
        """

        result = driver.execute_script(check_script)

        print("📊 검색 결과:")
        print(f"   - 기존 셀렉터 (input.is-speech[name='q']): {'✅' if result['oldInput'] else '❌'}")
        print(f"   - name='q' input: {'✅' if result['nameQ'] else '❌'}")
        print(f"   - 전체 input 개수: {result['allInputsCount']}")
        print(f"   - 검색 관련 input 개수: {result['searchInputsCount']}")
        print(f"   - 검색 버튼: {'✅' if result['searchBtn'] else '❌'}")
        print(f"   - 전체 form 개수: {result['formsCount']}")

        # 브라우저 콘솔 로그 확인
        print("\n📝 브라우저 콘솔 로그를 확인하세요 (F12 → Console)")
        print("\n⏸️  Enter를 눌러 브라우저를 종료하세요...")
        input()

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if core:
            core.close_browser()
            print("✅ 브라우저 종료\n")


if __name__ == "__main__":
    test_search_input()

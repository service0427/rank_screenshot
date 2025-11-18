#!/usr/bin/env python3
"""
RankMark 배지 추출 테스트 스크립트

쿠팡 검색 결과 페이지에서 1~10위 RankMark 배지를 추출하여
JavaScript와 Selenium 두 방식으로 모두 검증합니다.
"""

import sys
import time
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from selenium.webdriver.common.by import By
from uc_lib.core.browser_core_uc import BrowserCoreUC
from uc_lib.modules.coupang_handler_selenium import CoupangHandlerSelenium


def test_rankmark_detection():
    """RankMark 배지 감지 테스트"""

    print("\n" + "=" * 80)
    print("🔍 RankMark 배지 추출 테스트")
    print("=" * 80)

    # 1. 브라우저 초기화
    print("\n1️⃣  브라우저 초기화 중...")
    core = BrowserCoreUC(
        version_main=144,
        use_profile=False,
        headless=False
    )
    driver = core.driver
    handler = CoupangHandlerSelenium(driver)

    print("   ✅ 브라우저 실행 완료")

    # 2. 쿠팡 홈 이동
    print("\n2️⃣  쿠팡 홈페이지 이동 중...")
    handler.navigate_to_home()
    time.sleep(2)
    print("   ✅ 홈페이지 로드 완료")

    # 3. 검색 실행
    keyword = "냉장고부착볼펜"
    print(f"\n3️⃣  '{keyword}' 검색 중...")
    handler.search_product(keyword)
    time.sleep(3)
    print("   ✅ 검색 결과 로드 완료")

    # 4. JavaScript 방식으로 RankMark 추출
    print("\n" + "=" * 80)
    print("📊 방법 1: JavaScript execute_script() 방식")
    print("=" * 80)

    js_result = driver.execute_script("""
        // RankMark 배지 추출
        const rankMarks = document.querySelectorAll('#product-list span[class^="RankMark_rank"]');

        console.log('🔍 RankMark 배지 검색 시작');
        console.log('  선택자: #product-list span[class^="RankMark_rank"]');
        console.log('  발견 개수: ' + rankMarks.length);
        console.log('');

        // 각 배지 정보 수집
        const badges = [];
        rankMarks.forEach((mark, index) => {
            const text = mark.textContent.trim();
            const className = mark.className;
            const parentLi = mark.closest('li[data-id]');
            const dataId = parentLi ? parentLi.getAttribute('data-id') : 'N/A';

            console.log('  [' + index + '] 배지: "' + text + '"');
            console.log('      클래스: ' + className);
            console.log('      data-id: ' + dataId);
            console.log('');

            badges.push({
                index: index,
                text: text,
                className: className,
                dataId: dataId
            });
        });

        return {
            count: rankMarks.length,
            badges: badges
        };
    """)

    print(f"\n📋 JavaScript 결과:")
    print(f"   발견 개수: {js_result['count']}개")

    if js_result['count'] > 0:
        print(f"\n   배지 상세 정보:")
        for badge in js_result['badges']:
            print(f"   [{badge['index']}] \"{badge['text']}\" - {badge['className']}")
            print(f"       data-id: {badge['dataId']}")
    else:
        print(f"   ⚠️  RankMark 배지를 찾지 못했습니다!")

    # 5. Selenium find_elements 방식으로 RankMark 추출
    print("\n" + "=" * 80)
    print("📊 방법 2: Selenium find_elements() 방식")
    print("=" * 80)

    try:
        # CSS Selector 방식
        rankmarks_css = driver.find_elements(By.CSS_SELECTOR, '#product-list span[class^="RankMark_rank"]')
        print(f"\n📋 Selenium CSS Selector 결과:")
        print(f"   발견 개수: {len(rankmarks_css)}개")

        if len(rankmarks_css) > 0:
            print(f"\n   배지 상세 정보:")
            for i, mark in enumerate(rankmarks_css):
                text = mark.text.strip()
                class_name = mark.get_attribute('class')
                parent_li = mark.find_element(By.XPATH, './ancestor::li[@data-id]')
                data_id = parent_li.get_attribute('data-id') if parent_li else 'N/A'

                print(f"   [{i}] \"{text}\" - {class_name}")
                print(f"       data-id: {data_id}")
        else:
            print(f"   ⚠️  RankMark 배지를 찾지 못했습니다!")

    except Exception as e:
        print(f"   ❌ Selenium 추출 실패: {e}")

    # 6. XPath 방식으로도 시도
    print("\n" + "=" * 80)
    print("📊 방법 3: Selenium XPath 방식")
    print("=" * 80)

    try:
        rankmarks_xpath = driver.find_elements(By.XPATH, '//ul[@id="product-list"]//span[starts-with(@class, "RankMark_rank")]')
        print(f"\n📋 Selenium XPath 결과:")
        print(f"   발견 개수: {len(rankmarks_xpath)}개")

        if len(rankmarks_xpath) > 0:
            print(f"\n   배지 상세 정보:")
            for i, mark in enumerate(rankmarks_xpath):
                text = mark.text.strip()
                class_name = mark.get_attribute('class')
                print(f"   [{i}] \"{text}\" - {class_name}")
        else:
            print(f"   ⚠️  RankMark 배지를 찾지 못했습니다!")

    except Exception as e:
        print(f"   ❌ XPath 추출 실패: {e}")

    # 7. 전체 상품 리스트 구조 분석
    print("\n" + "=" * 80)
    print("📊 상품 리스트 구조 분석")
    print("=" * 80)

    structure = driver.execute_script("""
        const allItems = document.querySelectorAll('#product-list > li[data-id]');
        const structure = {
            totalItems: allItems.length,
            items: []
        };

        allItems.forEach((item, index) => {
            const dataId = item.getAttribute('data-id');
            const link = item.querySelector('a[href*="/vp/products/"]');
            const href = link ? link.getAttribute('href') : null;
            const hasRank = href && (href.includes('&rank=') || href.includes('?rank='));
            const rankMatch = href ? href.match(/[&?]rank=(\\d+)/) : null;
            const rank = rankMatch ? rankMatch[1] : null;
            const hasAdMark = item.querySelector('[class*="AdMark"]') !== null;
            const hasRankMark = item.querySelector('span[class^="RankMark_rank"]') !== null;
            const rankMarkText = hasRankMark ? item.querySelector('span[class^="RankMark_rank"]').textContent.trim() : null;

            if (index < 15) {  // 첫 15개만 출력
                structure.items.push({
                    index: index,
                    dataId: dataId,
                    rank: rank,
                    hasAdMark: hasAdMark,
                    hasRankMark: hasRankMark,
                    rankMarkText: rankMarkText
                });
            }
        });

        return structure;
    """)

    print(f"\n   전체 상품: {structure['totalItems']}개")
    print(f"\n   첫 15개 상품 상세:")
    print(f"   {'Index':<6} {'Rank':<6} {'광고':<6} {'배지유무':<10} {'배지텍스트':<12} {'data-id':<15}")
    print(f"   {'-'*70}")

    for item in structure['items']:
        ad_mark = "✅" if item['hasAdMark'] else "  "
        rank_mark = "✅" if item['hasRankMark'] else "❌"
        rank = item['rank'] or 'N/A'
        badge_text = item['rankMarkText'] or '-'
        data_id = item['dataId'][:12] + '...'

        print(f"   {item['index']:<6} {rank:<6} {ad_mark:<6} {rank_mark:<10} {badge_text:<12} {data_id:<15}")

    # 8. 최종 결과 요약
    print("\n" + "=" * 80)
    print("📊 최종 결과 요약")
    print("=" * 80)

    js_count = js_result['count']
    selenium_css_count = len(rankmarks_css) if 'rankmarks_css' in locals() else 0
    selenium_xpath_count = len(rankmarks_xpath) if 'rankmarks_xpath' in locals() else 0

    print(f"\n   JavaScript:        {js_count}개")
    print(f"   Selenium CSS:      {selenium_css_count}개")
    print(f"   Selenium XPath:    {selenium_xpath_count}개")

    if js_count == 10 and selenium_css_count == 10:
        print(f"\n   ✅ 성공: 모든 방식에서 10개 배지 추출 완료!")
    elif js_count > 0 or selenium_css_count > 0:
        print(f"\n   ⚠️  부분 성공: 일부 방식에서만 배지 추출됨")
    else:
        print(f"\n   ❌ 실패: 모든 방식에서 배지를 찾지 못했습니다")
        print(f"\n   🔍 원인 분석:")
        print(f"      1. RankMark 클래스명이 변경되었을 수 있음")
        print(f"      2. 배지가 JavaScript로 지연 로딩될 수 있음")
        print(f"      3. 선택자가 잘못되었을 수 있음")

    # 9. 브라우저 유지 (수동 확인용)
    print("\n" + "=" * 80)
    print("⏸️  브라우저 유지 (F12로 수동 확인 가능)")
    print("=" * 80)
    print("\n   브라우저 콘솔에서 다음 명령어를 실행해보세요:")
    print("   document.querySelectorAll('#product-list span[class^=\"RankMark_rank\"]')")
    print("\n   종료하려면 Enter 키를 누르세요...")

    input()

    # 10. 정리
    print("\n브라우저 종료 중...")
    driver.quit()
    print("✅ 테스트 완료\n")


if __name__ == "__main__":
    try:
        test_rankmark_detection()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 중단했습니다")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

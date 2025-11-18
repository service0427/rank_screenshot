"""
RankMark 배지 진단 모듈

DOM 스왑 전에 배지가 정상적으로 존재하는지 확인
"""

from typing import Dict, List


class BadgeDiagnostic:
    """배지 존재 여부 진단 클래스"""

    def __init__(self, driver):
        """
        Args:
            driver: Selenium WebDriver 인스턴스
        """
        self.driver = driver

    def check_rankmark_existence(self) -> Dict:
        """
        RankMark 배지 존재 여부 확인

        Returns:
            Dict: 진단 결과
                - js_count: JavaScript로 찾은 배지 개수
                - selenium_count: Selenium으로 찾은 배지 개수
                - badges: 배지 상세 정보 리스트
                - success: 진단 성공 여부 (10개 이상)
        """
        print("\n" + "=" * 60)
        print("🔍 RankMark 배지 진단")
        print("=" * 60)

        # 1. JavaScript 방식으로 배지 추출
        js_result = self.driver.execute_script("""
            const rankMarks = document.querySelectorAll('#product-list span[class^="RankMark_rank"]');

            console.log('🔍 RankMark 배지 검색');
            console.log('  선택자: #product-list span[class^="RankMark_rank"]');
            console.log('  발견 개수: ' + rankMarks.length);

            const badges = [];
            rankMarks.forEach((mark, index) => {
                const text = mark.textContent.trim();
                const className = mark.className;
                const parentLi = mark.closest('li[data-id]');
                const dataId = parentLi ? parentLi.getAttribute('data-id') : 'N/A';

                console.log('  [' + index + '] "' + text + '" - ' + className);

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

        js_count = js_result['count']
        badges = js_result['badges']

        # 2. 결과 출력
        print(f"\n📊 JavaScript 추출 결과: {js_count}개")

        if js_count > 0:
            print(f"\n   배지 목록:")
            for badge in badges:
                print(f"   [{badge['index']}] \"{badge['text']}\" - {badge['className']}")
        else:
            print(f"   ⚠️  RankMark 배지를 찾지 못했습니다!")

        # 3. 성공 여부 판단
        success = js_count >= 10

        if success:
            print(f"\n   ✅ 진단 성공: 10개 배지 확인됨")
        else:
            print(f"\n   ❌ 진단 실패: 배지 {js_count}개만 발견")
            print(f"   🔍 가능한 원인:")
            print(f"      1. 페이지 로딩이 완료되지 않음")
            print(f"      2. RankMark 클래스명이 변경됨")
            print(f"      3. 1페이지가 아닐 수 있음")

        print("=" * 60)

        return {
            'js_count': js_count,
            'badges': badges,
            'success': success
        }

    def analyze_product_structure(self) -> Dict:
        """
        상품 리스트 구조 분석 (디버깅용)

        Returns:
            Dict: 구조 분석 결과
                - totalItems: 전체 상품 개수
                - items: 상품별 상세 정보
        """
        print("\n" + "=" * 60)
        print("📊 상품 리스트 구조 분석")
        print("=" * 60)

        structure = self.driver.execute_script("""
            const allItems = document.querySelectorAll('#product-list > li[data-id]');
            const items = [];

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

                if (index < 15) {  // 첫 15개만
                    items.push({
                        index: index,
                        dataId: dataId,
                        rank: rank,
                        hasAdMark: hasAdMark,
                        hasRankMark: hasRankMark,
                        rankMarkText: rankMarkText
                    });
                }
            });

            return {
                totalItems: allItems.length,
                items: items
            };
        """)

        print(f"\n   전체 상품: {structure['totalItems']}개")
        print(f"\n   첫 15개 상품:")
        print(f"   {'Index':<6} {'Rank':<6} {'광고':<6} {'배지':<6} {'배지텍스트':<12}")
        print(f"   {'-'*50}")

        for item in structure['items']:
            ad_mark = "✅" if item['hasAdMark'] else "  "
            rank_mark = "✅" if item['hasRankMark'] else "❌"
            rank = item['rank'] or 'N/A'
            badge_text = item['rankMarkText'] or '-'

            print(f"   {item['index']:<6} {rank:<6} {ad_mark:<6} {rank_mark:<6} {badge_text:<12}")

        print("=" * 60)

        return structure

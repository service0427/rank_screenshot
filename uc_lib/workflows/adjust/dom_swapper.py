"""
DOM 스왑 및 배지 재정렬 모듈

쿠팡 RankMark 배지(1~10위)를 포함한 상품 DOM 스왑 처리
"""

from typing import Dict


class DOMSwapper:
    """DOM 스왑 및 배지 재정렬 전문 클래스"""

    def __init__(self, driver):
        """
        Args:
            driver: Selenium WebDriver 인스턴스
        """
        self.driver = driver

    def swap_products_rank1to10(self, organic_index1: int, organic_index2: int) -> Dict:
        """
        1~10위 범위 상품 DOM 스왑 + 배지 재정렬

        핵심 알고리즘:
        1. 전체 ul > li 배열 저장 (광고 + 일반 모두 포함)
        2. 배지 백업 (RankMark + 커스텀, 원본 노드 유지)
        3. 배지 제거 (DOM에서만)
        4. innerHTML 스왑 (절대 인덱스 사용)
        5. 배지 재정렬하여 복원 (스왑 위치는 교환된 배지 사용)

        Args:
            organic_index1: 첫 번째 일반 상품의 광고 제외 인덱스 (0부터 시작)
            organic_index2: 두 번째 일반 상품의 광고 제외 인덱스 (0부터 시작)

        Returns:
            Dict: 스왑 결과 정보
                - totalItems: 전체 상품 개수
                - organicCount: 일반 상품 개수
                - idx1Absolute: 첫 번째 상품의 절대 인덱스
                - idx2Absolute: 두 번째 상품의 절대 인덱스
                - rank1: 첫 번째 상품의 순위
                - rank2: 두 번째 상품의 순위
                - rankMarkCount: RankMark 배지 개수
                - customBadgeCount: 커스텀 배지 개수
                - restoredCount: 복원된 배지 개수
        """
        print("\n" + "=" * 60)
        print("🔄 DOM 스왑 시작 (배지 재정렬 포함)")
        print("=" * 60)
        print(f"   일반 상품 인덱스: [{organic_index1}] ↔ [{organic_index2}]")

        result = self.driver.execute_async_script("""
            const callback = arguments[arguments.length - 1];
            const idx1Organic = arguments[0];
            const idx2Organic = arguments[1];

            (async function() {
                console.log('');
                console.log('========================================');
                console.log('🔧 STEP 1: 전체 배열 및 매핑');
                console.log('========================================');

            // 1. 전체 ul > li 배열 (광고 + 일반 모두)
            const allItems = Array.from(document.querySelectorAll('#product-list > li[data-id]'));
            console.log('  전체 상품(광고 포함): ' + allItems.length + '개');

            // 2. 일반 상품의 절대 인덱스 매핑
            const organicMappings = [];
            allItems.forEach((item, absoluteIndex) => {
                let link = item.querySelector('a[href*="/vp/products/"]');
                if (!link) link = item.querySelector('a.search-product-link');
                if (!link) return;

                const href = link.getAttribute('href') || '';
                const hasRankParam = href.includes('&rank=') || href.includes('?rank=');
                const hasAdMark = item.querySelector('[class*="AdMark"]') !== null;

                if (hasRankParam && !hasAdMark) {
                    const rankMatch = href.match(/[&?]rank=(\\d+)/);
                    const rank = rankMatch ? parseInt(rankMatch[1]) : 0;
                    organicMappings.push({
                        absoluteIndex: absoluteIndex,
                        organicIndex: organicMappings.length,
                        rank: rank
                    });
                }
            });

            console.log('  일반 상품: ' + organicMappings.length + '개');
            console.log('');

            // 3. 스왑 대상의 절대 인덱스 찾기
            const mapping1 = organicMappings.find(m => m.organicIndex === idx1Organic);
            const mapping2 = organicMappings.find(m => m.organicIndex === idx2Organic);

            if (!mapping1 || !mapping2) {
                throw new Error('스왑 대상을 찾을 수 없습니다');
            }

            const idx1Absolute = mapping1.absoluteIndex;
            const idx2Absolute = mapping2.absoluteIndex;

            console.log('🎯 스왑 대상:');
            console.log('  일반[' + idx1Organic + '] (rank=' + mapping1.rank + ') → 절대[' + idx1Absolute + ']');
            console.log('  일반[' + idx2Organic + '] (rank=' + mapping2.rank + ') → 절대[' + idx2Absolute + ']');
            console.log('');

            // STEP 2: 배지 백업 (원본 노드 유지)
            console.log('========================================');
            console.log('🔧 STEP 2: 배지 백업 (원본 노드 유지)');
            console.log('========================================');
            console.log('');

            const rankMarkBackup = [];
            const customBadgeBackup = [];

            console.log('📋 배지 백업 시작:');
            console.log('');

            allItems.forEach((item, absoluteIndex) => {
                // RankMark span (1~10위 쿠팡 배지) - 원본 노드 제거 후 백업
                const rankMark = item.querySelector('span[class^="RankMark_rank"]');
                if (rankMark) {
                    rankMark.remove();  // DOM에서 제거 (메모리에는 유지됨)
                    rankMarkBackup[absoluteIndex] = rankMark;  // 원본 노드 백업
                    console.log('  ✅ [절대' + absoluteIndex + '] RankMark 백업: "' + rankMark.textContent.trim() + '"');
                } else {
                    rankMarkBackup[absoluteIndex] = null;
                    console.log('  ⚪ [절대' + absoluteIndex + '] RankMark 없음');
                }

                // 커스텀 배지 (11위 이상) - 원본 노드 제거 후 백업
                const customBadge = item.querySelector('.rank-badge');
                if (customBadge) {
                    customBadge.remove();
                    customBadgeBackup[absoluteIndex] = customBadge;
                    console.log('      ✅ 커스텀 배지 백업: "' + customBadge.textContent.trim() + '"');
                } else {
                    customBadgeBackup[absoluteIndex] = null;
                }
            });

            console.log('');
            console.log('  ✅ 배지 백업 완료');
            console.log('      RankMark: ' + rankMarkBackup.filter(b => b).length + '개');
            console.log('      커스텀: ' + customBadgeBackup.filter(b => b).length + '개');
            console.log('');

            // STEP 3: 2초 대기
            console.log('========================================');
            console.log('🔧 STEP 3: 2초 대기 (배지 제거 후 안정화)');
            console.log('========================================');
            await new Promise(resolve => setTimeout(resolve, 2000));
            console.log('  ✅ 2초 대기 완료');
            console.log('');

            // STEP 4: innerHTML 스왑
            console.log('========================================');
            console.log('🔧 STEP 4: innerHTML 스왑');
            console.log('========================================');

            const li1 = allItems[idx1Absolute];
            const li2 = allItems[idx2Absolute];

            if (li1 && li2) {
                const temp = li1.innerHTML;
                li1.innerHTML = li2.innerHTML;
                li2.innerHTML = temp;
                console.log('  ✅ innerHTML 스왑 완료: [절대' + idx1Absolute + '] ↔ [절대' + idx2Absolute + ']');
            } else {
                throw new Error('상품 요소를 찾을 수 없습니다');
            }
            console.log('');

            // STEP 5: 배지 원래 위치 그대로 복원 (innerHTML만 스왑, 배지는 유지)
            console.log('========================================');
            console.log('🔧 STEP 5: 배지 원래 위치로 복원 (자연스럽게)');
            console.log('========================================');
            console.log('');
            console.log('📋 배지 복원 시작 (스왑과 무관하게 원래 위치 유지):');
            console.log('');

            let restoredCount = 0;
            allItems.forEach((item, absoluteIndex) => {
                // ✅ 모든 li에 원래 위치(absoluteIndex) 그대로 배지 복원
                // innerHTML은 스왑되었지만 배지는 원래 순위 유지
                const targetRankMark = rankMarkBackup[absoluteIndex];
                const targetCustomBadge = customBadgeBackup[absoluteIndex];

                if (targetRankMark) {
                    console.log('  ✅ [절대' + absoluteIndex + '] ← RankMark "' + targetRankMark.textContent.trim() + '" (원래 위치 유지)');
                    item.appendChild(targetRankMark);
                    restoredCount++;
                } else {
                    console.log('  ⚪ [절대' + absoluteIndex + '] 배지 없음');
                }

                if (targetCustomBadge) {
                    console.log('      ✅ 커스텀 배지 복원');
                    item.appendChild(targetCustomBadge);
                    restoredCount++;
                }
            });

            console.log('');
            console.log('  ✅ 배지 복원 완료 (복원된 배지: ' + restoredCount + '개)');
            console.log('');

            // STEP 6: 복원 검증 (배지가 정말 복원되었는지 확인)
            console.log('========================================');
            console.log('🔧 STEP 6: 복원 검증');
            console.log('========================================');
            console.log('');

            const verifyMarks = document.querySelectorAll('#product-list span[class^="RankMark_rank"]');
            console.log('📊 복원 후 배지 개수: ' + verifyMarks.length + '개');
            console.log('');

            if (verifyMarks.length > 0) {
                console.log('✅ 복원 성공! 배지 목록:');
                verifyMarks.forEach((mark, index) => {
                    const text = mark.textContent.trim();
                    const parentLi = mark.closest('li[data-id]');
                    const parentIndex = Array.from(document.querySelectorAll('#product-list > li[data-id]')).indexOf(parentLi);
                    console.log('  [' + index + '] "' + text + '" → 절대 인덱스: ' + parentIndex);
                });
            } else {
                console.log('❌ 복원 실패: 배지가 하나도 없습니다!');
                console.log('   🔍 원인 분석:');
                console.log('      1. appendChild가 실패했을 수 있음');
                console.log('      2. 배지가 다른 곳으로 이동했을 수 있음');
                console.log('      3. DOM 구조가 변경되었을 수 있음');
            }
            console.log('');

            // HTML 저장 (디버깅용)
            console.log('💾 HTML 저장 (스왑 후)');
            const htmlAfter = document.documentElement.outerHTML;
            window.__DEBUG_HTML_AFTER = htmlAfter;
            console.log('  window.__DEBUG_HTML_AFTER 저장 완료');
            console.log('');

            console.log('========================================');
            console.log('🎉 DOM 스왑 전체 완료!');
            console.log('========================================');

            // 결과 반환 (검증 포함)
            callback({
                totalItems: allItems.length,
                organicCount: organicMappings.length,
                idx1Absolute: idx1Absolute,
                idx2Absolute: idx2Absolute,
                rank1: mapping1.rank,
                rank2: mapping2.rank,
                rankMarkCount: rankMarkBackup.filter(b => b).length,
                customBadgeCount: customBadgeBackup.filter(b => b).length,
                restoredCount: restoredCount,
                verifiedCount: verifyMarks.length  // 검증: 실제 DOM에서 확인한 배지 개수
            });
            })().catch(err => {
                console.error('❌ DOM 스왑 오류:', err);
                callback({ error: err.message });
            });
        """, organic_index1, organic_index2)

        # 결과 출력
        print("\n" + "📊 DOM 스왑 결과:")
        print(f"   전체 상품: {result['totalItems']}개 (광고 포함)")
        print(f"   일반 상품: {result['organicCount']}개")
        print(f"   스왑 대상:")
        print(f"     - [절대{result['idx1Absolute']}] (rank={result['rank1']}) ↔ [절대{result['idx2Absolute']}] (rank={result['rank2']})")
        print(f"   배지 처리:")
        print(f"     - RankMark: {result['rankMarkCount']}개 백업")
        print(f"     - 커스텀: {result['customBadgeCount']}개 백업")
        print(f"     - appendChild: {result['restoredCount']}번 호출")
        print(f"     - 검증 결과: {result['verifiedCount']}개 배지 확인됨")

        # 검증 결과에 따라 메시지 변경
        if result['verifiedCount'] == result['rankMarkCount'] + result['customBadgeCount']:
            print("✅ DOM 스왑 완료 (배지 복원 성공)")
        elif result['verifiedCount'] > 0:
            print(f"⚠️  DOM 스왑 완료 (일부 배지만 복원: {result['verifiedCount']}/{result['rankMarkCount'] + result['customBadgeCount']})")
        else:
            print("❌ DOM 스왑 완료 (배지 복원 실패: 0개)")

        print("   ℹ️  상세 로그는 브라우저 콘솔(F12)에서 확인하세요")
        print("=" * 60)

        return result

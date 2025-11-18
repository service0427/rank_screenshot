#!/usr/bin/env python3
"""
배지 탐지 테스트 스크립트
실제 브라우저에서 배지가 어떻게 구현되는지 확인
"""

import undetected_chromedriver as uc
import time

# Chrome 옵션
options = uc.ChromeOptions()
options.add_argument('--lang=ko-KR')
options.add_argument('--window-size=1920,1080')
options.add_argument('--disable-blink-features=AutomationControlled')

# 드라이버 시작
driver = uc.Chrome(options=options)

try:
    print("🌐 쿠팡 검색 페이지 접속 중...")
    driver.get("https://www.coupang.com/np/search?q=아이폰17카메라보호필름")
    time.sleep(5)  # 페이지 로드 대기

    print("\n🔍 배지 구조 분석 중...")

    # JavaScript로 배지 분석
    result = driver.execute_script("""
        const allItems = Array.from(document.querySelectorAll('#product-list > li[data-id]'));

        // 일반 상품만 필터링
        const organicProducts = allItems.filter(item => {
            let link = item.querySelector('a[href*="/vp/products/"]');
            if (!link) link = item.querySelector('a.search-product-link');
            if (!link) return false;
            const href = link.getAttribute('href') || '';
            const hasRankParam = href.includes('&rank=') || href.includes('?rank=');
            const hasAdMark = item.querySelector('[class*="AdMark"]') !== null;
            return hasRankParam && !hasAdMark;
        });

        console.log('총 일반 상품:', organicProducts.length);

        // 첫 5개 상품 분석
        const results = [];

        for (let i = 0; i < Math.min(5, organicProducts.length); i++) {
            const item = organicProducts[i];
            const link = item.querySelector('a[href*="/vp/products/"]');
            const href = link ? link.getAttribute('href') : '';
            const rankMatch = href.match(/[&?]rank=(\\d+)/);
            const rank = rankMatch ? rankMatch[1] : 'N/A';

            // 모든 data-* 속성 확인
            const dataAttrs = {};
            for (const attr of item.attributes) {
                if (attr.name.startsWith('data-')) {
                    dataAttrs[attr.name] = attr.value;
                }
            }

            // 모든 자식 요소에서 rank 관련 속성 찾기
            const allElements = item.querySelectorAll('*');
            const rankElements = [];

            allElements.forEach(el => {
                const hasRankAttr = Array.from(el.attributes).some(attr =>
                    attr.name.includes('rank') || attr.value.includes('rank')
                );

                if (hasRankAttr) {
                    const attrs = {};
                    for (const attr of el.attributes) {
                        attrs[attr.name] = attr.value;
                    }
                    rankElements.push({
                        tag: el.tagName.toLowerCase(),
                        attributes: attrs,
                        text: el.textContent.trim().slice(0, 50)
                    });
                }
            });

            // 숫자만 포함하는 짧은 요소 찾기
            const numberElements = [];
            allElements.forEach(el => {
                const text = el.textContent.trim();
                if (text.length <= 3 && /^\\d+$/.test(text)) {
                    const computed = window.getComputedStyle(el);
                    numberElements.push({
                        tag: el.tagName.toLowerCase(),
                        class: el.className,
                        text: text,
                        position: computed.position,
                        display: computed.display,
                        backgroundColor: computed.backgroundColor,
                        color: computed.color,
                        zIndex: computed.zIndex
                    });
                }
            });

            results.push({
                index: i,
                rank: rank,
                dataId: item.getAttribute('data-id'),
                dataAttrs: dataAttrs,
                rankElements: rankElements,
                numberElements: numberElements
            });
        }

        return results;
    """)

    import json
    print("\n" + "=" * 60)
    print("📊 분석 결과:")
    print("=" * 60)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("=" * 60)

    print("\n⏸️  브라우저를 10초간 유지합니다. 수동으로 확인하세요...")
    time.sleep(10)

finally:
    driver.quit()
    print("✅ 테스트 완료")

#!/usr/bin/env python3
"""
시각적 디버깅 헬퍼 모듈
모든 상품에 순위 테두리를 표시하고 전체 페이지 스크린샷 캡처
"""

from typing import List, Dict
from selenium.webdriver.remote.webelement import WebElement


class VisualDebugHelper:
    """시각적 디버깅을 위한 헬퍼 클래스"""

    def __init__(self, driver):
        """
        Args:
            driver: Selenium WebDriver 인스턴스
        """
        self.driver = driver
        self._applied_styles = []  # 적용한 스타일 추적

    def apply_rank_borders(
        self,
        organic_products: List[WebElement],
        organic_dom_indices: List[int]
    ) -> bool:
        """
        모든 일반 상품에 순위별 색상 테두리 적용

        Args:
            organic_products: 광고 제외 제품 리스트
            organic_dom_indices: 광고 제외 제품의 DOM 인덱스

        Returns:
            성공 여부
        """
        try:
            print(f"\n🎨 순위별 테두리 적용 중...")

            # 순위별 색상 정의
            colors = [
                "#FF0000",  # 1등: 빨강
                "#FF7F00",  # 2등: 주황
                "#FFFF00",  # 3등: 노랑
                "#00FF00",  # 4등: 초록
                "#0000FF",  # 5등: 파랑
                "#4B0082",  # 6등: 남색
                "#9400D3",  # 7등: 보라
                "#FF1493",  # 8등: 핑크
                "#00FFFF",  # 9등: 청록
                "#FF00FF",  # 10등: 자주
            ]

            for rank, (product, dom_index) in enumerate(zip(organic_products, organic_dom_indices), start=1):
                # 1~10등은 고유 색상, 11등 이후는 회색
                if rank <= 10:
                    color = colors[rank - 1]
                    border_width = "5px"
                else:
                    color = "#808080"  # 회색
                    border_width = "3px"

                # 테두리 적용 (outline 사용 - 레이아웃에 영향 없음)
                self.driver.execute_script(f"""
                    arguments[0].style.outline = '{border_width} solid {color}';
                    arguments[0].style.outlineOffset = '-{border_width}';  // 안쪽으로
                    arguments[0].style.position = 'relative';

                    // 순위 배지 추가
                    var badge = document.createElement('div');
                    badge.textContent = '{rank}등';
                    badge.style.position = 'absolute';
                    badge.style.top = '5px';
                    badge.style.left = '5px';
                    badge.style.backgroundColor = '{color}';
                    badge.style.color = 'white';
                    badge.style.padding = '5px 10px';
                    badge.style.fontWeight = 'bold';
                    badge.style.fontSize = '14px';
                    badge.style.borderRadius = '5px';
                    badge.style.zIndex = '9999';
                    badge.className = 'debug-rank-badge';

                    arguments[0].appendChild(badge);
                """, product)

                self._applied_styles.append(product)

                if rank <= 15:  # 처음 15개만 출력
                    print(f"   ✓ {rank}등: {color} 테두리 적용 (DOM[{dom_index}])")

            print(f"✅ 총 {len(organic_products)}개 상품에 테두리 적용 완료")
            return True

        except Exception as e:
            print(f"❌ 테두리 적용 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def remove_rank_borders(self) -> bool:
        """
        적용한 테두리 제거

        Returns:
            성공 여부
        """
        try:
            if not self._applied_styles:
                return True

            print(f"\n🧹 테두리 제거 중...")

            for product in self._applied_styles:
                try:
                    self.driver.execute_script("""
                        arguments[0].style.outline = '';
                        arguments[0].style.outlineOffset = '';

                        // 배지 제거
                        var badges = arguments[0].querySelectorAll('.debug-rank-badge');
                        badges.forEach(function(badge) {
                            badge.remove();
                        });
                    """, product)
                except:
                    pass  # Stale element 무시

            self._applied_styles = []
            print(f"✅ 테두리 제거 완료")
            return True

        except Exception as e:
            print(f"⚠️  테두리 제거 실패: {e}")
            self._applied_styles = []
            return False

    def highlight_ad_positions(self, all_items: List[WebElement], items_info: List[Dict]) -> bool:
        """
        광고 위치를 별도 색상으로 강조

        Args:
            all_items: 전체 li 요소
            items_info: 각 항목 정보

        Returns:
            성공 여부
        """
        try:
            print(f"\n📢 광고 위치 강조 중...")

            ad_count = 0
            for idx, info in enumerate(items_info):
                if info["is_ad"] and idx < len(all_items):
                    item = all_items[idx]

                    self.driver.execute_script("""
                        // outline 사용 (레이아웃 영향 없음)
                        arguments[0].style.outline = '5px dashed #FF0000';
                        arguments[0].style.outlineOffset = '-5px';  // 안쪽으로
                        arguments[0].style.backgroundColor = 'rgba(255, 0, 0, 0.1)';

                        // 광고 배지 추가
                        var badge = document.createElement('div');
                        badge.textContent = '광고';
                        badge.style.position = 'absolute';
                        badge.style.top = '5px';
                        badge.style.right = '5px';
                        badge.style.backgroundColor = '#FF0000';
                        badge.style.color = 'white';
                        badge.style.padding = '5px 10px';
                        badge.style.fontWeight = 'bold';
                        badge.style.fontSize = '14px';
                        badge.style.borderRadius = '5px';
                        badge.style.zIndex = '9999';
                        badge.className = 'debug-ad-badge';

                        arguments[0].style.position = 'relative';
                        arguments[0].appendChild(badge);
                    """, item)

                    ad_count += 1
                    print(f"   ✓ 광고 위치 강조: DOM[{idx}]")

            print(f"✅ 총 {ad_count}개 광고 강조 완료")
            return True

        except Exception as e:
            print(f"❌ 광고 강조 실패: {e}")
            return False

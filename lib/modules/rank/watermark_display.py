#!/usr/bin/env python3
"""
워터마크 표시 모듈 (정상 검색용)
10위권 밖의 상품에 순위 워터마크를 표시
"""

from typing import List, Dict
from selenium.webdriver.remote.webelement import WebElement
from lib.constants import Config


class WatermarkDisplay:
    """10위권 밖 상품에 순위 워터마크를 표시하는 클래스"""

    def __init__(self, driver):
        """
        Args:
            driver: Selenium WebDriver 인스턴스
        """
        self.driver = driver

    def display_watermarks_for_page(
        self,
        all_items: List[WebElement],
        items_info: List[Dict],
        rank_offset: int = 0
    ) -> bool:
        """
        현재 페이지의 11등 이상 상품에 워터마크 표시

        Args:
            all_items: 전체 li 요소 리스트 (광고 포함)
            items_info: 각 항목의 정보 (is_ad, dom_index, rank)
            rank_offset: 누적 순위 오프셋 (이전 페이지들의 상품 개수, 기본: 0)

        Returns:
            성공 여부
        """
        try:
            print(f"\n🏷️  순위 워터마크 표시 중...")
            print(f"   이전 페이지 상품 수: {rank_offset}개")

            # 일반 상품만 필터링
            organics = []
            organic_ranks = []

            for idx, info in enumerate(items_info):
                if not info["is_ad"]:
                    organics.append(all_items[idx])
                    # 전체 누적 순위 계산
                    page_rank = info["rank"]  # 페이지 내 순위 (1, 2, 3, ...)
                    cumulative_rank = rank_offset + page_rank
                    organic_ranks.append(cumulative_rank)

            print(f"   일반 상품: {len(organics)}개")
            if organics:
                print(f"   순위 범위: {organic_ranks[0]}~{organic_ranks[-1]}등")

            # MIN_RANK 이상의 상품에만 워터마크 추가
            watermark_count = 0
            for item, rank in zip(organics, organic_ranks):
                if rank >= Config.WATERMARK_MIN_RANK:  # 전역 설정 사용
                    success = self._add_watermark(item, rank)
                    if success:
                        watermark_count += 1

            if watermark_count > 0:
                print(f"   ✓ {watermark_count}개 워터마크 표시 완료")
            else:
                print(f"   ℹ️  10위권 밖의 상품 없음 (워터마크 표시 안 함)")

            return True

        except Exception as e:
            print(f"❌ 워터마크 표시 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _add_watermark(self, item: WebElement, rank: int) -> bool:
        """
        개별 상품에 워터마크 추가

        Args:
            item: 상품 요소
            rank: 순위 (전체 누적 순위)

        Returns:
            성공 여부
        """
        try:
            # 전역 설정을 사용하여 워터마크 생성
            script = f"""
                var rank = arguments[1];

                // 워터마크 컨테이너 찾기
                var container = arguments[0].querySelector('.search-product');
                if (!container) {{
                    container = arguments[0];
                }}

                // 워터마크 요소 생성
                var mark = document.createElement('span');
                mark.className = 'RankMark_rank' + rank + '__custom';
                mark.textContent = rank;

                // 전역 설정 기반 스타일 적용
                mark.style.position = 'absolute';
                mark.style.top = '{Config.WATERMARK_POSITION_TOP}';
                mark.style.right = '{Config.WATERMARK_POSITION_RIGHT}';
                mark.style.backgroundColor = '{Config.WATERMARK_BG_COLOR}';
                mark.style.color = '{Config.WATERMARK_TEXT_COLOR}';
                mark.style.padding = '{Config.WATERMARK_PADDING}';
                mark.style.fontSize = '{Config.WATERMARK_FONT_SIZE}';
                mark.style.fontWeight = '{Config.WATERMARK_FONT_WEIGHT}';
                mark.style.borderRadius = '{Config.WATERMARK_BORDER_RADIUS}';
                mark.style.zIndex = '{Config.WATERMARK_Z_INDEX}';
                mark.style.fontFamily = '{Config.WATERMARK_FONT_FAMILY}';
                mark.style.lineHeight = '{Config.WATERMARK_LINE_HEIGHT}';

                // 컨테이너 position 설정
                if (container.style.position !== 'relative' &&
                    container.style.position !== 'absolute') {{
                    container.style.position = 'relative';
                }}

                // 워터마크 추가
                container.appendChild(mark);
            """
            self.driver.execute_script(script, item, rank)

            return True

        except Exception as e:
            # 개별 상품 처리 실패는 무시
            return False

    def remove_all_watermarks(self, all_items: List[WebElement]) -> bool:
        """
        모든 워터마크 제거 (우리가 생성한 워터마크만)

        Args:
            all_items: 전체 li 요소 리스트

        Returns:
            성공 여부
        """
        try:
            print(f"\n🧹 워터마크 제거 중...")

            removed_count = 0
            for item in all_items:
                try:
                    # 우리가 생성한 워터마크만 제거
                    result = self.driver.execute_script("""
                        var marks = arguments[0].querySelectorAll('[class*="RankMark"][class*="__custom"]');
                        if (marks.length > 0) {
                            marks.forEach(function(mark) {
                                mark.remove();
                            });
                            return marks.length;
                        }
                        return 0;
                    """, item)

                    if result > 0:
                        removed_count += 1

                except Exception:
                    pass

            if removed_count > 0:
                print(f"   ✓ {removed_count}개 워터마크 제거 완료")
            else:
                print(f"   ℹ️  제거할 워터마크 없음")

            return True

        except Exception as e:
            print(f"❌ 워터마크 제거 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

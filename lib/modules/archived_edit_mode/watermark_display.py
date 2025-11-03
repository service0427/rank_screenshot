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
        rank_offset: int = 0,
        target_product_info: Dict = None
    ) -> bool:
        """
        타겟 상품(매칭된 상품)에만 워터마크 표시 (11등 이상)

        Args:
            all_items: 전체 li 요소 리스트 (광고 포함)
            items_info: 각 항목의 정보 (is_ad, dom_index, rank, product_id, item_id, vendor_item_id)
            rank_offset: 누적 순위 오프셋 (이전 페이지들의 상품 개수, 기본: 0)
            target_product_info: 타겟 상품 정보 (product_id, item_id, vendor_item_id)

        Returns:
            성공 여부
        """
        try:
            # 전역 설정 체크: 워터마크 표시 비활성화 시 스킵
            if not Config.ENABLE_WATERMARK_DISPLAY:
                print(f"\n   ℹ️  타겟 워터마크 표시 비활성화 (Config.ENABLE_WATERMARK_DISPLAY=False)")
                return True

            # 타겟 상품 정보가 없으면 스킵
            if not target_product_info:
                print(f"\n   ℹ️  타겟 상품 정보 없음 - 워터마크 표시 스킵")
                return True

            print(f"\n🏷️  타겟 상품 워터마크 표시 중...")

            # 타겟 상품 찾기
            target_product_id = target_product_info.get('product_id')
            target_item_id = target_product_info.get('item_id')
            target_vendor_item_id = target_product_info.get('vendor_item_id')

            target_found = False
            for idx, info in enumerate(items_info):
                # 광고 상품은 스킵
                if info.get("is_ad"):
                    continue

                # 타겟 상품 매칭 (product_id, item_id, vendor_item_id 중 하나라도 일치)
                is_target = False
                if target_product_id and info.get("product_id") == target_product_id:
                    is_target = True
                elif target_item_id and info.get("item_id") == target_item_id:
                    is_target = True
                elif target_vendor_item_id and info.get("vendor_item_id") == target_vendor_item_id:
                    is_target = True

                if is_target:
                    # 누적 순위 계산
                    page_rank = int(info["rank"]) if info["rank"] is not None else 0
                    cumulative_rank = int(rank_offset) + page_rank

                    # 11등 이상만 워터마크 표시
                    if cumulative_rank >= Config.WATERMARK_MIN_RANK:
                        success = self._add_watermark(all_items[idx], cumulative_rank)
                        if success:
                            print(f"   ✓ 타겟 상품 워터마크 표시 완료 (순위: {cumulative_rank}등)")
                            target_found = True
                    else:
                        print(f"   ℹ️  타겟 상품 {cumulative_rank}등 - 워터마크 표시 안 함 (11등 이상만 표시)")
                        target_found = True
                    break

            if not target_found:
                print(f"   ℹ️  현재 페이지에서 타겟 상품 미발견")

            return True

        except Exception as e:
            print(f"❌ 워터마크 표시 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _add_watermark(self, item: WebElement, rank: int) -> bool:
        """
        타겟 상품에 워터마크 추가

        Args:
            item: 상품 요소
            rank: 순위 (전체 누적 순위)

        Returns:
            성공 여부
        """
        try:
            # 타겟 상품 스타일 적용
            bg_color = Config.WATERMARK_BG_COLOR
            text_color = Config.WATERMARK_TEXT_COLOR
            border = Config.WATERMARK_BORDER
            font_size = Config.WATERMARK_FONT_SIZE
            padding = Config.WATERMARK_PADDING
            position_top = Config.WATERMARK_POSITION_TOP
            position_left = Config.WATERMARK_POSITION_LEFT
            position_right = Config.WATERMARK_POSITION_RIGHT

            # 전역 설정을 사용하여 워터마크 생성
            # 위치 설정 JavaScript 코드 동적 생성
            position_style = f"mark.style.top = '{position_top}';"

            if position_left:
                position_style += f"\n                mark.style.left = '{position_left}';"
                # 좌측 세로 중앙 정렬 (transform: translateY(-50%))
                if position_top == "50%":
                    position_style += "\n                mark.style.transform = 'translateY(-50%)';"

            if position_right:
                position_style += f"\n                mark.style.right = '{position_right}';"

            script = f"""
                var rank = arguments[1];

                // 워터마크 컨테이너 찾기
                var container = arguments[0].querySelector('.search-product');
                if (!container) {{
                    container = arguments[0];
                }}

                // 워터마크 요소 생성
                var mark = document.createElement('span');
                mark.className = 'RankMark_rank' + String(rank) + '__custom';
                mark.textContent = String(rank);

                // 전역 설정 기반 스타일 적용
                mark.style.position = 'absolute';
                {position_style}
                mark.style.backgroundColor = '{bg_color}';
                mark.style.color = '{text_color}';
                mark.style.padding = '{padding}';
                mark.style.fontSize = '{font_size}';
                mark.style.fontWeight = '{Config.WATERMARK_FONT_WEIGHT}';
                mark.style.borderRadius = '{Config.WATERMARK_BORDER_RADIUS}';
                mark.style.zIndex = '{Config.WATERMARK_Z_INDEX}';
                mark.style.fontFamily = '{Config.WATERMARK_FONT_FAMILY}';
                mark.style.lineHeight = '{Config.WATERMARK_LINE_HEIGHT}';
                mark.style.border = '{border}';

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
            # 개별 상품 처리 실패 - 디버깅용 로그 출력
            print(f"      ⚠️  워터마크 추가 실패 (순위 {rank}등): {e}")
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

#!/usr/bin/env python3
"""
순위 워터마크 관리 모듈
1~10등 워터마크 제거 및 재생성
"""

from typing import List
from selenium.webdriver.remote.webelement import WebElement


class WatermarkManager:
    """순위 워터마크를 관리하는 클래스"""

    def __init__(self, driver):
        """
        Args:
            driver: Selenium WebDriver 인스턴스
        """
        self.driver = driver

    def remove_watermarks(self, items: List[WebElement], count: int = 10) -> bool:
        """
        1~N등의 워터마크 완전 제거

        Args:
            items: 일반 상품 요소 리스트
            count: 제거할 워터마크 개수 (기본: 10)

        Returns:
            성공 여부
        """
        try:
            print(f"\n🧹 순위 워터마크 제거 중 (1~{count}등)...")

            removed_count = 0
            for idx in range(min(count, len(items))):
                item = items[idx]
                try:
                    # 워터마크 요소 찾아서 제거
                    result = self.driver.execute_script("""
                        var marks = arguments[0].querySelectorAll('[class*="RankMark"]');
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

                except Exception as e:
                    # 개별 요소 처리 실패는 무시
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

    def recreate_watermarks(self, items: List[WebElement], count: int = 10) -> bool:
        """
        1~N등의 워터마크 재생성

        Note:
            실제 쿠팡 워터마크 구조를 분석하여 동일하게 재생성해야 함
            현재는 간단한 구조로 구현 (필요시 수정 가능)

        Args:
            items: 일반 상품 요소 리스트
            count: 재생성할 워터마크 개수 (기본: 10)

        Returns:
            성공 여부
        """
        try:
            print(f"\n🏷️  순위 워터마크 재생성 중 (1~{count}등)...")

            created_count = 0
            for rank in range(1, min(count + 1, len(items) + 1)):
                item = items[rank - 1]

                try:
                    # 워터마크 재생성
                    # TODO: 실제 쿠팡 워터마크 구조에 맞춰 수정 필요
                    self.driver.execute_script("""
                        var rank = arguments[1];

                        // 워터마크 컨테이너 찾기 (또는 생성)
                        var container = arguments[0].querySelector('.search-product');
                        if (!container) {
                            container = arguments[0];
                        }

                        // 워터마크 요소 생성
                        var mark = document.createElement('span');
                        mark.className = 'RankMark_rank' + rank + '__custom';
                        mark.textContent = rank;
                        mark.style.position = 'absolute';
                        mark.style.top = '10px';
                        mark.style.left = '10px';
                        mark.style.backgroundColor = '#FF6B00';
                        mark.style.color = 'white';
                        mark.style.padding = '4px 8px';
                        mark.style.fontSize = '12px';
                        mark.style.fontWeight = 'bold';
                        mark.style.borderRadius = '4px';
                        mark.style.zIndex = '10';

                        // 컨테이너 position 설정
                        if (container.style.position !== 'relative' &&
                            container.style.position !== 'absolute') {
                            container.style.position = 'relative';
                        }

                        // 워터마크 추가
                        container.appendChild(mark);
                    """, item, rank)

                    created_count += 1

                except Exception as e:
                    print(f"   ⚠️  {rank}등 워터마크 생성 실패: {e}")

            if created_count > 0:
                print(f"   ✓ {created_count}개 워터마크 생성 완료")
            else:
                print(f"   ⚠️  생성된 워터마크 없음")

            return True

        except Exception as e:
            print(f"❌ 워터마크 재생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_watermark(self, item: WebElement, rank: int) -> bool:
        """
        단일 워터마크 업데이트 (textContent 변경 방식)

        Note:
            간단한 업데이트용. 전체 재정렬 시에는 remove + recreate 권장

        Args:
            item: 상품 요소
            rank: 새로운 순위

        Returns:
            성공 여부
        """
        try:
            # 워터마크 요소 찾기
            mark = item.find_element("css selector", '[class*="RankMark"]')

            # textContent 변경
            self.driver.execute_script("""
                arguments[0].textContent = arguments[1];
            """, mark, str(rank))

            return True

        except Exception:
            # 워터마크 없는 경우 (정상)
            return False

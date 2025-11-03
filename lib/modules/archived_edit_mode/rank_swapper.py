#!/usr/bin/env python3
"""
상품 순위 변경 모듈 (Simple Swap 방식)
두 상품의 위치만 교환하는 단순하고 안정적인 알고리즘
"""

import time
from typing import Optional, Dict, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from lib.modules.rank.watermark_manager import WatermarkManager


class RankSwapper:
    """Simple Swap 방식으로 상품 순위를 변경하는 클래스"""

    def __init__(self, driver, finder):
        """
        Args:
            driver: Selenium WebDriver 인스턴스
            finder: ProductFinder 인스턴스
        """
        self.driver = driver
        self.finder = finder
        self.watermark_manager = WatermarkManager(driver)

    def find_organic_product_by_rank(self, target_rank: int) -> Optional[Tuple[WebElement, int]]:
        """
        광고를 제외한 순수 순위로 상품 찾기

        ⚠️  중요: finder.analyze_product_list_structure()를 재사용하여
        RankManipulator와 동일한 상품 목록을 사용

        Args:
            target_rank: 찾을 순위 (광고 제외, 1부터 시작)

        Returns:
            (WebElement, DOM index) 또는 None
        """
        try:
            # finder의 메서드를 사용하여 일관성 유지
            structure = self.finder.analyze_product_list_structure()
            organic_products = structure['organic_products']  # WebElement 리스트

            print(f"   🔍 일반 상품: {len(organic_products)}개")

            if target_rank < 1 or target_rank > len(organic_products):
                print(f"   ❌ {target_rank}등 상품을 찾을 수 없습니다 (일반 상품 총 {len(organic_products)}개)")
                return None

            # target_rank는 1-based, 리스트 인덱스는 0-based
            target_element = organic_products[target_rank - 1]

            # DOM index 계산 (전체 li 중에서의 위치)
            all_items = structure['all_items']
            dom_idx = -1
            for idx, item in enumerate(all_items):
                if item == target_element:
                    dom_idx = idx
                    break

            if dom_idx >= 0:
                print(f"   ✅ {target_rank}등 상품 발견 (DOM index: {dom_idx})")
                return (target_element, dom_idx)
            else:
                print(f"   ❌ DOM index를 찾을 수 없습니다")
                return None

        except Exception as e:
            print(f"   ❌ 상품 찾기 실패: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _is_ad_or_special(self, element: WebElement) -> bool:
        """
        광고 또는 특수 섹션 여부 확인

        Args:
            element: 검사할 li 요소

        Returns:
            True: 광고/특수 섹션, False: 일반 상품
        """
        try:
            # 1. data-ad-id 속성 체크 (광고)
            ad_id = element.get_attribute('data-ad-id')
            if ad_id:
                return True

            # 2. class 기반 특수 섹션 감지
            element_class = element.get_attribute('class') or ''
            special_keywords = [
                'best-seller',
                'limited-time-offer',
                'time-deal',
                'special-offer',
                'promotion'
            ]

            for keyword in special_keywords:
                if keyword in element_class.lower():
                    return True

            # 3. 상품 링크 없으면 특수 섹션
            links = element.find_elements(By.CSS_SELECTOR, "a[href*='/vp/products/']")
            if not links:
                # 추가 검증: 상품명 요소가 있는지 확인
                name_elements = element.find_elements(By.CSS_SELECTOR, "div[class*='name'], div[class*='title']")
                if not name_elements:
                    return True  # 링크도 없고 상품명도 없으면 특수 섹션

            return False

        except Exception:
            # 에러 발생 시 안전하게 일반 상품으로 간주
            return False

    def move_product_to_rank(
        self,
        target_product: Dict,
        desired_rank: int,
        all_products: list
    ) -> tuple:
        """
        상품을 원하는 순위로 이동 (Simple Swap 방식)

        RankManipulator와의 호환성을 위한 인터페이스 메서드

        Args:
            target_product: 이동할 상품 정보 (rank 포함)
            desired_rank: 목표 순위
            all_products: 전체 상품 목록 (사용하지 않음, 호환성을 위해 존재)

        Returns:
            (success: bool, error_msg: Optional[str])
        """
        current_rank = target_product.get('rank')

        if not current_rank:
            return (False, "상품의 현재 순위 정보가 없습니다")

        if current_rank == desired_rank:
            return (True, None)  # 이미 목표 순위

        # Simple Swap 실행
        result = self.swap_products_simple(current_rank, desired_rank)

        if result["success"]:
            return (True, None)
        else:
            return (False, result["message"])

    def swap_products_simple(
        self,
        rank_a: int,
        rank_b: int
    ) -> Dict:
        """
        두 상품의 위치를 교환 (Simple Swap)

        광고와 특수 섹션은 완전히 무시하고,
        두 일반 상품의 DOM 위치만 교환함

        Args:
            rank_a: 첫 번째 상품의 순위 (광고 제외)
            rank_b: 두 번째 상품의 순위 (광고 제외)

        Returns:
            {
                "success": bool,
                "message": str
            }
        """
        try:
            print(f"\n🔄 Simple Swap 시작: {rank_a}등 ↔ {rank_b}등")

            # 1. 두 상품 찾기
            result_a = self.find_organic_product_by_rank(rank_a)
            result_b = self.find_organic_product_by_rank(rank_b)

            if not result_a or not result_b:
                return {
                    "success": False,
                    "message": f"상품을 찾을 수 없습니다 (rank_a={rank_a}, rank_b={rank_b})"
                }

            product_a, dom_idx_a = result_a
            product_b, dom_idx_b = result_b

            print(f"   ✓ {rank_a}등 (DOM {dom_idx_a}) 찾기 완료")
            print(f"   ✓ {rank_b}등 (DOM {dom_idx_b}) 찾기 완료")

            # 2. 워터마크 백업 및 제거 (1페이지 규칙)
            structure = self.finder.analyze_product_list_structure()
            organic_elements = structure['organic_products']

            # watermark_manager를 사용하여 백업 및 제거
            self.watermark_manager.backup_and_remove(organic_elements, count=10)

            # 3. 내용 복제 및 교환 (워터마크 없는 상태로 swap)
            print(f"\n   🔀 상품 내용 교환 중 (innerHTML swap)...")
            self.driver.execute_script("""
                var elementA = arguments[0];  // rank_a 위치의 li
                var elementB = arguments[1];  // rank_b 위치의 li

                console.log('Before swap - A:', elementA.className, 'B:', elementB.className);

                // Step 1: 두 요소의 innerHTML 백업
                var contentA = elementA.innerHTML;
                var contentB = elementB.innerHTML;

                console.log('Backup complete - A length:', contentA.length, 'B length:', contentB.length);

                // Step 2: 내용 교환 (li 요소는 그대로, 내용만 바뀜)
                elementA.innerHTML = contentB;  // A 위치에 B 내용
                elementB.innerHTML = contentA;  // B 위치에 A 내용

                console.log('Swap complete - A innerHTML:', elementA.innerHTML.substring(0, 50));
                console.log('Swap complete - B innerHTML:', elementB.innerHTML.substring(0, 50));
            """, product_a, product_b)

            time.sleep(0.3)  # DOM 안정화 대기
            print(f"      ✓ 상품 내용 교환 완료")

            # 4. 워터마크 재생성 (위치 기준으로 1~10)
            # DOM에서 현재 상품 목록 다시 가져오기 (swap 후)
            structure = self.finder.analyze_product_list_structure()
            organic_elements_after = structure['organic_products']

            # watermark_manager를 사용하여 롤백
            self.watermark_manager.restore(organic_elements_after, count=10)

            print(f"\n✅ Simple Swap 완료: {rank_a}등 ↔ {rank_b}등")
            return {
                "success": True,
                "message": f"{rank_a}등과 {rank_b}등의 위치가 교환되었습니다"
            }

        except Exception as e:
            print(f"❌ Simple Swap 실패: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"교환 중 오류 발생: {e}"
            }

    def verify_new_order(self, expected_order: list) -> list:
        """
        순위 변경 후 상품 순서 확인 및 현재 상품 목록 반환

        Args:
            expected_order: 기대하는 상품 순서 (사용하지 않음)

        Returns:
            현재 DOM의 상품 정보 리스트
        """
        try:
            print(f"\n🔍 재배치 후 순서 확인 중...")

            # DOM에서 현재 순서대로 상품 요소들 다시 가져오기
            structure = self.finder.analyze_product_list_structure()
            new_organic_products_elements = structure['organic_products']

            # WebElement 리스트를 딕셔너리 리스트로 변환
            new_organic_products = self.finder.extract_all_products_params(new_organic_products_elements)

            print(f"✅ 재배치 확인 완료: {len(new_organic_products)}개 일반 상품\n")

            return new_organic_products

        except Exception as e:
            print(f"❌ 재배치 확인 실패: {e}")
            import traceback
            traceback.print_exc()
            return expected_order

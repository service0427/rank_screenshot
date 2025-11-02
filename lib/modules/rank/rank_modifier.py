#!/usr/bin/env python3
"""
상품 순위 변경 모듈 (배열 재정렬 방식)
광고는 원래 위치 유지, 일반 상품만 재정렬
"""

import time
from typing import List, Dict, Optional
from selenium.webdriver.remote.webelement import WebElement
from .watermark_manager import WatermarkManager


class RankModifier:
    """상품 순위를 배열 재정렬 방식으로 변경하는 클래스"""

    def __init__(self, driver):
        """
        Args:
            driver: Selenium WebDriver 인스턴스
        """
        self.driver = driver
        self.watermark_manager = WatermarkManager(driver)

    def rearrange_products_by_rank(
        self,
        all_items: List[WebElement],
        items_info: List[Dict],
        source_rank: int,
        target_rank: int
    ) -> Dict:
        """
        배열 재정렬 방식으로 순위 변경
        광고는 원래 DOM 인덱스 유지, 일반 상품만 재정렬

        예: 광고,1,2,3,광고,4,5,...,15
        → 광고,1,2,(15),광고,3,4,...,14  (광고 위치 완전 유지)

        Args:
            all_items: 전체 li 요소 리스트 (광고 포함)
            items_info: 각 항목의 정보 (is_ad, dom_index, rank)
            source_rank: 원본 순위 (예: 15, 광고 제외 순위)
            target_rank: 목표 순위 (예: 3, 광고 제외 순위)

        Returns:
            {
                "success": bool,
                "new_organic_products": List[WebElement],  # 재정렬된 일반 상품
                "new_organic_dom_indices": List[int]        # 새로운 DOM 인덱스
            }
        """
        try:
            print(f"\n🔄 배열 재정렬 방식으로 순위 변경 중...")
            print(f"   {source_rank}등 상품 → {target_rank}등 자리로 이동")

            # 1. 광고와 일반 상품 분류
            ads = {}  # {original_dom_index: WebElement}
            organics = []  # [WebElement, WebElement, ...]
            organic_indices = []  # 원본 DOM 인덱스 추적

            for idx, info in enumerate(items_info):
                if info["is_ad"]:
                    ads[idx] = all_items[idx]
                else:
                    organics.append(all_items[idx])
                    organic_indices.append(idx)

            print(f"   ✓ 분류 완료: 일반 {len(organics)}개, 광고 {len(ads)}개")

            # 2. 일반 상품 재정렬
            if source_rank < 1 or source_rank > len(organics):
                print(f"❌ 원본 순위 {source_rank}가 범위를 벗어났습니다 (1~{len(organics)})")
                return {"success": False}

            if target_rank < 1 or target_rank > len(organics):
                print(f"❌ 목표 순위 {target_rank}가 범위를 벗어났습니다 (1~{len(organics)})")
                return {"success": False}

            if source_rank == target_rank:
                print(f"⚠️  원본과 목표 순위가 동일합니다 ({source_rank}등)")
                return {"success": True, "new_organic_products": organics, "new_organic_dom_indices": organic_indices}

            # 배열 재정렬
            source_item = organics.pop(source_rank - 1)  # source_rank 상품 제거
            organics.insert(target_rank - 1, source_item)  # target_rank 위치에 삽입

            print(f"   ✓ 배열 재정렬 완료")

            # 3. 워터마크 완전 제거 (1~10등)
            self.watermark_manager.remove_watermarks(organics, count=10)

            # 4. DOM 완전 재구성
            print(f"\n   🏗️  DOM 재구성 중...")
            self._reconstruct_dom(ads, organics, len(all_items))

            # DOM 변경 후 렌더링 대기
            time.sleep(0.5)

            # 5. Fresh 요소 다시 조회
            print(f"\n   🔄 재구성된 DOM 요소 조회 중...")
            fresh_all_items = self.driver.find_elements("css selector", "#product-list > li[data-id]")
            if not fresh_all_items:
                fresh_all_items = self.driver.find_elements("css selector", "#product-list > li")

            print(f"      - 조회된 요소 개수: {len(fresh_all_items)}")

            # 6. 새로운 organic 요소 및 DOM 인덱스 추출
            fresh_organics = []
            fresh_organic_dom_indices = []

            organic_idx = 0
            for dom_idx in range(len(fresh_all_items)):
                if dom_idx in ads:
                    # 광고는 skip
                    continue
                else:
                    fresh_organics.append(fresh_all_items[dom_idx])
                    fresh_organic_dom_indices.append(dom_idx)
                    organic_idx += 1

            print(f"      - 일반 상품: {len(fresh_organics)}개")
            print(f"      - 광고: {len(fresh_all_items) - len(fresh_organics)}개")

            # 7. 워터마크 재생성 (1~10등)
            self.watermark_manager.recreate_watermarks(fresh_organics, count=10)

            print(f"\n✅ 순위 변경 완료:")
            print(f"   • {source_rank}등 → {target_rank}등 위치")
            print(f"   • 광고 위치: 원래 위치 완전 유지")
            print(f"   • 워터마크: 1~10등 재생성 완료")

            return {
                "success": True,
                "new_organic_products": fresh_organics,
                "new_organic_dom_indices": fresh_organic_dom_indices
            }

        except Exception as e:
            print(f"❌ 순위 변경 실패: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False}

    def _reconstruct_dom(
        self,
        ads: Dict[int, WebElement],
        organics: List[WebElement],
        total_count: int
    ):
        """
        DOM을 완전히 재구성
        광고는 원래 위치, 일반 상품은 재정렬된 순서로 배치

        Args:
            ads: {original_dom_index: WebElement} 광고 딕셔너리
            organics: 재정렬된 일반 상품 리스트
            total_count: 전체 요소 개수
        """
        try:
            # 부모 컨테이너 찾기
            parent = self.driver.find_element("css selector", "#product-list")

            # 전체 비우기 (innerHTML = "")
            self.driver.execute_script("""
                arguments[0].innerHTML = '';
            """, parent)

            print(f"      - 기존 DOM 완전히 비움")

            # 재구성 전략:
            # 1단계: 일반 상품을 먼저 모두 추가 (appendChild)
            # 2단계: 광고를 원래 위치에 삽입 (insertBefore)

            # 1단계: 일반 상품 먼저 추가
            for organic_element in organics:
                self.driver.execute_script("""
                    arguments[0].appendChild(arguments[1]);
                """, parent, organic_element)

            print(f"      - 1단계: 일반 상품 {len(organics)}개 추가 완료")

            # 2단계: 광고를 원래 위치에 삽입
            # 광고 위치를 DOM 인덱스 기준으로 정렬 (앞에서부터 삽입)
            sorted_ad_positions = sorted(ads.keys())

            for ad_dom_idx in sorted_ad_positions:
                ad_element = ads[ad_dom_idx]

                # 현재 parent의 자식 요소 조회
                current_children = self.driver.execute_script("""
                    return arguments[0].children;
                """, parent)

                # 삽입 위치 계산
                # ad_dom_idx가 원래 위치, 하지만 이미 삽입된 광고 수만큼 앞당겨야 함
                insert_position = ad_dom_idx

                if insert_position < len(current_children):
                    # 중간에 삽입
                    self.driver.execute_script("""
                        arguments[0].insertBefore(arguments[1], arguments[2]);
                    """, parent, ad_element, current_children[insert_position])
                else:
                    # 맨 끝에 추가
                    self.driver.execute_script("""
                        arguments[0].appendChild(arguments[1]);
                    """, parent, ad_element)

            print(f"      - 2단계: 광고 {len(ads)}개 원래 위치에 삽입 완료")
            print(f"      - DOM 재구성 완료: 광고 {len(ads)}개 + 일반 {len(organics)}개")

        except Exception as e:
            print(f"      ❌ DOM 재구성 실패: {e}")
            import traceback
            traceback.print_exc()

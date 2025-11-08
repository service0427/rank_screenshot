#!/usr/bin/env python3
"""
순위 상태 관리 모듈
DOM 상태를 JSON으로 저장하고, 순위 변경 전후를 비교
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from selenium.webdriver.remote.webelement import WebElement


class RankStateManager:
    """순위 상태를 JSON으로 저장하고 관리하는 클래스"""

    def __init__(self, base_dir: str = "rank_states"):
        """
        Args:
            base_dir: JSON 파일 저장 기본 디렉토리
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def capture_state(
        self,
        driver,
        all_items: List[WebElement],
        items_info: List[Dict],
        organic_products: List[WebElement],
        organic_dom_indices: List[int],
        label: str = "state"
    ) -> Dict:
        """
        현재 DOM 상태를 캡처하여 딕셔너리로 반환

        Args:
            driver: Selenium WebDriver 인스턴스
            all_items: 전체 li 요소 리스트
            items_info: 각 항목의 정보
            organic_products: 광고 제외 제품 리스트
            organic_dom_indices: 광고 제외 제품의 DOM 인덱스
            label: 상태 라벨 (before, after 등)

        Returns:
            상태 딕셔너리
        """
        state = {
            "label": label,
            "timestamp": datetime.now().isoformat(),
            "total_items": len(all_items),
            "organic_count": len(organic_products),
            "ad_count": len(all_items) - len(organic_products),
            "items": []
        }

        # 각 항목의 상세 정보 저장
        for idx, item in enumerate(all_items):
            try:
                # 기본 정보
                item_data = {
                    "dom_index": idx,
                    "is_ad": items_info[idx]["is_ad"] if idx < len(items_info) else True,
                    "rank": items_info[idx].get("rank") if idx < len(items_info) else None,
                }

                # 상품 링크 추출
                try:
                    link_elem = item.find_element("css selector", 'a[href*="/vp/products/"]')
                    item_data["link"] = link_elem.get_attribute("href")
                except:
                    item_data["link"] = None

                # 상품명 추출
                try:
                    name_elem = item.find_element("css selector", '[class*="name"]')
                    item_data["name"] = name_elem.text[:50]  # 앞 50자만
                except:
                    item_data["name"] = None

                # 순위 워터마크 추출 (1~10등)
                try:
                    rank_mark_elem = item.find_element("css selector", '[class*="RankMark"]')
                    item_data["rank_watermark"] = rank_mark_elem.text
                    item_data["rank_watermark_class"] = rank_mark_elem.get_attribute("class")
                except:
                    item_data["rank_watermark"] = None
                    item_data["rank_watermark_class"] = None

                state["items"].append(item_data)

            except Exception as e:
                # 파싱 실패 시 기본 정보만 저장
                state["items"].append({
                    "dom_index": idx,
                    "is_ad": True,
                    "rank": None,
                    "error": str(e)
                })

        return state

    def save_state(self, state: Dict, filename: str) -> Optional[str]:
        """
        상태를 JSON 파일로 저장

        Args:
            state: 상태 딕셔너리
            filename: 저장할 파일명 (확장자 제외)

        Returns:
            저장된 파일 경로 (실패 시 None)
        """
        try:
            filepath = self.base_dir / f"{filename}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

            print(f"📄 순위 상태 저장: {filepath}")
            return str(filepath)

        except Exception as e:
            print(f"❌ 순위 상태 저장 실패: {e}")
            return None

    def compare_states(self, before: Dict, after: Dict) -> Dict:
        """
        변경 전후 상태를 비교

        Args:
            before: 변경 전 상태
            after: 변경 후 상태

        Returns:
            비교 결과 딕셔너리
        """
        comparison = {
            "changes": [],
            "ad_moved": False,
            "rank_watermark_issues": []
        }

        # 광고 위치 변경 확인
        before_ads = [item for item in before["items"] if item["is_ad"]]
        after_ads = [item for item in after["items"] if item["is_ad"]]

        if len(before_ads) != len(after_ads):
            comparison["ad_moved"] = True
            comparison["changes"].append("광고 개수가 변경되었습니다")

        # DOM 인덱스 기반 광고 위치 확인
        before_ad_indices = set(item["dom_index"] for item in before_ads)
        after_ad_indices = set(item["dom_index"] for item in after_ads)

        if before_ad_indices != after_ad_indices:
            comparison["ad_moved"] = True
            moved = before_ad_indices.symmetric_difference(after_ad_indices)
            comparison["changes"].append(f"광고 위치 변경: DOM 인덱스 {moved}")

        # 순위 워터마크 확인 (1~10등)
        for item in after["items"]:
            if not item["is_ad"] and item.get("rank") and item["rank"] <= 10:
                expected_rank = str(item["rank"])
                actual_mark = item.get("rank_watermark")

                if actual_mark != expected_rank:
                    comparison["rank_watermark_issues"].append({
                        "dom_index": item["dom_index"],
                        "expected": expected_rank,
                        "actual": actual_mark,
                        "name": item.get("name")
                    })

        return comparison

    def print_comparison(self, comparison: Dict):
        """
        비교 결과 출력

        Args:
            comparison: 비교 결과 딕셔너리
        """
        print("\n" + "=" * 60)
        print("📊 순위 변경 검증 결과")
        print("=" * 60)

        if comparison["ad_moved"]:
            print("❌ 광고 위치 변경 감지!")
            for change in comparison["changes"]:
                print(f"   • {change}")
        else:
            print("✅ 광고 위치 유지됨")

        if comparison["rank_watermark_issues"]:
            print(f"\n⚠️  순위 워터마크 불일치: {len(comparison['rank_watermark_issues'])}건")
            for issue in comparison["rank_watermark_issues"]:
                print(f"   • DOM[{issue['dom_index']}]: 예상={issue['expected']}, 실제={issue['actual']}")
                print(f"     상품: {issue['name']}")
        else:
            print("✅ 순위 워터마크 일치")

        print("=" * 60)

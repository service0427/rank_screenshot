#!/usr/bin/env python3
"""
순위 워터마크 관리 모듈 (1~10등 쿠팡 워터마크 전용)
Edit 모드에서 쿠팡 워터마크 백업 → 제거 → 순위 조작 → 롤백
"""

from typing import List, Optional, Dict
from selenium.webdriver.remote.webelement import WebElement
from lib.constants import Config


class WatermarkManager:
    """1~10등 쿠팡 워터마크 백업/제거/롤백 전용 클래스"""

    def __init__(self, driver):
        """
        Args:
            driver: Selenium WebDriver 인스턴스
        """
        self.driver = driver
        self._watermark_backup = None  # 백업된 워터마크 스타일

    def backup_and_remove(self, items: List[WebElement], count: int = 10) -> bool:
        """
        1~10등 워터마크 백업 후 제거

        Args:
            items: 일반 상품 요소 리스트 (WebElement)
            count: 백업/제거할 워터마크 개수 (기본: 10)

        Returns:
            성공 여부
        """
        try:
            print(f"\n📦 1~{count}등 워터마크 백업 및 제거 중...")

            # Step 1: 워터마크 스타일 백업
            self._watermark_backup = self._backup_watermark_style(items[:count])
            if self._watermark_backup:
                print(f"   ✓ 워터마크 스타일 백업 완료")
            else:
                print(f"   ℹ️  워터마크 없음 (11등 이하 상품일 수 있음)")

            # Step 2: 워터마크 제거
            removed_count = self._remove_watermarks(items[:count])
            print(f"   ✓ {removed_count}개 워터마크 제거 완료")

            return True

        except Exception as e:
            print(f"❌ 워터마크 백업 및 제거 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def restore(self, items: List[WebElement], count: int = 10) -> bool:
        """
        백업한 워터마크로 롤백 (순위 조작 후 1~10등 워터마크 재생성)

        Args:
            items: 현재 DOM 순서의 일반 상품 요소 리스트 (순위 조작 후)
            count: 재생성할 워터마크 개수 (기본: 10)

        Returns:
            성공 여부
        """
        try:
            print(f"\n🔄 1~{count}등 워터마크 롤백 중...")

            if not self._watermark_backup:
                print(f"   ⚠️  백업된 워터마크 스타일 없음 - 롤백 건너뜀")
                return False

            # 백업한 스타일로 워터마크 재생성 (위치 기준)
            created_count = self._create_watermarks(
                items[:count],
                self._watermark_backup
            )

            print(f"   ✓ {created_count}개 워터마크 롤백 완료")
            return True

        except Exception as e:
            print(f"❌ 워터마크 롤백 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def remove_single(self, element: WebElement) -> bool:
        """
        단일 상품의 워터마크 제거 (다른 페이지 교체용)

        Args:
            element: 워터마크를 제거할 상품 요소

        Returns:
            성공 여부
        """
        try:
            result = self.driver.execute_script("""
                var element = arguments[0];
                var watermark = element.querySelector('[class*="RankMark"]') ||
                                element.querySelector('[class*="rank"]') ||
                                element.querySelector('[class*="number"]');

                if (watermark && watermark.parentElement) {
                    watermark.parentElement.removeChild(watermark);
                    return true;
                }
                return false;
            """, element)

            return bool(result)

        except Exception as e:
            print(f"   ⚠️  워터마크 제거 실패: {e}")
            return False

    def _backup_watermark_style(self, items: List[WebElement]) -> Optional[Dict]:
        """
        1~10등 쿠팡 워터마크 스타일 백업

        Returns:
            {
                'rankClasses': ['RankMark_rank1__xxx', 'RankMark_rank2__xxx', ...],
                'tagName': 'span',
                'fontSize': '...',
                ...
            }
        """
        try:
            js_code = """
            var products = arguments[0];
            var rankClasses = new Array(10).fill(null);
            var commonStyle = null;

            // 각 상품에서 워터마크를 찾아 텍스트 기준으로 올바른 위치에 저장
            for (var i = 0; i < Math.min(products.length, 10); i++) {
                var element = products[i];

                // 워터마크 찾기
                var watermark = element.querySelector('[class*="RankMark"]') ||
                                element.querySelector('[class*="rank"]') ||
                                element.querySelector('[class*="number"]');

                if (watermark) {
                    // 워터마크 텍스트 읽기
                    var rankText = watermark.textContent.trim();
                    var rankNum = parseInt(rankText, 10);

                    // 유효한 순위(1~10)인 경우 해당 인덱스에 저장
                    if (rankNum >= 1 && rankNum <= 10) {
                        rankClasses[rankNum - 1] = watermark.className;
                    } else {
                        // 순위가 유효하지 않으면 위치 기준으로 저장 (fallback)
                        rankClasses[i] = watermark.className;
                    }

                    // 첫 번째 워터마크에서 공통 스타일 추출
                    if (!commonStyle) {
                        var computedStyle = window.getComputedStyle(watermark);
                        commonStyle = {
                            tagName: watermark.tagName,
                            fontSize: computedStyle.fontSize,
                            fontWeight: computedStyle.fontWeight,
                            fontFamily: computedStyle.fontFamily,
                            color: computedStyle.color,
                            backgroundColor: computedStyle.backgroundColor,
                            width: computedStyle.width,
                            height: computedStyle.height,
                            position: computedStyle.position,
                            top: computedStyle.top,
                            left: computedStyle.left,
                            right: computedStyle.right,
                            bottom: computedStyle.bottom,
                            zIndex: computedStyle.zIndex,
                            textAlign: computedStyle.textAlign,
                            lineHeight: computedStyle.lineHeight,
                            display: computedStyle.display
                        };
                    }
                }
            }

            if (commonStyle) {
                commonStyle.rankClasses = rankClasses;
                return commonStyle;
            }

            return null;
            """

            style_info = self.driver.execute_script(js_code, items)

            if style_info and style_info.get('rankClasses'):
                rank_classes = style_info['rankClasses']
                valid_classes = [c for c in rank_classes if c]
                print(f"      백업된 클래스: {len(valid_classes)}개")
                return style_info
            else:
                return None

        except Exception as e:
            print(f"      ⚠️  백업 실패: {e}")
            return None

    def _remove_watermarks(self, items: List[WebElement]) -> int:
        """
        워터마크 제거

        Returns:
            제거된 워터마크 개수
        """
        removed_count = 0

        js_code = """
        var element = arguments[0];
        var watermark = element.querySelector('[class*="RankMark"]') ||
                        element.querySelector('[class*="rank"]') ||
                        element.querySelector('[class*="number"]');

        if (watermark && watermark.parentElement) {
            watermark.parentElement.removeChild(watermark);
            return true;
        }
        return false;
        """

        for item in items:
            try:
                result = self.driver.execute_script(js_code, item)
                if result:
                    removed_count += 1
            except Exception:
                pass

        return removed_count

    def _create_watermarks(
        self,
        items: List[WebElement],
        style_info: Dict
    ) -> int:
        """
        백업한 스타일로 워터마크 재생성 (위치 기준)

        Args:
            items: 현재 DOM 순서의 상품 요소 리스트
            style_info: 백업된 스타일 정보

        Returns:
            생성된 워터마크 개수
        """
        created_count = 0
        rank_classes = style_info.get('rankClasses', [])

        for rank, element in enumerate(items, 1):
            try:
                class_index = rank - 1

                if class_index >= len(rank_classes) or not rank_classes[class_index]:
                    continue

                rank_class_name = rank_classes[class_index]

                js_code = """
                var element = arguments[0];
                var rankNum = arguments[1];
                var rankClassName = arguments[2];
                var style = arguments[3];

                // 기존 워터마크 제거
                var existingWatermark = element.querySelector('[class*="RankMark"]');
                if (existingWatermark && existingWatermark.parentElement) {
                    existingWatermark.parentElement.removeChild(existingWatermark);
                }

                // 워터마크 생성
                var watermark = document.createElement(style.tagName || 'span');
                watermark.className = rankClassName;
                watermark.textContent = rankNum.toString();

                // 위치 설정
                if (!watermark.style.position || watermark.style.position === 'static') {
                    watermark.style.position = style.position || 'absolute';
                }

                // 상품 요소에 추가
                element.style.position = 'relative';
                element.insertBefore(watermark, element.firstChild);

                return true;
                """

                created = self.driver.execute_script(
                    js_code, element, rank, rank_class_name, style_info
                )
                if created:
                    created_count += 1

            except Exception:
                pass

        return created_count

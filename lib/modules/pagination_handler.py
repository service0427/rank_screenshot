#!/usr/bin/env python3
"""
페이지네이션 핸들러
검색 결과에서 여러 페이지를 순회하며 상품 탐색
"""

from typing import Optional, Tuple
import time
import random
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class PaginationHandler:
    """페이지네이션 핸들러 클래스"""

    def __init__(self, driver):
        """
        Args:
            driver: Selenium WebDriver
        """
        self.driver = driver
        self.current_page = 1
        self.max_pages = 26  # 최대 26페이지까지 탐색

    def go_to_page(self, page_num: int, wait_time: float = 2.0) -> Tuple[bool, Optional[str]]:
        """
        특정 페이지로 이동 (URL 파라미터 기반 우선, 실패 시 클릭 기반)

        Args:
            page_num: 이동할 페이지 번호 (1-based)
            wait_time: 페이지 로드 후 대기 시간 (초)

        Returns:
            (성공 여부, 에러 메시지)
        """
        try:
            print(f"\n📄 페이지 {page_num}로 이동 중...")

            # 현재 페이지와 같으면 이동 불필요
            if self.current_page == page_num:
                print(f"   ℹ️  이미 페이지 {page_num}에 있습니다")
                return (True, None)

            # 방법 1: URL 파라미터로 직접 이동 (가장 안정적)
            print(f"   🔗 URL 파라미터로 페이지 {page_num} 이동 시도...")
            url_success = self._go_to_page_by_url(page_num, wait_time)
            if url_success:
                return (True, None)

            # 방법 2: 클릭 기반 이동 (폴백)
            print(f"   🖱️  클릭 기반 페이지 {page_num} 이동 시도...")

            # 1. 페이지네이션 영역 찾기
            pagination = self._find_pagination_area()
            if not pagination:
                return (False, "페이지네이션 영역을 찾을 수 없음")

            # 2. 페이지 번호 버튼 찾기
            page_button = self._find_page_button(pagination, page_num)
            if not page_button:
                # 페이지 번호가 보이지 않는 경우 (다음 그룹으로 이동 필요)
                if not self._navigate_to_page_group(page_num):
                    return (False, f"페이지 {page_num} 버튼을 찾을 수 없음")

                # 다시 버튼 찾기
                pagination = self._find_pagination_area()
                if pagination:
                    page_button = self._find_page_button(pagination, page_num)

            if not page_button:
                return (False, f"페이지 {page_num} 버튼을 찾을 수 없음")

            # 3. 랜덤 지연 (사람처럼 행동)
            delay = random.uniform(0.5, 1.5)
            time.sleep(delay)

            # 4. 페이지 버튼 클릭
            print(f"   🖱️  페이지 {page_num} 버튼 클릭")
            page_button.click()

            # 5. 페이지 로드 대기
            time.sleep(wait_time)

            # 6. 현재 페이지 번호 업데이트
            actual_page = self._get_current_page_from_url()
            if actual_page:
                self.current_page = actual_page
                print(f"   ✅ 페이지 {actual_page}로 이동 완료")
            else:
                self.current_page = page_num
                print(f"   ✅ 페이지 {page_num}로 이동 완료 (URL 확인 실패)")

            # 7. 점검 페이지 체크
            if self._is_blocked_page():
                return (False, "점검 페이지로 리다이렉트됨")

            return (True, None)

        except TimeoutException:
            error_msg = f"페이지 {page_num} 로드 타임아웃"
            print(f"   ❌ {error_msg}")
            return (False, error_msg)
        except Exception as e:
            error_msg = f"페이지 이동 실패: {e}"
            print(f"   ❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return (False, error_msg)

    def go_to_next_page(self, wait_time: float = 2.0) -> Tuple[bool, Optional[str]]:
        """
        다음 페이지로 이동

        Args:
            wait_time: 페이지 로드 후 대기 시간 (초)

        Returns:
            (성공 여부, 에러 메시지)
        """
        next_page = self.current_page + 1

        if next_page > self.max_pages:
            return (False, f"최대 페이지({self.max_pages}) 도달")

        return self.go_to_page(next_page, wait_time)

    def _find_pagination_area(self) -> Optional[object]:
        """
        페이지네이션 영역 찾기

        Returns:
            페이지네이션 요소 (실패 시 None)
        """
        try:
            # 쿠팡 페이지네이션 선택자 (여러 가능성 시도)
            selectors = [
                'div.search-pagination',
                'div[class*="pagination"]',
                'nav[class*="pagination"]',
                'div.pagination',
                'ol.search-pagination'
            ]

            for selector in selectors:
                try:
                    pagination = self.driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"   ✓ 페이지네이션 영역 발견: {selector}")
                    return pagination
                except NoSuchElementException:
                    continue

            print(f"   ⚠️  페이지네이션 영역을 찾을 수 없음")
            return None

        except Exception as e:
            print(f"   ⚠️  페이지네이션 검색 오류: {e}")
            return None

    def _find_page_button(self, pagination, page_num: int) -> Optional[object]:
        """
        특정 페이지 번호 버튼 찾기

        Args:
            pagination: 페이지네이션 영역 요소
            page_num: 찾을 페이지 번호

        Returns:
            페이지 버튼 요소 (실패 시 None)
        """
        try:
            # 모든 페이지 링크 가져오기
            page_links = pagination.find_elements(By.TAG_NAME, 'a')

            # 디버깅: 발견된 모든 링크 출력
            print(f"   🔍 페이지네이션 디버그: {len(page_links)}개 링크 발견")
            for idx, link in enumerate(page_links):
                text = link.text.strip()
                href = link.get_attribute('href') or ''
                class_name = link.get_attribute('class') or ''
                data_page = link.get_attribute('data-page') or ''
                print(f"      [{idx}] text='{text}', data-page='{data_page}', class='{class_name[:50]}...'")

            for link in page_links:
                # 링크 텍스트가 페이지 번호와 일치하는지 확인
                text = link.text.strip()
                try:
                    link_page_num = int(text)
                    if link_page_num == page_num:
                        print(f"   ✓ 페이지 {page_num} 버튼 발견")
                        return link
                except ValueError:
                    # 숫자가 아닌 텍스트 (이전, 다음 등) 무시
                    continue

            # 버튼을 찾지 못한 경우
            print(f"   ℹ️  페이지 {page_num} 버튼이 현재 그룹에 없음")
            return None

        except Exception as e:
            print(f"   ⚠️  페이지 버튼 검색 오류: {e}")
            return None

    def _navigate_to_page_group(self, target_page: int) -> bool:
        """
        목표 페이지가 속한 그룹으로 이동 (다음/이전 버튼 사용)

        쿠팡은 보통 10개씩 페이지 번호를 표시하므로,
        예를 들어 15페이지로 가려면 "다음" 버튼을 클릭해야 함

        Args:
            target_page: 목표 페이지 번호

        Returns:
            성공 여부
        """
        try:
            # 현재 페이지 그룹 계산 (1-10, 11-20, 21-30)
            current_group = (self.current_page - 1) // 10
            target_group = (target_page - 1) // 10

            if current_group == target_group:
                # 같은 그룹이면 이동 불필요
                return True

            # 다음 그룹으로 이동
            if target_group > current_group:
                return self._click_next_group()
            # 이전 그룹으로 이동
            else:
                return self._click_prev_group()

        except Exception as e:
            print(f"   ⚠️  페이지 그룹 이동 실패: {e}")
            return False

    def _click_next_group(self) -> bool:
        """
        다음 페이지 그룹으로 이동 (> 버튼 클릭)

        쿠팡의 경우 [class^="Pagination_nextBtn"][data-page="next"] 선택자 사용

        Returns:
            성공 여부
        """
        try:
            # 쿠팡 전용 다음 버튼 선택자
            next_button_selector = '[class^="Pagination_nextBtn"][data-page="next"]'

            try:
                next_button = self.driver.find_element(By.CSS_SELECTOR, next_button_selector)

                # disabled 상태 체크
                class_name = next_button.get_attribute('class') or ''
                if 'disabled' in class_name.lower():
                    print(f"   ⚠️  다음 그룹 버튼이 비활성화됨 (마지막 그룹)")
                    return False

                print(f"   🖱️  다음 그룹 버튼 클릭 ({next_button_selector})")
                next_button.click()
                time.sleep(1.5)
                return True

            except NoSuchElementException:
                print(f"   ⚠️  다음 그룹 버튼을 찾을 수 없음 ({next_button_selector})")
                return False

        except Exception as e:
            print(f"   ⚠️  다음 그룹 이동 실패: {e}")
            return False

    def _click_prev_group(self) -> bool:
        """
        이전 페이지 그룹으로 이동 (< 버튼 클릭)

        Returns:
            성공 여부
        """
        try:
            pagination = self._find_pagination_area()
            if not pagination:
                return False

            # "이전" 버튼 찾기 (<, 이전, prev 등)
            prev_buttons = pagination.find_elements(By.TAG_NAME, 'a')

            for button in prev_buttons:
                aria_label = button.get_attribute('aria-label') or ''
                title = button.get_attribute('title') or ''
                text = button.text.strip()

                # 이전 버튼 식별
                if any(keyword in (aria_label + title + text).lower() for keyword in ['prev', '이전', '<', '‹', '«']):
                    print(f"   🖱️  이전 그룹 버튼 클릭")
                    button.click()
                    time.sleep(1.5)
                    return True

            print(f"   ⚠️  이전 그룹 버튼을 찾을 수 없음")
            return False

        except Exception as e:
            print(f"   ⚠️  이전 그룹 이동 실패: {e}")
            return False

    def _go_to_page_by_url(self, page_num: int, wait_time: float = 2.0) -> bool:
        """
        URL 파라미터를 변경하여 페이지 이동

        Args:
            page_num: 이동할 페이지 번호
            wait_time: 페이지 로드 후 대기 시간

        Returns:
            성공 여부
        """
        try:
            current_url = self.driver.current_url

            # URL에 page 파라미터 추가/변경
            if '&page=' in current_url:
                # 기존 page 파라미터 교체
                new_url = re.sub(r'&page=\d+', f'&page={page_num}', current_url)
            elif '?page=' in current_url:
                # 첫 파라미터가 page인 경우
                new_url = re.sub(r'\?page=\d+', f'?page={page_num}', current_url)
            else:
                # page 파라미터가 없으면 추가
                separator = '&' if '?' in current_url else '?'
                new_url = f"{current_url}{separator}page={page_num}"

            # 새 URL로 이동
            self.driver.get(new_url)

            # 페이지 로드 대기
            time.sleep(wait_time)

            # 현재 페이지 번호 업데이트
            actual_page = self._get_current_page_from_url()
            if actual_page:
                self.current_page = actual_page
                print(f"   ✅ URL 파라미터로 페이지 {actual_page}로 이동 완료")
                return True
            else:
                self.current_page = page_num
                print(f"   ✅ URL 파라미터로 페이지 {page_num}로 이동 완료")
                return True

        except Exception as e:
            print(f"   ⚠️  URL 기반 페이지 이동 실패: {e}")
            return False

    def _get_current_page_from_url(self) -> Optional[int]:
        """
        URL에서 현재 페이지 번호 추출

        Returns:
            현재 페이지 번호 (실패 시 None)
        """
        try:
            current_url = self.driver.current_url

            # URL에 page 파라미터가 있는지 확인
            if '&page=' in current_url or '?page=' in current_url:
                # page= 뒤의 숫자 추출
                if '&page=' in current_url:
                    page_str = current_url.split('&page=')[1].split('&')[0]
                else:
                    page_str = current_url.split('?page=')[1].split('&')[0]

                return int(page_str)
            else:
                # page 파라미터가 없으면 1페이지
                return 1

        except Exception as e:
            print(f"   ⚠️  URL에서 페이지 번호 추출 실패: {e}")
            return None

    def _is_blocked_page(self) -> bool:
        """
        점검 페이지로 리다이렉트되었는지 확인

        Returns:
            점검 페이지 여부
        """
        try:
            current_url = self.driver.current_url.lower()

            # 점검 페이지 URL 패턴
            blocked_patterns = ['sorry', 'block', 'maintenance', 'error']

            for pattern in blocked_patterns:
                if pattern in current_url:
                    print(f"   ⚠️  점검 페이지 감지: {pattern}")
                    return True

            return False

        except Exception:
            return False

    def reset(self):
        """페이지 번호 초기화"""
        self.current_page = 1
        print(f"   🔄 페이지네이션 상태 초기화 (현재 페이지: 1)")

    def has_next_page(self) -> bool:
        """
        다음 페이지가 있는지 확인

        쿠팡의 경우 'a[class*="Pagination_nextBtn"]:not([class*="Pagination_disabled"])'
        선택자로 활성화된 다음 버튼이 있는지 확인

        Returns:
            다음 페이지 존재 여부
        """
        try:
            # 최대 페이지 제한 먼저 확인
            if self.current_page >= self.max_pages:
                print(f"   ℹ️  최대 페이지({self.max_pages}) 도달")
                return False

            # DOM에서 활성화된 다음 버튼 찾기
            next_button_selector = 'a[class*="Pagination_nextBtn"]:not([class*="Pagination_disabled"])'

            try:
                next_button = self.driver.find_element(By.CSS_SELECTOR, next_button_selector)
                print(f"   ✓ 다음 페이지 버튼 발견 (활성화됨)")
                return True
            except NoSuchElementException:
                print(f"   ℹ️  다음 페이지 버튼이 없거나 비활성화됨")
                return False

        except Exception as e:
            print(f"   ⚠️  다음 페이지 확인 오류: {e}")
            return False

    def get_current_page(self) -> int:
        """
        현재 페이지 번호 반환

        Returns:
            현재 페이지 번호
        """
        return self.current_page

    def is_empty_results_page(self) -> bool:
        """
        검색 결과가 없는 페이지인지 확인

        쿠팡의 경우 "검색결과가 없습니다" 메시지 또는
        빈 상품 목록으로 판단

        Returns:
            빈 결과 페이지 여부
        """
        try:
            # 1. "검색결과가 없습니다" 메시지 확인
            no_result_selectors = [
                'div.no-result_magnifier__SUz6j',  # 쿠팡 no-result 아이콘
                'div[class*="no-result"]',
                'div.search-no-result'
            ]

            for selector in no_result_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"   ⚠️  빈 결과 페이지 감지: {selector}")
                    return True
                except NoSuchElementException:
                    continue

            # 2. 텍스트 메시지 확인
            page_text = self.driver.page_source
            if '검색결과가 없습니다' in page_text or '검색 결과가 없습니다' in page_text:
                print(f"   ⚠️  빈 결과 페이지 감지: '검색결과가 없습니다' 메시지")
                return True

            # 3. 상품 목록이 비어있는지 확인 (추가 검증)
            # JavaScript로 상품 개수 확인
            js_code = """
            const products = document.querySelectorAll('li[data-item-id]');
            return products.length;
            """
            product_count = self.driver.execute_script(js_code)

            if product_count == 0:
                print(f"   ⚠️  빈 결과 페이지 감지: 상품 개수 = 0")
                return True

            return False

        except Exception as e:
            print(f"   ⚠️  빈 결과 페이지 확인 오류: {e}")
            # 오류 발생 시 안전하게 False 반환
            return False

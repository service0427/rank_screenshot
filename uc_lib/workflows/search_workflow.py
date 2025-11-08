#!/usr/bin/env python3
"""
순수 오리지널 상품 검색 워크플로우

워크플로우: Main → Search → Match → Highlight → Capture → Upload

핵심 기능:
- 쿠팡 상품 검색 및 매칭 (product_id, item_id, vendor_item_id)
- 다중 페이지 탐색 (최대 26페이지)
- 하이라이트 및 순위 배지 표시 (타겟 상품)
- 스크린샷 캡처 및 업로드
"""

import time
from typing import Optional, Dict, Any
from pathlib import Path

# Selenium imports
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

# Project imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common.utils.highlight_preset import HighlightStyle, generate_highlight_js
from uc_lib.modules.product_page_visitor import ProductPageVisitor
from uc_lib.modules.pagination_handler import PaginationHandler
from common.constants import Config


class SearchWorkflowResult:
    """워크플로우 실행 결과를 담는 데이터 클래스"""

    def __init__(self):
        self.success = False
        self.matched_product = None
        self.match_condition = None
        self.before_screenshot = None
        self.before_screenshot_url = None
        self.after_screenshot = None
        self.after_screenshot_url = None
        self.error_message = None

        # 페이지 정보 (최종 요약용)
        self.found_on_page = None
        self.target_page = None

        # 탐색 통계 (실패/성공 모두)
        self.pages_searched = 0  # 탐색한 총 페이지 수
        self.total_products_checked = 0  # 확인한 총 상품 개수
        self.page_history = []  # 페이지별 상세 정보
        self.last_page_url = None  # 마지막 탐색 페이지 URL


class SearchWorkflow:
    """상품 검색 및 스크린샷 캡처 워크플로우"""

    def __init__(
        self,
        driver,
        handler,
        finder,
        screenshot_processor,
        core=None,
        enable_main_filter: bool = False
    ):
        """
        Args:
            driver: Selenium WebDriver
            handler: CoupangHandlerSelenium 인스턴스
            finder: ProductFinder 인스턴스
            screenshot_processor: ScreenshotProcessor 인스턴스
            core: BrowserCoreUC 인스턴스 (네트워크 필터 제어용, 선택)
            enable_main_filter: 메인 페이지 네트워크 필터 활성화 여부 (기본: False)
        """
        self.driver = driver
        self.handler = handler
        self.finder = finder
        self.screenshot_processor = screenshot_processor
        self.core = core
        self.enable_main_filter = enable_main_filter

        # 하이라이트 스타일은 Config 설정 직접 사용
        self.highlight_style = HighlightStyle(
            border_width=Config.HIGHLIGHT_BORDER_WIDTH,
            border_color=Config.HIGHLIGHT_BORDER_COLOR,
            border_style=Config.HIGHLIGHT_BORDER_STYLE,
            border_offset=Config.HIGHLIGHT_BORDER_OFFSET,
            background_overlay=Config.HIGHLIGHT_BACKGROUND_OVERLAY,
            background_color=Config.HIGHLIGHT_BACKGROUND_COLOR,
            show_piv_labels=Config.HIGHLIGHT_SHOW_PIV_LABELS,
            label_font_size=Config.HIGHLIGHT_LABEL_FONT_SIZE,
            label_background=Config.HIGHLIGHT_LABEL_BACKGROUND,
            label_text_color=Config.HIGHLIGHT_LABEL_TEXT_COLOR,
            label_padding=Config.HIGHLIGHT_LABEL_PADDING,
            label_border_radius=Config.HIGHLIGHT_LABEL_BORDER_RADIUS,
            match_highlight_color=Config.HIGHLIGHT_MATCH_COLOR,
            show_rank_badge=Config.HIGHLIGHT_SHOW_RANK_BADGE,
            rank_badge_size=Config.HIGHLIGHT_RANK_BADGE_SIZE,
            rank_badge_color=Config.HIGHLIGHT_RANK_BADGE_COLOR,
            rank_badge_text_color=Config.HIGHLIGHT_RANK_BADGE_TEXT_COLOR
        )

        # 상품 페이지 방문 모듈 초기화 (core, enable_main_filter 전달)
        self.page_visitor = ProductPageVisitor(driver, handler, core, enable_main_filter)

        # 페이지네이션 핸들러 초기화
        self.pagination = PaginationHandler(driver)

        # 공유 상태: 현재 페이지의 상품 분석 결과 (순위 불일치 방지)
        self.current_items_info = None  # items_info 리스트
        self.current_all_items = None   # WebElement 리스트

    def execute(
        self,
        keyword: str,
        product_id: Optional[str] = None,
        item_id: Optional[str] = None,
        vendor_item_id: Optional[str] = None,
        version: str = "unknown",
        min_rank: Optional[int] = None,  # Adjust 모드 개발용 인터페이스 (현재 미사용)
        screenshot_id: Optional[int] = None
    ) -> SearchWorkflowResult:
        """
        전체 워크플로우 실행 (순수 오리지널)

        순서: Main → Search → Match → Highlight → Capture → Upload

        Args:
            keyword: 검색 키워드
            product_id: 상품 ID (매칭용)
            item_id: 아이템 ID (매칭용)
            vendor_item_id: 판매자 아이템 ID (매칭용)
            version: Chrome 버전
            min_rank: Adjust 모드 개발용 인터페이스 (현재 미사용)
            screenshot_id: 업로드용 작업 ID

        Returns:
            SearchWorkflowResult 객체
        """
        result = SearchWorkflowResult()
        self.screenshot_id = screenshot_id  # 메타데이터 생성 시 사용

        try:
            # 1. 쿠팡 홈페이지 이동
            print("\n" + "=" * 60)
            print("🏠 쿠팡 홈페이지 이동")
            print("=" * 60 + "\n")

            # 네트워크 필터 활성화 (페이지 이동 **전**에 활성화해야 리소스 차단됨)
            if self.core and self.enable_main_filter:
                print(f"   🔍 필터 활성화 조건 체크: enable_main_filter={self.enable_main_filter}")
                print(f"   ✅ 페이지 이동 전 네트워크 필터 활성화\n")
                self.core.enable_network_filter()
            elif not self.enable_main_filter:
                print(f"   ℹ️  네트워크 필터 비활성화됨 (--enable-main-filter 플래그 없음)\n")

            if not self.handler.navigate_to_home():
                result.error_message = "홈페이지 이동 실패"
                return result

            # 홈페이지 로딩 완료 대기
            self._wait_for_page_load()

            # URL 확인 (디버깅용)
            current_url = self.driver.current_url.rstrip('/')
            print(f"   🔍 페이지 로드 완료 - 현재 URL: {current_url}")

            # 네트워크 필터 작동 확인 (페이지 로드 후 모니터링)
            if self.core and self.enable_main_filter:
                print(f"\n   🔍 네트워크 필터 작동 확인 (3초간 모니터링)...")
                self.core._monitor_network_requests(duration=3)

            print()

            # 2. 상품 검색
            # 네트워크 필터 비활성화 (검색 결과 페이지에서는 필터 해제)
            if self.core and self.enable_main_filter:
                self.core.disable_network_filter()

            print("\n" + "=" * 60)
            print("🔍 상품 검색 실행")
            print("=" * 60)
            print(f"키워드: {keyword}\n")

            if not self.handler.search_product(keyword):
                result.error_message = "검색 실패 - 검색창을 찾을 수 없음"
                return result

            # 검색 결과 로딩 완료 대기
            self._wait_for_page_load()

            # 현재 URL 출력 (디버깅)
            current_url = self.driver.current_url
            print(f"   🔗 현재 URL: {current_url}\n")

            # http2 protocol error 체크 (네트워크 오류 → 차단으로 처리)
            if self._check_http2_error():
                result.error_message = "검색 결과 차단됨 (네트워크 오류 - http2 protocol error)"
                return result

            # 빠른 차단 체크 (스크롤 전에 확인)
            print("\n🔍 Checking for errors...\n")
            try:
                page_source = self.driver.page_source.lower()
                if any(keyword in page_source for keyword in ['rate limit', 'blocked', 'access denied', 'captcha', '일시적으로 차단', 'too many requests']):
                    result.error_message = "검색 결과 차단됨 (IP 제한 또는 봇 감지)"
                    print(f"🚫 차단 감지: 페이지 소스에서 차단 키워드 발견\n")
                    return result
            except:
                pass

            # 차단이 아니면 전체 페이지 스크롤로 이미지 로드
            print("🔄 이미지 로드 최적화: 전체 페이지 스크롤 중...\n")
            self.finder.scroll_full_page_for_lazy_loading(rounds=1, scroll_pause=0.1)

            # 4. 상품 목록 추출
            print("\n" + "=" * 60)
            print("🔍 상품 검색 결과 분석")
            print("=" * 60 + "\n")

            structure = self.finder.analyze_product_list_structure()
            organic_products = structure["organic_products"]

            if not organic_products:
                # 상품이 없는 경우 (차단은 이미 위에서 체크함)
                print(f"\n⚠️  1페이지에 상품이 없습니다 - 다음 페이지 탐색을 계속합니다...")
                organic_products = []  # 빈 리스트로 초기화하여 while 루프 진입

            # 5. 파라미터 기반 상품 매칭 (다중 페이지 탐색)
            print("\n" + "=" * 60)
            print("🔍 목표 상품 검색 (파라미터 기반)")
            print("=" * 60)
            print(f"검색 조건:")
            print(f"   - keyword: {keyword}")
            print(f"   - product_id: {product_id if product_id else '(지정 안 됨)'}")
            print(f"   - item_id: {item_id if item_id else '(지정 안 됨)'}")
            print(f"   - vendor_item_id: {vendor_item_id if vendor_item_id else '(지정 안 됨)'}")
            print("=" * 60 + "\n")

            # 다중 페이지 탐색 시작
            found_product = None
            match_condition = None
            current_page = 1
            max_pages = 26
            cumulative_rank_offset = 0  # 누적 순위 오프셋 (이전 페이지들의 상품 개수 합계)
            found_on_page = None  # 상품을 발견한 페이지 번호

            # 페이지별 정보 저장 (Adjust 모드용)
            page_history = []  # [{page: 1, url: "...", product_count: 27, rank_range: (1, 27)}, ...]

            while current_page <= max_pages:
                # 현재 페이지에서 상품 검색
                print(f"📄 페이지 {current_page}/{max_pages} 탐색 중... (누적 오프셋: {cumulative_rank_offset})")

                # 첫 페이지가 아닐 때만 다시 분석 (첫 페이지는 이미 Line 194에서 분석됨)
                if current_page > 1:
                    structure = self.finder.analyze_product_list_structure()
                    organic_products = structure["organic_products"]

                    # 상품이 없으면 탐색 종료
                    if not organic_products:
                        print(f"\n⚠️  페이지 {current_page}에 상품이 없습니다 - 탐색 종료")
                        print(f"   페이지 {current_page - 1}까지만 탐색 가능\n")
                        break

                # 전체 상품 목록의 URL 파라미터 추출
                all_products_params = self.finder.extract_all_products_params(organic_products)
                print(f"   ✓ {len(all_products_params)}개 상품의 파라미터 추출 완료")

                # 전체 아이템 및 광고 정보 수집 (첫 페이지는 이미 있으므로 재사용)
                items_info = structure.get('items_info', [])
                total_items_count = len(items_info)
                ad_count = sum(1 for info in items_info if info.get('is_ad', False))

                # 페이지 정보 저장 (모든 모드에서 수집)
                current_url = self.driver.current_url
                rank_start = cumulative_rank_offset + 1
                rank_end = cumulative_rank_offset + len(all_products_params)
                page_history.append({
                    'page': current_page,
                    'url': current_url,
                    'product_count': len(all_products_params),  # 일반 상품
                    'total_items': total_items_count,  # 전체 아이템 (광고 포함)
                    'ad_count': ad_count,  # 광고 개수
                    'rank_range': (rank_start, rank_end)
                })

                # 파라미터로 상품 검색
                found_product, match_condition = self.finder.find_product_by_params(
                    all_products_params,
                    product_id=product_id,
                    item_id=item_id,
                    vendor_item_id=vendor_item_id
                )

                if found_product:
                    # 누적 순위 계산 (페이지 내 순위 + 이전 페이지들의 상품 개수)
                    page_rank = found_product['rank']  # 현재 페이지 내 순위 (1-based)
                    actual_rank = cumulative_rank_offset + page_rank  # 실제 누적 순위

                    # 상품 발견!
                    print(f"\n✅ 목표 상품 발견! (페이지 {current_page})")
                    print(f"   매칭 조건: {match_condition}")
                    print(f"   페이지 내 순위: {page_rank}등")
                    print(f"   실제 누적 순위: {actual_rank}등")
                    print(f"   상품명: {found_product['name'][:50]}...")
                    print(f"   product_id: {found_product['product_id']}")
                    print(f"   item_id: {found_product['item_id']}")
                    print(f"   vendor_item_id: {found_product['vendor_item_id']}\n")

                    # 페이지 내 순위와 누적 순위 모두 저장
                    found_product['page_rank'] = page_rank  # 페이지 내 순위
                    found_product['rank'] = actual_rank  # 누적 순위 (표시용)
                    found_on_page = current_page

                    break

                # 상품을 못 찾았으면 다음 페이지로 이동
                print(f"   ℹ️  페이지 {current_page}에서 상품을 찾지 못함")

                # 현재 페이지의 상품 개수를 누적 오프셋에 추가
                cumulative_rank_offset += len(all_products_params)
                print(f"   📊 누적 오프셋 업데이트: {cumulative_rank_offset} (현재 페이지 +{len(all_products_params)})")

                if current_page >= max_pages:
                    print(f"\n❌ 최대 페이지({max_pages})까지 탐색했으나 상품을 찾지 못했습니다\n")
                    break

                # 다음 페이지로 이동
                current_page += 1
                success, error = self.pagination.go_to_page(current_page)

                if not success:
                    print(f"\n⚠️  페이지 {current_page} 이동 실패: {error}")
                    print(f"   페이지 {current_page - 1}까지만 탐색 가능\n")
                    break

                # 다음 페이지 로딩 대기
                self._wait_for_page_load()

                # 전체 페이지 스크롤로 모든 이미지 Lazy Loading 트리거
                print(f"   🔄 페이지 {current_page} 이미지 로드 최적화 중...")
                self.finder.scroll_full_page_for_lazy_loading(rounds=1, scroll_pause=0.3)

                # http2 protocol error 체크 (네트워크 오류 → 차단으로 처리)
                if self._check_http2_error():
                    result.error_message = "검색 결과 차단됨 (네트워크 오류 - http2 protocol error)"
                    return result

                # 새 페이지는 while 루프 시작 시 자동으로 분석됨 (Line 240-242)

            # 상품을 찾지 못한 경우
            if not found_product:
                result.error_message = "상품 매칭 실패 (모든 페이지 탐색 완료)"

                # 탐색 통계 저장
                result.pages_searched = current_page
                result.total_products_checked = cumulative_rank_offset
                result.page_history = page_history
                result.last_page_url = self.driver.current_url

                return result

            # 매칭 성공
            result.matched_product = found_product
            result.match_condition = match_condition

            # 페이지 정보 저장 (최종 요약용)
            result.found_on_page = found_on_page

            # 탐색 통계 저장 (성공 시에도)
            result.pages_searched = current_page
            result.total_products_checked = cumulative_rank_offset + found_product.get('page_rank', found_product.get('rank', 0))
            result.page_history = page_history
            result.last_page_url = self.driver.current_url

            # 6. 상품 정보 생성
            product_info = {
                "name": found_product['name'],
                "rank": found_product['rank'],
                "link": found_product['link'],
                "element": found_product['element'],
                "price": "",
                "rating": "",
                "review_count": ""
            }

            # 7. 상품 스크롤 및 하이라이트
            self.finder.scroll_to_center(product_info)

            print(f"\n{'=' * 60}")
            print(f"📸 스크린샷 캡처")
            print(f"{'=' * 60}\n")

            # 하이라이트 적용
            self._highlight_product(
                element=product_info['element'],
                product_data=found_product,
                match_condition=match_condition
            )

            # 페이지 안정화 대기
            self._wait_for_page_load()

            # 스크린샷 캡처 (디버그 오버레이 포함)
            self._display_watermark_and_capture(
                keyword=keyword,
                version=version,
                product_info=product_info,
                result=result,
                match_condition=match_condition
            )

            result.success = True
            return result

        except Exception as e:
            print(f"\n❌ 워크플로우 실행 실패: {e}")
            import traceback
            traceback.print_exc()
            result.error_message = str(e)
            return result

    def _check_http2_error(self) -> bool:
        """
        http2 protocol error 감지

        Returns:
            에러 발생 시 True, 정상이면 False
        """
        try:
            current_url = self.driver.current_url.lower()

            # http2_protocol_error 또는 차단 페이지 감지
            if 'http2_protocol_error' in current_url or 'err_http2_protocol_error' in current_url or 'chrome-error://' in current_url:
                print("\n🚫 http2 protocol error 감지!")
                print(f"   URL: {self.driver.current_url}")
                return True

            # 페이지 타이틀에서도 에러 감지
            try:
                page_title = self.driver.title.lower()
                if 'error' in page_title or '오류' in page_title:
                    # body 텍스트 확인
                    body_text = self.driver.find_element(By.TAG_NAME, 'body').text.lower()
                    if 'http2' in body_text or 'protocol' in body_text or 'err_' in body_text:
                        print("\n🚫 http2 protocol error 감지! (페이지 내용 기반)")
                        print(f"   Title: {self.driver.title}")
                        print(f"   URL: {self.driver.current_url}")
                        return True
            except:
                pass

            return False

        except Exception as e:
            print(f"⚠️  URL 확인 실패: {e}")
            return False

    def _wait_for_page_load(self, timeout: int = 10) -> bool:
        """
        페이지 로딩 완료 대기

        Args:
            timeout: 최대 대기 시간 (초)

        Returns:
            로딩 완료 여부
        """
        try:
            # 1. document.readyState === 'complete' 대기
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # 2. 네트워크 idle 상태 확인 (활성 요청 0개)
            for _ in range(20):  # 최대 2초 (0.1초 × 20회)
                active_requests = self.driver.execute_script(
                    """
                    return window.performance.getEntriesByType('resource')
                        .filter(r => !r.responseEnd).length;
                    """
                )
                if active_requests == 0:
                    break
                time.sleep(0.1)

            # 3. 추가 3초 대기 (동적 콘텐츠 렌더링 완료 보장)
            print("⏳ 페이지 로딩 완료 - 3초 안정화 대기 중...")
            time.sleep(3)

            print("✅ 페이지 완전히 로드됨")
            return True

        except Exception as e:
            print(f"⚠️  페이지 로딩 대기 실패: {e}")
            # 실패해도 3초는 대기
            time.sleep(3)
            return False

    def _display_watermark_and_capture(
        self,
        keyword: str,
        version: str,
        product_info: Dict,
        result: 'SearchWorkflowResult',
        match_condition: str = None
    ) -> bool:
        """
        스크린샷 캡처 (디버그 오버레이 포함)

        Args:
            keyword: 검색 키워드
            version: Chrome 버전
            product_info: 상품 정보 딕셔너리
            result: SearchWorkflowResult 객체 (스크린샷 저장용)
            match_condition: 매칭 조건 (메타데이터 생성용)

        Returns:
            성공 여부
        """
        try:
            # 0. 페이지네이션 고정 (스크린샷에 페이지 번호 표시)
            try:
                self.finder.fix_pagination_visibility()
            except Exception as e:
                print(f"⚠️  페이지네이션 고정 실패 (계속 진행): {e}")

            # 1. 상품 분석 및 디버그 오버레이
            try:
                # finder의 analyze_product_list_structure()를 사용하여 광고 여부 판단
                structure = self.finder.analyze_product_list_structure()

                # 공유 상태에 저장 (디버그 오버레이, 하이라이트 등에서 재사용)
                self.current_items_info = structure['items_info']
                self.current_all_items = structure['all_items']

                items_info = self.current_items_info
                all_items = self.current_all_items

                # 누적 오프셋 계산 (이전 페이지들의 정보 누적)
                current_page = result.found_on_page if result.found_on_page else 1
                rank_offset = 0  # 일반 상품 누적
                total_items_offset = 0  # 전체 아이템 누적
                ad_offset = 0  # 광고 누적

                # page_history에서 이전 페이지들의 정보 합산
                if hasattr(result, 'page_history') and result.page_history:
                    for page_info in result.page_history:
                        if page_info['page'] < current_page:
                            rank_offset += page_info['product_count']  # 일반 상품
                            # 전체 아이템과 광고는 page_info에 있으면 사용, 없으면 현재 계산
                            total_items_offset += page_info.get('total_items', page_info['product_count'])
                            ad_offset += page_info.get('ad_count', 0)
                else:
                    # page_history 없으면 추정값 사용 (비권장)
                    rank_offset = (current_page - 1) * 40
                    total_items_offset = (current_page - 1) * 40
                    ad_offset = 0

            except Exception as e:
                print(f"⚠️  상품 분석 중 오류 (계속 진행): {e}")

            # 디버깅 오버레이 표시 (독립적 try-except)
            try:
                if Config.ENABLE_DEBUG_OVERLAY:
                    self._add_debug_overlay(all_items, items_info, rank_offset, total_items_offset, ad_offset)
            except Exception as e:
                print(f"⚠️  디버깅 오버레이 표시 중 오류 (계속 진행): {e}")

            # 2. 스크린샷 캡처
            result.after_screenshot, result.after_screenshot_url = self.screenshot_processor.capture_with_overlay(
                keyword=keyword,
                version=version,
                overlay_text="",
                full_page=False,
                metadata=self._create_metadata(keyword, product_info, match_condition)
            )

            return True

        except Exception as e:
            print(f"❌ 스크린샷 캡처 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _highlight_product(self, element, product_data: Dict, match_condition: str):
        """
        상품 강조 표시 (프리셋 기반)

        Args:
            element: 강조할 상품 요소
            product_data: 상품 데이터 (product_id, item_id, vendor_item_id, rank 포함)
            match_condition: 매칭 조건 (어떤 값이 일치했는지)
        """
        try:
            # 전역 설정 체크: 하이라이트 표시 비활성화 시 스킵
            if not Config.ENABLE_HIGHLIGHT:
                print(f"   ℹ️  하이라이트(P/I/V 포함) 표시 비활성화 (Config.ENABLE_HIGHLIGHT=False)")
                return

            # JavaScript 코드 생성 (테두리)
            js_code = generate_highlight_js(
                element_selector="element",
                style=self.highlight_style,
                product_data=product_data,
                match_condition=match_condition
            )

            # 테두리 적용
            self.driver.execute_script(js_code, element)

            print(f"✅ 상품 강조 표시 완료")
            print(f"   매칭 정보: {match_condition}")

        except Exception as e:
            print(f"⚠️  상품 강조 실패: {e}")
            # Fallback: 기본 테두리만 표시
            try:
                self.driver.execute_script(
                    """
                    arguments[0].style.outline = '5px solid #FF0000';
                    arguments[0].style.outlineOffset = '-5px';
                    arguments[0].style.position = 'relative';
                    """,
                    element
                )
            except:
                pass

    def _create_metadata(self, keyword: str, product_info: Dict, match_condition: str = None) -> Dict[str, Any]:
        """
        업로드용 메타데이터 생성

        Args:
            keyword: 검색 키워드
            product_info: 상품 정보 딕셔너리
            match_condition: 매칭 조건 문자열

        Returns:
            메타데이터 딕셔너리 (match_product_id, match_item_id, match_vendor_item_id 포함)
        """
        url_params = self.finder.extract_url_params(product_info.get('link', ''))

        # match_condition 문자열을 boolean 필드로 변환 (agent.py와 동일한 로직)
        match_product_id = False
        match_item_id = False
        match_vendor_item_id = False

        if match_condition:
            if "완전 일치" in match_condition:
                # 완전 일치: 3개 모두 매칭
                match_product_id = True
                match_item_id = True
                match_vendor_item_id = True
            elif "product_id + vendor_item_id 일치" in match_condition:
                # product_id + vendor_item_id만 매칭
                match_product_id = True
                match_vendor_item_id = True
            elif "product_id + item_id 일치" in match_condition:
                # product_id + item_id만 매칭
                match_product_id = True
                match_item_id = True
            elif "item_id + vendor_item_id 일치" in match_condition:
                # item_id + vendor_item_id만 매칭
                match_item_id = True
                match_vendor_item_id = True
            elif "product_id만 일치" in match_condition:
                # product_id만 매칭
                match_product_id = True
            elif "item_id만 일치" in match_condition:
                # item_id만 매칭
                match_item_id = True
            elif "vendor_item_id만 일치" in match_condition:
                # vendor_item_id만 매칭
                match_vendor_item_id = True

        return {
            'screenshot_id': self.screenshot_id if hasattr(self, 'screenshot_id') and self.screenshot_id else '',
            'keyword': keyword,
            'product_id': url_params['product_id'],
            'item_id': url_params['item_id'],
            'vendor_item_id': url_params['vendor_item_id'],
            'rank': str(product_info.get('rank', 'unknown')),
            'match_product_id': match_product_id,
            'match_item_id': match_item_id,
            'match_vendor_item_id': match_vendor_item_id
        }

    def _add_debug_overlay(self, all_items: list, items_info: list, rank_offset: int = 0, total_items_offset: int = 0, ad_offset: int = 0):
        """
        디버깅용 오버레이 추가 (좌측 하단)

        Args:
            all_items: 전체 li 요소 리스트
            items_info: 각 항목의 정보 (is_ad, dom_index, rank)
            rank_offset: 누적 순위 오프셋 (이전 페이지들의 일반 상품 개수)
            total_items_offset: 누적 전체 아이템 오프셋 (이전 페이지들의 전체 아이템 개수)
            ad_offset: 누적 광고 오프셋 (이전 페이지들의 광고 개수)
        """
        try:
            if Config.DEBUG_MODE:
                print(f"\n🐛 디버깅 오버레이 추가 중...")

            # 🔍 디버그 정보를 파일로 저장 (디버그 모드일 때만)
            if Config.DEBUG_MODE:
                import json
                from datetime import datetime
                from pathlib import Path

                debug_dir = Path(__file__).parent.parent.parent / "debug_logs"
                debug_dir.mkdir(exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                debug_file = debug_dir / f"debug_overlay_{timestamp}.json"

                # items_info를 JSON으로 변환 (WebElement 제외)
                debug_data = []
                for idx, info in enumerate(items_info):
                    dom_index = info.get('dom_index', idx)
                    is_ad = info.get('is_ad', False)

                    # 누적 계산
                    cumulative_dom_index = total_items_offset + dom_index + 1

                    if is_ad:
                        ad_rank = info.get('ad_rank', 0)
                        cumulative_ad_rank = ad_offset + ad_rank
                        page_rank = None
                        cumulative_rank = None
                    else:
                        page_rank = info.get('rank', 0)
                        cumulative_rank = rank_offset + page_rank
                        ad_rank = None
                        cumulative_ad_rank = None

                    debug_item = {
                        "idx": idx,
                        "dom_index": dom_index,
                        "cumulative_dom_index": cumulative_dom_index,  # 누적 DOM 인덱스
                        "is_ad": is_ad,
                        "page_rank": page_rank,  # 페이지 내 일반 순위
                        "cumulative_rank": cumulative_rank,  # 누적 일반 순위
                        "ad_rank": ad_rank,  # 페이지 내 광고 순위
                        "cumulative_ad_rank": cumulative_ad_rank,  # 누적 광고 순위
                        "type": info.get('type'),
                        "product_id": info.get('product_id'),
                        "item_id": info.get('item_id'),
                        "vendor_item_id": info.get('vendor_item_id')
                    }
                    debug_data.append(debug_item)

                with open(debug_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "timestamp": timestamp,
                        "total_items": len(items_info),
                        "rank_offset": rank_offset,  # 일반 상품 오프셋
                        "total_items_offset": total_items_offset,  # 전체 아이템 오프셋
                        "ad_offset": ad_offset,  # 광고 오프셋
                        "items": debug_data
                    }, f, indent=2, ensure_ascii=False)

                print(f"   📁 디버그 정보 저장: {debug_file}")

                # 오래된 디버그 로그 자동 정리 (최신 50개만 유지)
                from common.utils.file_cleanup import cleanup_debug_logs
                try:
                    cleanup_debug_logs(base_dir=debug_dir, keep_count=50)
                except Exception as e:
                    logger.warning(f"디버그 로그 정리 실패: {e}")

            overlay_count = 0

            for idx, info in enumerate(items_info):
                try:
                    element = all_items[idx]
                    dom_index = info['dom_index']
                    is_ad = info['is_ad']

                    # 누적 인덱스 계산
                    cumulative_dom_index = total_items_offset + dom_index + 1  # 전체 DOM 인덱스 누적

                    # items_info의 값을 그대로 사용 (재계산 금지)
                    if is_ad:
                        ad_rank = info.get('ad_rank', 0)  # 페이지 내 광고 순위
                        cumulative_ad_rank = ad_offset + ad_rank  # 누적 광고 순위
                        label_text = f"전체:{cumulative_dom_index}/광고:{cumulative_ad_rank}"
                    else:
                        page_rank = info.get('rank', 0)  # 페이지 내 일반 순위
                        cumulative_rank = rank_offset + page_rank  # 누적 일반 순위
                        label_text = f"전체:{cumulative_dom_index}/일반:{cumulative_rank}"

                    # JavaScript로 오버레이 추가
                    js_code = """
                    var element = arguments[0];
                    var labelText = arguments[1];

                    // 기존 디버그 오버레이 제거
                    var existingDebug = element.querySelector('.debug-overlay');
                    if (existingDebug) {
                        existingDebug.remove();
                    }

                    // 디버그 오버레이 생성
                    var debugDiv = document.createElement('div');
                    debugDiv.className = 'debug-overlay';
                    debugDiv.textContent = '[' + labelText + ']';
                    debugDiv.style.cssText = `
                        position: absolute;
                        bottom: 10px;
                        left: 10px;
                        background: rgba(0, 0, 0, 0.85);
                        color: #00FF00;
                        padding: 4px 8px;
                        font-size: 11px;
                        font-weight: bold;
                        font-family: 'Courier New', monospace;
                        border-radius: 3px;
                        z-index: 10002;
                        pointer-events: none;
                    `;

                    // 상품 요소에 추가
                    element.style.position = 'relative';
                    element.appendChild(debugDiv);
                    """

                    self.driver.execute_script(js_code, element, label_text)
                    overlay_count += 1

                except Exception as e:
                    print(f"   ⚠️  [{idx}] 오버레이 추가 실패: {e}")
                    continue

            print(f"   ✓ {overlay_count}개 디버깅 오버레이 추가 완료")

        except Exception as e:
            print(f"❌ 디버깅 오버레이 추가 실패: {e}")
            import traceback
            traceback.print_exc()

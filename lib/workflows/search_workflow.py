#!/usr/bin/env python3
"""
상품 검색 워크플로우
검색 → 매칭 → 스크린샷 → 순위 변조의 전체 흐름을 관리
"""

import time
import math
import re
import json
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 하이라이트 프리셋 임포트
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from lib.utils.highlight_preset import HighlightPresets, generate_highlight_js
from lib.modules.rank_manipulator import RankManipulator
from lib.modules.rank.rank_swapper import RankSwapper
from lib.modules.product_page_visitor import ProductPageVisitor
from lib.modules.pagination_handler import PaginationHandler


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
        enable_rank_manipulation: bool = False,
        edit_mode: str = None,
        highlight_preset: str = "default",
        enable_main_filter: bool = False
    ):
        """
        Args:
            driver: Selenium WebDriver
            handler: CoupangHandlerSelenium 인스턴스
            finder: ProductFinder 인스턴스
            screenshot_processor: ScreenshotProcessor 인스턴스
            core: BrowserCoreUC 인스턴스 (네트워크 필터 제어용, 선택)
            enable_rank_manipulation: 순위 변조 기능 활성화 여부
            edit_mode: 순위 조작 모드 ("edit": 복잡한 DOM 재구성, "edit2": Simple Swap, None: 비활성)
            highlight_preset: 하이라이트 프리셋 이름
                            (default, minimal, detailed, subtle, neon, professional)
            enable_main_filter: 메인 페이지 네트워크 필터 활성화 여부 (기본: False)
        """
        self.driver = driver
        self.handler = handler
        self.finder = finder
        self.screenshot_processor = screenshot_processor
        self.core = core
        self.enable_rank_manipulation = enable_rank_manipulation
        self.edit_mode = edit_mode
        self.highlight_preset = highlight_preset
        self.highlight_style = HighlightPresets.get_preset(highlight_preset)
        self.enable_main_filter = enable_main_filter

        # 순위 조작 모듈 초기화 (edit_mode에 따라 다른 모듈 사용)
        if edit_mode == "edit2":
            print(f"   📐 Edit Mode: Simple Swap (v2)")
            self.rank_manipulator = RankSwapper(driver, finder)
        else:
            print(f"   📐 Edit Mode: DOM Reconstruction (v1)")
            self.rank_manipulator = RankManipulator(driver, finder)

        # 상품 페이지 방문 모듈 초기화 (core, enable_main_filter 전달)
        self.page_visitor = ProductPageVisitor(driver, handler, core, enable_main_filter)

        # 페이지네이션 핸들러 초기화
        self.pagination = PaginationHandler(driver)

    def execute(
        self,
        keyword: str,
        product_id: Optional[str] = None,
        item_id: Optional[str] = None,
        vendor_item_id: Optional[str] = None,
        version: str = "unknown",
        min_rank: Optional[int] = None
    ) -> SearchWorkflowResult:
        """
        전체 워크플로우 실행

        Args:
            keyword: 검색 키워드
            product_id: 상품 ID
            item_id: 아이템 ID
            vendor_item_id: 판매자 아이템 ID
            version: Chrome 버전
            min_rank: 최소 순위 (순위 조작 시 목표 순위)

        Returns:
            SearchWorkflowResult 객체
        """
        result = SearchWorkflowResult()

        try:
            # 0. 상품 페이지 방문 (--edit 옵션이 있고, product_id/item_id/vendor_item_id가 있는 경우만)
            product_detail_info = None  # 수집된 상품 상세 정보
            skip_search_steps = False

            if self.enable_rank_manipulation and product_id and item_id and vendor_item_id:
                print("\n" + "=" * 60)
                print("🔄 상품 페이지 방문 → 검색 복귀 워크플로우")
                print("=" * 60 + "\n")

                success, error, product_detail_info = self.page_visitor.visit_and_return_to_search(
                    product_id=product_id,
                    item_id=item_id,
                    vendor_item_id=vendor_item_id,
                    keyword=keyword,
                    wait_time=2.0
                )

                if not success:
                    print(f"⚠️  상품 페이지 방문 실패: {error}")
                    print(f"   계속 진행하여 검색을 시도합니다...\n")
                    # 실패해도 계속 진행 (검색만으로도 상품을 찾을 수 있음)
                else:
                    print(f"✅ 상품 페이지 방문 → 검색 복귀 완료\n")

                    # 수집된 상품 정보 로깅
                    if product_detail_info:
                        print(f"📦 상품 상세 정보:")
                        print(f"   - 상품명: {product_detail_info.get('title', 'N/A')[:50]}...")
                        print(f"   - 가격: {product_detail_info.get('price', {}).get('current', 'N/A')}")
                        print(f"   - 배송: {product_detail_info.get('delivery', {}).get('type', 'N/A')}")
                        print(f"   - 품절: {'예' if product_detail_info.get('sold_out') else '아니오'}\n")

                    # 이미 검색 결과 페이지에 있으므로 Step 1-2를 건너뜀
                    # 바로 Step 3 (에러 체크)로 이동

                    # 검색 결과 로딩 완료 대기
                    self._wait_for_page_load()

                    # Step 3으로 이동 (아래 검색 단계는 이미 완료됨)
                    # 여기서 continue 대신 플래그 사용
                    skip_search_steps = True

            # 1. 쿠팡 홈페이지 이동 (상품 페이지 방문을 하지 않은 경우만)
            if not skip_search_steps:
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

            # 2. 상품 검색 (상품 페이지 방문을 하지 않은 경우만)
            if not skip_search_steps:
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

            # 3. 에러 체크
            print("\n🔍 Checking for errors...\n")
            # (에러 체크 로직은 handler에서 처리)

            # 4. 상품 목록 추출
            print("\n" + "=" * 60)
            print("🔍 상품 검색 결과 분석")
            print("=" * 60 + "\n")

            structure = self.finder.analyze_product_list_structure()
            organic_products = structure["organic_products"]

            if not organic_products:
                result.error_message = "검색 결과 없음"
                return result

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

            # 페이지별 정보 저장 (Edit 모드용)
            page_history = []  # [{page: 1, url: "...", product_count: 27, rank_range: (1, 27)}, ...]

            while current_page <= max_pages:
                # 현재 페이지에서 상품 검색
                print(f"📄 페이지 {current_page}/{max_pages} 탐색 중... (누적 오프셋: {cumulative_rank_offset})")

                # 전체 상품 목록의 URL 파라미터 추출
                all_products_params = self.finder.extract_all_products_params(organic_products)
                print(f"   ✓ {len(all_products_params)}개 상품의 파라미터 추출 완료")

                # 페이지 정보 저장 (모든 모드에서 수집)
                current_url = self.driver.current_url
                rank_start = cumulative_rank_offset + 1
                rank_end = cumulative_rank_offset + len(all_products_params)
                page_history.append({
                    'page': current_page,
                    'url': current_url,
                    'product_count': len(all_products_params),
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
                    found_product['page_rank'] = page_rank  # 페이지 내 순위 (DOM 재배치용)
                    found_product['rank'] = actual_rank  # 누적 순위 (표시용)
                    found_on_page = current_page

                    # Edit 모드에서 다른 페이지로 이동할 경우를 대비하여 전체 DOM 백업
                    if self.enable_rank_manipulation and found_product.get('element'):
                        try:
                            outer_html = found_product['element'].get_attribute('outerHTML')
                            found_product['outerHTML'] = outer_html
                            print(f"   💾 상품 전체 DOM 백업 완료 (길이: {len(outer_html)} 문자)")
                        except Exception as e:
                            print(f"   ⚠️  DOM 백업 실패: {e}")
                            found_product['outerHTML'] = None

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

                # 새 페이지에서 상품 목록 다시 추출
                structure = self.finder.analyze_product_list_structure()
                organic_products = structure["organic_products"]

                if not organic_products:
                    print(f"\n⚠️  페이지 {current_page}에 상품이 없습니다 - 탐색 종료")
                    print(f"   페이지 {current_page - 1}까지만 탐색 가능\n")
                    break

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

            # 디버그: 페이지 히스토리 저장 (Edit 모드일 때)
            if self.enable_rank_manipulation and page_history:
                self._save_debug_info(page_history, found_product, keyword, product_id, item_id, vendor_item_id)

            # 목표 페이지 정보 초기화 (스코프 문제 해결)
            target_page_info = None
            target_page_num = None

            # --edit 모드에서 목표 순위(min_rank)가 속한 페이지로 이동
            if self.enable_rank_manipulation and found_on_page and min_rank:
                # 목표 순위가 속한 페이지 찾기
                for page_info in page_history:
                    rank_start, rank_end = page_info['rank_range']
                    if rank_start <= min_rank <= rank_end:
                        target_page_info = page_info
                        break

                if not target_page_info:
                    # 페이지 히스토리에서 못 찾으면 계산으로 추정
                    print(f"\n⚠️  페이지 히스토리에서 순위 {min_rank}를 찾을 수 없음 - 계산으로 추정")
                    PRODUCTS_PER_PAGE = 27
                    estimated_page = math.ceil(min_rank / PRODUCTS_PER_PAGE)
                    print(f"   추정 페이지: {estimated_page} (순위 {min_rank} ÷ {PRODUCTS_PER_PAGE})")

                    # URL 직접 구성
                    current_url = self.driver.current_url
                    trace_id_match = re.search(r'traceId=([^&]+)', current_url)
                    if trace_id_match:
                        trace_id = trace_id_match.group(1)
                        target_url = f"https://www.coupang.com/np/search?q={keyword}&traceId={trace_id}&channel=user&page={estimated_page}"
                        target_page_num = estimated_page
                    else:
                        result.error_message = "목표 페이지를 찾을 수 없음 (traceId 추출 실패)"
                        return result
                else:
                    target_url = target_page_info['url']
                    target_page_num = target_page_info['page']

                print(f"\n{'=' * 60}")
                print(f"🔄 Edit 모드: 목표 순위 페이지로 이동")
                print(f"{'=' * 60}\n")
                print(f"   상품 발견 위치: 페이지 {found_on_page} ({found_product['rank']}등)")
                print(f"   목표 순위: {min_rank}등")
                print(f"   목표 페이지: {target_page_num}")
                if target_page_info:
                    print(f"   순위 범위: {target_page_info['rank_range'][0]}~{target_page_info['rank_range'][1]}등")
                print(f"   이동 URL: {target_url}\n")

                # 페이지 정보 저장 (최종 요약용)
                result.target_page = target_page_num

                # 같은 페이지인지 확인
                is_same_page = (found_on_page == target_page_num)

                if is_same_page:
                    # 같은 페이지 시나리오: 페이지 새로고침 불필요
                    print(f"   ℹ️  같은 페이지 시나리오: 페이지 이동 생략")
                    print(f"      현재 페이지에서 상품 목록 재사용\n")

                    # 이미 가지고 있는 organic_products 사용 (found_product가 발견된 페이지)
                    # structure와 organic_products는 이미 최신 상태

                else:
                    # 다른 페이지 시나리오: 페이지 이동 필요
                    print(f"   🚀 다른 페이지 시나리오: 페이지 {target_page_num}로 이동 중...")
                    self.driver.get(target_url)
                    time.sleep(2)

                    # 페이지 로딩 대기
                    self._wait_for_page_load()

                    # 목표 페이지에서 상품 목록 다시 추출
                    structure = self.finder.analyze_product_list_structure()
                    organic_products = structure["organic_products"]

                    if not organic_products:
                        result.error_message = f"페이지 {target_page_num}에 상품이 없음"
                        return result

                    print(f"✅ 페이지 {target_page_num} 이동 완료 ({len(organic_products)}개 상품 확인)\n")

                # 순위 조작을 위해 all_products_params 업데이트
                all_products_params = self.finder.extract_all_products_params(organic_products)

                # Edit 모드에서는 목표 페이지에서 상품을 찾지 않음
                # 대신 목표 위치의 상품 element를 가져와서 원본 P/I/V를 덮어씌울 것
                print(f"   ℹ️  Edit 모드: 목표 페이지에서 상품 재발견 시도하지 않음")
                print(f"      원본 상품 정보를 목표 위치에 덮어씌울 예정\n")

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

            # 7. Edit 모드에서 다른 페이지로 이동한 경우 처리
            edit_mode_different_page = False
            target_element_for_replacement = None

            if self.enable_rank_manipulation and found_on_page and target_page_num and (found_on_page != target_page_num):
                edit_mode_different_page = True

                print(f"\n{'=' * 60}")
                print(f"🔄 Edit 모드: 다른 페이지로 이동 (P/I/V 덮어씌우기 모드)")
                print(f"{'=' * 60}")
                print(f"   원본 상품 위치: 페이지 {found_on_page}")
                print(f"   목표 페이지: {target_page_num}")
                print(f"   목표 순위: {min_rank}등\n")

                # 목표 위치의 상품 element 가져오기
                if target_page_info:
                    page_start_rank = target_page_info['rank_range'][0]
                    target_position_in_page = min_rank - page_start_rank  # 0-based index
                else:
                    # 추정 페이지인 경우
                    page_start_rank = (target_page_num - 1) * 27 + 1
                    target_position_in_page = min_rank - page_start_rank  # 0-based index

                # 범위 체크
                if 0 <= target_position_in_page < len(organic_products):
                    target_element_for_replacement = organic_products[target_position_in_page]
                    print(f"   ✓ 목표 위치의 상품 element 획득: 페이지 {target_page_num}의 {target_position_in_page + 1}번째")
                    print(f"   → 이 위치에 원본 상품(P/I/V)을 덮어씌울 예정\n")
                else:
                    print(f"   ⚠️  목표 위치({target_position_in_page + 1})가 범위를 벗어남\n")
                    result.error_message = f"목표 위치({target_position_in_page + 1})가 범위(1~{len(organic_products)})를 벗어남"
                    return result

            # 8. Edit 모드에서 다른 페이지로 이동한 경우: 전체 상품 내용 교체
            if edit_mode_different_page and target_element_for_replacement:
                print(f"\n{'=' * 60}")
                print(f"🔄 상품 전체 내용 교체 (이미지/제목/가격 + P/I/V)")
                print(f"{'=' * 60}\n")

                # 목표 위치 element의 워터마크 제거
                self._remove_watermark_from_element(target_element_for_replacement)

                # 원본 상품 정보 복사 및 순위 업데이트
                display_product_data = found_product.copy()
                display_product_data['rank'] = min_rank  # 목표 순위로 변경 (배지 표시용)

                print(f"   📊 교체할 상품 정보:")
                print(f"      원본 순위: {found_product.get('rank')}등")
                print(f"      표시할 순위: {min_rank}등")
                print(f"      상품명: {found_product.get('name', '')[:50]}...")
                print(f"      P/I/V: {found_product.get('product_id')} / {found_product.get('item_id')} / {found_product.get('vendor_item_id')}\n")

                # Step 1: 교체 전 상품에 하이라이트 적용 (사용자가 어떤 상품이 바뀔지 확인)
                print(f"   ✨ Step 1: 교체 전 상품 하이라이트 (목표 위치)")
                temp_display_data = {
                    'product_id': 'BEFORE',
                    'item_id': 'REPLACEMENT',
                    'vendor_item_id': 'TARGET',
                    'rank': min_rank
                }
                self._highlight_product(
                    element=target_element_for_replacement,
                    product_data=temp_display_data,
                    match_condition="교체 대상"
                )
                time.sleep(1.5)  # 사용자가 볼 시간

                # Step 2: 워터마크 제거
                print(f"\n   🧹 Step 2: 워터마크 제거")
                self._remove_watermark_from_element(target_element_for_replacement)

                # Step 3: 실제 DOM 내용 교체
                print(f"\n   🔄 Step 3: DOM 전체 교체 (이미지/제목/가격)")
                self._replace_product_content_by_data(
                    target_element=target_element_for_replacement,
                    source_data=found_product
                )

                # Step 4: DOM 교체 후 새로운 element 다시 찾기
                print(f"\n   🔍 Step 4: 교체 후 새 element 검색")
                time.sleep(0.5)  # DOM 업데이트 대기

                structure_after_replacement = self.finder.analyze_product_list_structure()
                organic_products_after = structure_after_replacement["organic_products"]

                if 0 <= target_position_in_page < len(organic_products_after):
                    new_target_element = organic_products_after[target_position_in_page]
                    print(f"   ✓ 새 element 획득 완료 (위치: {target_position_in_page + 1})")
                else:
                    print(f"   ⚠️  새 element를 찾을 수 없음")
                    new_target_element = target_element_for_replacement

                # 교체 후 하이라이트 재적용 (원본 상품 정보로)
                print(f"\n   ✨ Step 4-1: 교체 후 하이라이트 재적용")
                self._highlight_product(
                    element=new_target_element,
                    product_data=display_product_data,  # 목표 순위가 반영된 데이터
                    match_condition=match_condition
                )

                # Step 5: 스크롤하여 화면 중앙으로
                print(f"\n   📍 Step 5: 화면 중앙으로 스크롤")
                temp_product_info = {
                    "element": new_target_element,
                    "name": found_product['name'],
                    "rank": min_rank
                }
                self.finder.scroll_to_center(temp_product_info)

                # 스크린샷 캡처
                print("\n" + "=" * 60)
                print(f"📸 스크린샷 캡처 (목표 순위 {min_rank}등 위치)")
                print("=" * 60 + "\n")
                self._wait_for_page_load()

                result.before_screenshot, result.before_screenshot_url = self.screenshot_processor.capture_with_overlay(
                    keyword=keyword,
                    version=version,
                    overlay_text="",
                    full_page=False,
                    metadata=self._create_metadata(keyword, temp_product_info)
                )

                # Edit 모드에서 다른 페이지로 이동한 경우 순위 조작 불필요
                print(f"\n✅ Edit 모드 완료: P/I/V 덮어씌우기 + 워터마크 제거 + 스크린샷 캡처")
                result.success = True
                result.after_screenshot = result.before_screenshot
                result.after_screenshot_url = result.before_screenshot_url
                return result

            # 일반 모드 또는 같은 페이지 내 순위 조작
            # ⚠️  하이라이트는 순위 조작 후에만 적용 (순서: 스크린샷 → 순위 이동 → 하이라이트 → 스크린샷)
            # self._highlight_product()는 순위 조작 후에 호출됨

            self.finder.scroll_to_center(product_info)

            # 스크린샷 전 최종 안정화 대기
            print("\n" + "=" * 60)
            print("📸 변경 전 스크린샷 캡처 (하이라이트 없음)")
            print("=" * 60 + "\n")
            self._wait_for_page_load()

            # 스크린샷 + 오버레이 + 업로드 (하이라이트 없는 상태로)
            result.before_screenshot, result.before_screenshot_url = self.screenshot_processor.capture_with_overlay(
                keyword=keyword,
                version=version,
                overlay_text="",  # 오버레이 텍스트 제거 (썸네일에 P/I/V로 표시)
                full_page=False,
                metadata=self._create_metadata(keyword, product_info)
            )

            # 9. Edit 모드에서 순위 변환 (같은 페이지 내에서만)
            desired_rank_in_page = min_rank  # 기본값 (Edit 모드가 아닌 경우)

            # 같은 페이지 내에서만 순위 변환 실행
            if (self.enable_rank_manipulation and found_on_page and target_page_num and
                (found_on_page == target_page_num) and target_page_info and min_rank):
                # 목표 순위가 현재 페이지 범위에 속하는지 확인
                page_start_rank = target_page_info['rank_range'][0]
                page_end_rank = target_page_info['rank_range'][1]

                if page_start_rank <= min_rank <= page_end_rank:
                    # 페이지 내 상대 순위 계산 (1-based)
                    desired_rank_in_page = min_rank - page_start_rank + 1
                    print(f"\n📊 순위 변환:")
                    print(f"   전체 목표 순위: {min_rank}등")
                    print(f"   페이지 {target_page_num} 범위: {page_start_rank}~{page_end_rank}등")
                    print(f"   페이지 내 목표 순위: {desired_rank_in_page}등\n")
                else:
                    print(f"\n⚠️  경고: 목표 순위({min_rank})가 현재 페이지 범위({page_start_rank}~{page_end_rank})를 벗어남")
                    print(f"   페이지 내 첫 번째 위치로 이동합니다.\n")
                    desired_rank_in_page = 1

            # 9. 순위 변조 (활성화된 경우)
            if self.enable_rank_manipulation and min_rank:
                # 페이지 내 현재 순위 가져오기 (page_rank가 없으면 rank 사용)
                current_rank = found_product.get('page_rank', found_product['rank'])

                # 현재 순위와 목표 순위가 다르면 순위 조작 실행
                if current_rank != desired_rank_in_page:
                    print(f"\n⚠️  현재 순위({current_rank}등)와 목표 순위({desired_rank_in_page}등)가 다릅니다")
                    print(f"🔀 순위 조작을 시작합니다...")

                    # 순위 조작 실행 (페이지 내 로컬 순위 사용)
                    # target_product의 rank를 페이지 내 순위로 덮어쓰기
                    target_product_local_rank = found_product.copy()
                    target_product_local_rank['rank'] = current_rank  # 페이지 내 로컬 순위

                    success, error_msg = self.rank_manipulator.move_product_to_rank(
                        target_product=target_product_local_rank,
                        desired_rank=desired_rank_in_page,
                        all_products=all_products_params
                    )

                    if not success:
                        print(f"❌ 순위 조작 실패: {error_msg}")
                        result.error_message = f"순위 조작 실패: {error_msg}"
                        return result

                    # 순위 조작 후 새로운 순서 확인 (verify_new_order에서 출력 포함)
                    all_products_params_after = self.rank_manipulator.verify_new_order(all_products_params)

                    # 변경된 위치에서 상품 다시 찾기 (product_id와 item_id로 검색)
                    updated_product = None
                    for p in all_products_params_after:
                        # product_id와 item_id로 같은 상품 찾기
                        if (p.get('product_id') == found_product.get('product_id') and
                            p.get('item_id') == found_product.get('item_id')):
                            updated_product = p
                            print(f"\n✅ 순위 조작 후 상품 위치 확인:")
                            print(f"   페이지 내 새 순위: {p['rank']}등")
                            print(f"   페이지 내 목표 순위: {desired_rank_in_page}등")
                            if self.enable_rank_manipulation and found_on_page and target_page_info:
                                print(f"   전체 순위로 환산: {min_rank}등 (목표)")
                            if p['rank'] == desired_rank_in_page:
                                print(f"   ✅ 순위 이동 성공!")
                            else:
                                print(f"   ⚠️  경고: 예상 순위와 실제 순위가 다릅니다")
                            break

                    if not updated_product:
                        print(f"⚠️  순위 조작 후 상품을 찾을 수 없습니다")
                        print(f"   검색 조건: product_id={found_product.get('product_id')}, item_id={found_product.get('item_id')}")
                        result.error_message = "순위 조작 후 상품 찾기 실패"
                        return result

                    # 9. 변경 후 스크린샷 (새 위치에서 하이라이트 재적용)
                    print(f"\n{'=' * 60}")
                    if self.enable_rank_manipulation and found_on_page and target_page_info:
                        print(f"📸 순위 변경 후 스크린샷 캡처 (전체 순위: {min_rank}등, 페이지 내: {desired_rank_in_page}등)")
                    else:
                        print(f"📸 순위 변경 후 스크린샷 캡처 (새 위치: {min_rank}등)")
                    print(f"{'=' * 60}\n")

                    # 새 위치에 하이라이트 재적용 (전역 순위 사용)
                    updated_product_with_global_rank = updated_product.copy()
                    updated_product_with_global_rank['rank'] = min_rank  # 전역 순위로 덮어쓰기

                    self._highlight_product(
                        element=updated_product['element'],
                        product_data=updated_product_with_global_rank,
                        match_condition=match_condition
                    )

                    # 새 위치로 스크롤
                    updated_product_info = {
                        "name": updated_product['name'],
                        "rank": updated_product['rank'],
                        "link": updated_product['link'],
                        "element": updated_product['element'],
                        "price": "",
                        "rating": "",
                        "review_count": ""
                    }
                    self.finder.scroll_to_center(updated_product_info)

                    # 페이지 안정화 대기
                    self._wait_for_page_load()

                    # 변경 후 스크린샷 (업데이트된 정보 사용)
                    result.after_screenshot, result.after_screenshot_url = self.screenshot_processor.capture_with_overlay(
                        keyword=keyword,
                        version=version,
                        overlay_text="",
                        full_page=False,
                        metadata=self._create_metadata(keyword, updated_product_info)
                    )

                else:
                    print(f"\n✅ 현재 순위({current_rank}등)가 이미 목표 순위({min_rank}등)입니다")
                    print(f"   순위 조작을 건너뜁니다")

                    # 순위 이동이 없어도 하이라이트는 적용 후 "after" 스크린샷 촬영
                    print(f"\n{'=' * 60}")
                    print(f"📸 현재 위치 스크린샷 캡처 (순위 이동 없음)")
                    print(f"{'=' * 60}\n")

                    # 하이라이트 적용 (전역 순위 사용)
                    found_product_with_global_rank = found_product.copy()
                    found_product_with_global_rank['rank'] = min_rank  # 전역 순위로 덮어쓰기

                    self._highlight_product(
                        element=product_info['element'],
                        product_data=found_product_with_global_rank,
                        match_condition=match_condition
                    )

                    # 스크롤 및 안정화
                    self.finder.scroll_to_center(product_info)
                    self._wait_for_page_load()

                    # "after" 스크린샷 (하이라이트 적용된 상태)
                    result.after_screenshot, result.after_screenshot_url = self.screenshot_processor.capture_with_overlay(
                        keyword=keyword,
                        version=version,
                        overlay_text="",
                        full_page=False,
                        metadata=self._create_metadata(keyword, product_info)
                    )

            else:
                # 순위 변조가 비활성화되어 있는 경우: 하이라이트 적용 후 스크린샷
                print(f"\n{'=' * 60}")
                print(f"📸 스크린샷 캡처 (순위 변조 비활성화)")
                print(f"{'=' * 60}\n")

                # 하이라이트 적용 (전역 순위 사용)
                found_product_with_global_rank = found_product.copy()
                found_product_with_global_rank['rank'] = min_rank  # 전역 순위로 덮어쓰기

                self._highlight_product(
                    element=product_info['element'],
                    product_data=found_product_with_global_rank,
                    match_condition=match_condition
                )

                # 스크롤 및 안정화
                self.finder.scroll_to_center(product_info)
                self._wait_for_page_load()

                # "after" 스크린샷 (하이라이트 적용된 상태)
                result.after_screenshot, result.after_screenshot_url = self.screenshot_processor.capture_with_overlay(
                    keyword=keyword,
                    version=version,
                    overlay_text="",
                    full_page=False,
                    metadata=self._create_metadata(keyword, product_info)
                )

            # 10. Edit 모드 종합 로그
            self._log_edit_mode_summary(
                enable_rank_manipulation=self.enable_rank_manipulation,
                min_rank=min_rank,
                found_product=found_product,
                result=result
            )

            result.success = True
            return result

        except Exception as e:
            print(f"\n❌ 워크플로우 실행 실패: {e}")
            import traceback
            traceback.print_exc()
            result.error_message = str(e)
            return result

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

            # 3. 추가 2초 대기 (동적 콘텐츠 렌더링 완료 보장)
            print("⏳ 페이지 로딩 완료 - 2초 안정화 대기 중...")
            time.sleep(2)

            print("✅ 페이지 완전히 로드됨")
            return True

        except Exception as e:
            print(f"⚠️  페이지 로딩 대기 실패: {e}")
            # 실패해도 2초는 대기
            time.sleep(2)
            return False

    def _remove_watermark_from_element(self, element):
        """
        특정 element에서 워터마크 제거

        Args:
            element: 워터마크를 제거할 상품 요소 (WebElement)
        """
        try:
            js_code = """
            var element = arguments[0];

            // 워터마크 요소 찾기
            var watermark = element.querySelector('[class*="RankMark"]') ||
                            element.querySelector('[class*="rank"]') ||
                            element.querySelector('[class*="number"]');

            if (watermark && watermark.parentElement) {
                watermark.parentElement.removeChild(watermark);
                console.log('Watermark removed');
                return true;
            }
            return false;
            """

            removed = self.driver.execute_script(js_code, element)
            if removed:
                print(f"   ✓ 워터마크 제거 완료")
            else:
                print(f"   ℹ️  워터마크가 없음 (11등 이하 상품)")

        except Exception as e:
            print(f"   ⚠️  워터마크 제거 실패: {e}")

    def _add_rank_overlay(self, element, rank: int):
        """
        11등 이상 상품에 커스텀 순위 오버레이 추가

        1~10등 워터마크와 유사한 스타일로 생성

        Args:
            element: 순위 오버레이를 추가할 상품 요소 (WebElement)
            rank: 표시할 순위 (11 이상)
        """
        try:
            js_code = """
            var element = arguments[0];
            var rank = arguments[1];

            // 커스텀 순위 뱃지 생성 (쿠팡 워터마크 스타일 모방)
            var overlay = document.createElement('span');
            overlay.textContent = rank.toString();
            overlay.className = 'custom-rank-overlay';

            // 스타일 적용 (쿠팡 RankMark와 유사)
            overlay.style.position = 'absolute';
            overlay.style.top = '8px';
            overlay.style.left = '8px';
            overlay.style.width = '24px';
            overlay.style.height = '24px';
            overlay.style.borderRadius = '50%';
            overlay.style.backgroundColor = '#00A8FF';
            overlay.style.color = '#FFFFFF';
            overlay.style.fontSize = '12px';
            overlay.style.fontWeight = 'bold';
            overlay.style.display = 'flex';
            overlay.style.alignItems = 'center';
            overlay.style.justifyContent = 'center';
            overlay.style.zIndex = '100';
            overlay.style.fontFamily = 'sans-serif';
            overlay.style.lineHeight = '1';
            overlay.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';

            // 상품 요소 위치 설정
            element.style.position = 'relative';

            // 기존 오버레이 제거 (중복 방지)
            var existing = element.querySelector('.custom-rank-overlay');
            if (existing) {
                existing.remove();
            }

            // 맨 앞에 삽입
            element.insertBefore(overlay, element.firstChild);

            console.log('Custom rank overlay created:', rank);
            return true;
            """

            self.driver.execute_script(js_code, element, rank)

        except Exception as e:
            print(f"   ⚠️  순위 오버레이 생성 실패: {e}")

    def _replace_product_content_by_data(self, target_element, source_data: Dict):
        """
        목표 위치의 상품 내용을 원본 상품 데이터로 교체

        found_product 딕셔너리에서 추출한 데이터를 사용하여 교체
        (stale element 문제 해결)

        교체 전략:
        1. source_data에 'outerHTML'이 있으면 → 전체 <li> 요소 교체 (다른 페이지 시나리오)
        2. 없으면 → 텍스트/링크만 교체 (폴백)

        Args:
            target_element: 교체될 대상 상품 요소 (WebElement)
            source_data: 원본 상품 데이터 딕셔너리 (outerHTML, name, link 포함)
        """
        try:
            print(f"   🔄 DOM 내용 교체 시작 (데이터 기반)...")

            # 전략 1: 전체 DOM 교체 (outerHTML이 있을 경우)
            source_outer_html = source_data.get('outerHTML')
            if source_outer_html:
                print(f"      전략: 전체 <li> DOM 교체 (백업된 outerHTML 사용)")
                print(f"      백업 DOM 크기: {len(source_outer_html)} 문자")

                js_code = """
                var targetEl = arguments[0];
                var sourceHTML = arguments[1];

                // 전체 <li> 요소를 원본 HTML로 교체
                targetEl.outerHTML = sourceHTML;

                return {
                    success: true,
                    method: 'full_dom_replacement',
                    html_length: sourceHTML.length
                };
                """

                result = self.driver.execute_script(js_code, target_element, source_outer_html)

                if result and result.get('success'):
                    print(f"   ✅ 전체 DOM 교체 완료 (방법: {result.get('method')})")
                    print(f"      HTML 길이: {result.get('html_length')} 문자")
                else:
                    print(f"   ⚠️  DOM 교체 실패")

                return

            # 전략 2: 텍스트/링크만 교체 (폴백)
            print(f"      전략: 텍스트/링크 교체 (outerHTML 없음)")
            source_name = source_data.get('name', '')
            source_link = source_data.get('link', '')

            js_code = """
            var targetEl = arguments[0];
            var sourceName = arguments[1];
            var sourceLink = arguments[2];

            var changes = [];

            // 1. 상품명 교체
            var targetName = targetEl.querySelector('.name') ||
                             targetEl.querySelector('[class*="productName"]') ||
                             targetEl.querySelector('div.descriptions');

            if (targetName && sourceName) {
                targetName.textContent = sourceName;
                changes.push('상품명 교체: ' + sourceName.substring(0, 30) + '...');
            }

            // 2. 상품 링크 교체 (a 태그의 href)
            var targetLink = targetEl.querySelector('a[href*="/vp/products/"]') ||
                            targetEl.querySelector('a[href]');

            if (targetLink && sourceLink) {
                targetLink.href = sourceLink;
                changes.push('링크 교체: ' + sourceLink.substring(0, 50) + '...');
            }

            console.log('Content replacement completed:', changes);
            return {
                success: true,
                changes: changes
            };
            """

            result = self.driver.execute_script(js_code, target_element, source_name, source_link)

            if result and result.get('success'):
                print(f"   ✅ DOM 내용 교체 완료:")
                for change in result.get('changes', []):
                    print(f"      - {change}")
            else:
                print(f"   ⚠️  일부 내용 교체 실패")

        except Exception as e:
            print(f"   ❌ DOM 내용 교체 실패: {e}")
            import traceback
            traceback.print_exc()

    def _highlight_product(self, element, product_data: Dict, match_condition: str):
        """
        상품 강조 표시 (프리셋 기반)

        Args:
            element: 강조할 상품 요소
            product_data: 상품 데이터 (product_id, item_id, vendor_item_id, rank 포함)
            match_condition: 매칭 조건 (어떤 값이 일치했는지)
        """
        try:
            product_rank = product_data.get('rank', 0)

            # JavaScript 코드 생성 (테두리)
            js_code = generate_highlight_js(
                element_selector="element",
                style=self.highlight_style,
                product_data=product_data,
                match_condition=match_condition
            )

            # 테두리 적용
            self.driver.execute_script(js_code, element)

            print(f"✅ 상품 강조 표시 완료 (프리셋: {self.highlight_preset})")
            print(f"   매칭 정보: {match_condition}")

            # 11등 이상이면 커스텀 순위 오버레이 추가
            if product_rank and product_rank > 10:
                print(f"   🔢 {product_rank}등 → 커스텀 순위 오버레이 생성 중...")
                self._add_rank_overlay(element, product_rank)
                print(f"      ✓ 순위 오버레이 '{product_rank}' 생성 완료")

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

    def _create_metadata(self, keyword: str, product_info: Dict) -> Dict[str, Any]:
        """업로드용 메타데이터 생성"""
        url_params = self.finder.extract_url_params(product_info.get('link', ''))
        return {
            'keyword': keyword,
            'product_id': url_params['product_id'],
            'item_id': url_params['item_id'],
            'vendor_item_id': url_params['vendor_item_id'],
            'rank': str(product_info.get('rank', 'unknown'))
        }

    def _log_edit_mode_summary(
        self,
        enable_rank_manipulation: bool,
        min_rank: Optional[int],
        found_product: Dict,
        result: SearchWorkflowResult
    ):
        """
        Edit 모드 종합 로그 출력

        Args:
            enable_rank_manipulation: 순위 조작 활성화 여부
            min_rank: 목표 순위
            found_product: 발견된 상품 정보
            result: 워크플로우 실행 결과
        """
        print(f"\n{'=' * 60}")
        print(f"📊 최종 결과 요약 (Final Summary)")
        print(f"{'=' * 60}")

        # Edit 모드 상태
        if enable_rank_manipulation:
            mode_name = "Simple Swap (v2)" if self.edit_mode == "edit2" else "DOM Reconstruction (v1)"
            flag_name = "--edit2" if self.edit_mode == "edit2" else "--edit"
            print(f"   Edit 모드: ✅ 활성화 ({flag_name} 플래그 사용 - {mode_name})")
        else:
            print(f"   Edit 모드: ⏸️  비활성화 (--edit/--edit2 플래그 없음)")
            print(f"{'=' * 60}\n")
            return

        # min_rank 확인
        if not min_rank:
            print(f"   목표 순위: ⚠️  미지정 (min_rank 없음)")
            print(f"   변경 여부: ⏭️  순위 조작 건너뜀")
            print(f"{'=' * 60}\n")
            return

        # 상품 기본 정보
        original_rank = found_product.get('rank')
        product_name = found_product.get('name', 'Unknown')
        product_id = found_product.get('product_id', 'N/A')
        item_id = found_product.get('item_id', 'N/A')
        vendor_item_id = found_product.get('vendor_item_id', 'N/A')

        print(f"\n📦 상품 정보:")
        print(f"   상품명: {product_name[:60]}{'...' if len(product_name) > 60 else ''}")
        print(f"   Product ID: {product_id}")
        print(f"   Item ID: {item_id}")
        print(f"   Vendor Item ID: {vendor_item_id}")

        # 순위 변경 정보
        print(f"\n🔄 순위 변경 정보:")
        print(f"   원래 순위: {original_rank}등")
        print(f"   목표 순위: {min_rank}등")

        # 페이지 정보 추가 (result에 저장된 정보 활용)
        if hasattr(result, 'found_on_page') and result.found_on_page:
            print(f"   발견 페이지: {result.found_on_page}")
        if hasattr(result, 'target_page') and result.target_page:
            print(f"   목표 페이지: {result.target_page}")

        # 변경 여부 판단
        print(f"\n📸 스크린샷:")
        if original_rank == min_rank:
            # 순위 변경 불필요
            print(f"   상태: ⏭️  변경 불필요 (이미 목표 순위에 위치)")
            print(f"   스크린샷: {result.before_screenshot if result.before_screenshot else '❌ 캡처 실패'}")
            if result.before_screenshot_url:
                print(f"   업로드: {result.before_screenshot_url}")

        elif result.after_screenshot:
            # 순위 변경 성공
            print(f"   상태: ✅ 순위 변경 성공 ({original_rank}등 → {min_rank}등)")
            print(f"   변경 전: {result.before_screenshot}")
            print(f"   변경 후: {result.after_screenshot}")

            if result.before_screenshot_url:
                print(f"   변경 전 업로드: {result.before_screenshot_url}")
            if result.after_screenshot_url:
                print(f"   변경 후 업로드: {result.after_screenshot_url}")

        else:
            # 순위 변경 시도했으나 실패
            print(f"   상태: ❌ 변경 실패")
            if result.error_message:
                print(f"   실패 원인: {result.error_message}")
            print(f"   변경 전 스크린샷: {result.before_screenshot if result.before_screenshot else '❌ 캡처 실패'}")

        # 매칭 조건 추가
        if result.match_condition:
            print(f"\n🎯 매칭 조건: {result.match_condition}")

        print(f"{'=' * 60}\n")

    def _save_debug_info(
        self,
        page_history: list,
        found_product: dict,
        keyword: str,
        product_id: str,
        item_id: str,
        vendor_item_id: str
    ):
        """
        디버그 정보를 JSON 파일로 저장

        Args:
            page_history: 페이지별 정보 리스트
            found_product: 발견한 상품 정보
            keyword: 검색 키워드
            product_id: 상품 ID
            item_id: 아이템 ID
            vendor_item_id: 판매자 아이템 ID
        """
        try:
            # 디버그 디렉토리 생성
            debug_dir = Path("debug_logs")
            debug_dir.mkdir(exist_ok=True)

            # 타임스탬프
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 디버그 정보 구성
            debug_data = {
                "timestamp": timestamp,
                "keyword": keyword,
                "product_info": {
                    "product_id": product_id,
                    "item_id": item_id,
                    "vendor_item_id": vendor_item_id,
                    "found_rank": found_product.get('rank'),
                    "found_on_page": None
                },
                "page_history": []
            }

            # 페이지 히스토리 저장 (element 제외)
            for page_info in page_history:
                debug_data["page_history"].append({
                    "page": page_info['page'],
                    "url": page_info['url'],
                    "product_count": page_info['product_count'],
                    "rank_start": page_info['rank_range'][0],
                    "rank_end": page_info['rank_range'][1]
                })

                # 발견한 페이지 확인
                rank_start, rank_end = page_info['rank_range']
                if rank_start <= found_product.get('rank', 0) <= rank_end:
                    debug_data["product_info"]["found_on_page"] = page_info['page']

            # JSON 파일로 저장
            filename = f"{timestamp}_{keyword}_{product_id}_{item_id}_{vendor_item_id}.json"
            filepath = debug_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, ensure_ascii=False, indent=2)

            print(f"\n📝 디버그 정보 저장 완료: {filepath}")
            print(f"{'=' * 60}")
            print(f"페이지 히스토리 요약:")
            for page_info in debug_data["page_history"]:
                print(f"  페이지 {page_info['page']}: {page_info['rank_start']}~{page_info['rank_end']}등 ({page_info['product_count']}개)")
            print(f"발견 위치:")
            print(f"  페이지: {debug_data['product_info']['found_on_page']}")
            print(f"  순위: {debug_data['product_info']['found_rank']}등")
            print(f"{'=' * 60}\n")

        except Exception as e:
            print(f"⚠️  디버그 정보 저장 실패: {e}")
            import traceback
            traceback.print_exc()

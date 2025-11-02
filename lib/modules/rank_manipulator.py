#!/usr/bin/env python3
"""
순위 조작 모듈
DOM 조작을 통해 검색 결과 상품의 순위를 변경
"""

from typing import Optional, Dict, List, Tuple
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By


class RankManipulator:
    """상품 순위 조작 클래스 (DOM 재배치)"""

    def __init__(self, driver, product_finder):
        """
        Args:
            driver: Selenium WebDriver
            product_finder: ProductFinder 인스턴스
        """
        self.driver = driver
        self.finder = product_finder

    def move_product_to_rank(
        self,
        target_product: Dict,
        desired_rank: int,
        all_products: List[Dict]
    ) -> Tuple[bool, Optional[str]]:
        """
        상품을 원하는 순위로 이동 (광고 고정 + 일반 상품 끼워넣기)

        Args:
            target_product: 이동할 상품 정보 (element, rank 포함)
            desired_rank: 목표 순위 (예: 3)
            all_products: 전체 일반 상품 리스트 (광고 제외)

        Returns:
            (성공 여부, 에러 메시지)
        """
        try:
            current_rank = target_product['rank']

            print(f"\n{'=' * 60}")
            print(f"🔀 순위 조작 시작 (광고 고정 방식)")
            print(f"{'=' * 60}")
            print(f"현재 순위: {current_rank}등")
            print(f"목표 순위: {desired_rank}등")
            print(f"상품명: {target_product['name'][:50]}...")
            print(f"{'=' * 60}\n")

            # 1. 같은 순위면 이동 불필요
            if current_rank == desired_rank:
                print(f"✅ 이미 목표 순위({desired_rank}등)에 있습니다")
                return (True, None)

            # 2. 목표 순위가 범위를 벗어나는지 체크
            if desired_rank < 1 or desired_rank > len(all_products):
                error_msg = f"목표 순위({desired_rank})가 유효 범위(1~{len(all_products)})를 벗어남"
                print(f"❌ {error_msg}")
                return (False, error_msg)

            # 3. 전체 DOM 구조 분석 (광고 + 일반 상품)
            structure = self.finder.analyze_product_list_structure()

            print(f"📊 DOM 구조:")
            print(f"   - 전체 상품: {len(structure['all_items'])}개")
            print(f"   - 일반 상품: {len(all_products)}개")

            # 4. 일반 상품 재정렬 (target_product를 desired_rank로 이동)
            reordered_products = self._reorder_organic_products(
                all_products,
                target_product,
                current_rank,
                desired_rank
            )

            # 5. 광고와 재정렬된 일반 상품을 합쳐서 최종 DOM 순서 생성
            success = self._rebuild_dom_with_fixed_ads(
                structure,
                reordered_products
            )

            if success:
                print(f"\n✅ 순위 이동 완료: {current_rank}등 → {desired_rank}등")

                # DOM 재배치 후 워터마크 재정립
                # 기존 워터마크를 모두 제거하고 새 순서에 맞게 재생성
                self._reapply_rank_watermarks(all_products)

                return (True, None)
            else:
                return (False, "DOM 조작 실패")

        except Exception as e:
            import traceback
            traceback.print_exc()
            return (False, str(e))

    def _reorder_organic_products(
        self,
        all_products: List[Dict],
        target_product: Dict,
        current_rank: int,
        desired_rank: int
    ) -> List[Dict]:
        """
        일반 상품만 재정렬 (광고 제외)

        Args:
            all_products: 전체 일반 상품 리스트 (광고 제외)
            target_product: 이동할 상품
            current_rank: 현재 순위 (1-based)
            desired_rank: 목표 순위 (1-based)

        Returns:
            재정렬된 일반 상품 리스트
        """
        # 리스트 복사 (원본 유지)
        reordered = all_products.copy()

        # 현재 위치에서 제거 (1-based → 0-based)
        reordered.pop(current_rank - 1)

        # 목표 위치에 삽입 (1-based → 0-based)
        reordered.insert(desired_rank - 1, target_product)

        print(f"\n🔄 일반 상품 재정렬:")
        print(f"   - {current_rank}등 상품을 {desired_rank}등으로 이동")
        print(f"   - 재정렬 후 상위 5개:")
        for i, p in enumerate(reordered[:5], 1):
            print(f"      {i}등: {p['name'][:40]}...")

        return reordered

    def _rebuild_dom_with_fixed_ads(
        self,
        structure: Dict,
        reordered_products: List[Dict]
    ) -> bool:
        """
        광고를 고정하고 재정렬된 일반 상품으로 DOM 재구성

        전략:
        1. structure['items_info']에서 광고 위치 확인
        2. 광고는 원래 DOM 인덱스 유지
        3. 일반 상품은 재정렬된 순서대로 빈 자리에 배치
        4. 모든 요소를 순차적으로 재배치

        Args:
            structure: analyze_product_list_structure()의 결과
            reordered_products: 재정렬된 일반 상품 리스트

        Returns:
            성공 여부
        """
        try:
            items_info = structure['items_info']
            all_items = structure['all_items']

            print(f"\n🔨 DOM 재구성 시작...")
            print(f"   - 전체 항목: {len(all_items)}개")
            print(f"   - 광고: {sum(1 for item in items_info if item.get('is_ad'))}개")

            # 재정렬된 일반 상품의 인덱스
            organic_idx = 0

            # DOM 컨테이너 찾기
            container = all_items[0].find_element(By.XPATH, "..")  # 부모 요소 (#product-list)

            # 디버깅: items_info 순서 확인
            print(f"\n   📋 items_info 순서 (처음 5개):")
            for i, info in enumerate(items_info[:5]):
                print(f"      [{i}] dom_index={info.get('dom_index')}, is_ad={info.get('is_ad')}, type={info.get('type')}")

            # 새로운 전략:
            # 1단계 - 일반 상품을 먼저 모두 추가
            # 2단계 - 광고를 원래 위치에 삽입

            print(f"\n   1️⃣  1단계: 일반 상품 추가 중...")

            # 1단계: 일반 상품 먼저 모두 추가
            for product in reordered_products:
                element = product['element']
                self.driver.execute_script(
                    "arguments[0].appendChild(arguments[1]);",
                    container,
                    element
                )

            print(f"      ✓ 일반 상품 {len(reordered_products)}개 추가 완료")

            # 2단계: 광고를 원래 위치에 삽입
            print(f"\n   2️⃣  2단계: 광고를 원래 위치에 삽입 중...")

            # 광고 정보 수집 및 정렬
            ads = []
            for item_info in items_info:
                if item_info.get('is_ad'):
                    dom_idx = item_info['dom_index']
                    element = all_items[dom_idx]
                    ads.append({
                        'dom_index': dom_idx,
                        'element': element,
                        'type': item_info.get('type', '광고')
                    })

            # DOM 인덱스 기준으로 정렬 (앞에서부터 삽입)
            ads.sort(key=lambda x: x['dom_index'])

            # 광고를 원래 위치에 삽입
            for ad in ads:
                dom_idx = ad['dom_index']
                element = ad['element']
                element_type = ad['type']

                # 현재 container의 자식 요소들
                current_children = self.driver.execute_script(
                    "return arguments[0].children;",
                    container
                )

                # 삽입 위치 (원래 DOM 인덱스)
                if dom_idx < len(current_children):
                    # 중간에 삽입
                    self.driver.execute_script(
                        "arguments[0].insertBefore(arguments[1], arguments[2]);",
                        container,
                        element,
                        current_children[dom_idx]
                    )
                    print(f"      ✓ {element_type} → 원본 위치 {dom_idx}에 삽입")
                else:
                    # 맨 끝에 추가
                    self.driver.execute_script(
                        "arguments[0].appendChild(arguments[1]);",
                        container,
                        element
                    )
                    print(f"      ✓ {element_type} → 마지막에 추가 (원본 위치 {dom_idx})")

            print(f"\n   ✅ 2단계 완료: 광고 {len(ads)}개 삽입 완료")
            print(f"✅ DOM 재구성 완료 (일반 {len(reordered_products)}개 + 광고 {len(ads)}개)")
            return True

        except Exception as e:
            print(f"❌ DOM 재구성 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _move_element_before(
        self,
        moving_element: WebElement,
        target_element: WebElement
    ) -> bool:
        """
        moving_element를 target_element 앞에 삽입

        Args:
            moving_element: 이동할 요소
            target_element: 기준 요소 (이 요소 앞에 삽입)

        Returns:
            성공 여부
        """
        try:
            # JavaScript로 DOM 조작
            js_code = """
            var movingElement = arguments[0];
            var targetElement = arguments[1];

            // targetElement의 부모 노드에서 targetElement 앞에 movingElement 삽입
            targetElement.parentNode.insertBefore(movingElement, targetElement);

            return true;
            """

            result = self.driver.execute_script(js_code, moving_element, target_element)
            return result

        except Exception as e:
            print(f"❌ Element 이동 실패 (before): {e}")
            return False

    def _move_element_after(
        self,
        moving_element: WebElement,
        target_element: WebElement
    ) -> bool:
        """
        moving_element를 target_element 뒤에 삽입

        Args:
            moving_element: 이동할 요소
            target_element: 기준 요소 (이 요소 뒤에 삽입)

        Returns:
            성공 여부
        """
        try:
            # JavaScript로 DOM 조작
            js_code = """
            var movingElement = arguments[0];
            var targetElement = arguments[1];

            // targetElement 다음 형제 요소를 찾음
            var nextSibling = targetElement.nextSibling;

            if (nextSibling) {
                // 다음 형제가 있으면 그 앞에 삽입
                targetElement.parentNode.insertBefore(movingElement, nextSibling);
            } else {
                // 다음 형제가 없으면 부모의 마지막에 추가
                targetElement.parentNode.appendChild(movingElement);
            }

            return true;
            """

            result = self.driver.execute_script(js_code, moving_element, target_element)
            return result

        except Exception as e:
            print(f"❌ Element 이동 실패 (after): {e}")
            return False

    def _reapply_rank_watermarks(self, all_products: List[Dict]):
        """
        DOM 재배치 후 순위 워터마크 재정립

        전략:
        1. 기존 1~10등 워터마크 백업 (첫 번째 상품에서 스타일 추출)
        2. 모든 상품에서 워터마크 제거
        3. 새로운 1~10등 위치에 워터마크 재생성

        Args:
            all_products: 재배치 전 상품 리스트 (DOM 순서는 이미 변경됨)
        """
        try:
            print(f"\n🔄 순위 워터마크 재정립 시작...")

            # Step 1: 워터마크 샘플 백업 (1등 상품에서 스타일 추출)
            watermark_style = self._backup_watermark_style(all_products)

            if not watermark_style:
                print(f"   ⚠️  워터마크 스타일을 찾을 수 없습니다 - 재정립 건너뜀")
                return

            # Step 2: 모든 기존 워터마크 제거
            removed_count = self._remove_all_watermarks(all_products)
            print(f"   ✓ {removed_count}개 기존 워터마크 제거 완료")

            # Step 3: DOM에서 현재 순서대로 상품 다시 가져오기
            structure = self.finder.analyze_product_list_structure()
            current_order_elements = structure['organic_products']  # 현재 DOM 순서

            # Step 4: 새로운 1~10등에 워터마크 재생성
            created_count = self._create_new_watermarks(
                current_order_elements[:10],  # 상위 10개만
                watermark_style
            )
            print(f"   ✓ {created_count}개 새 워터마크 생성 완료")

            print(f"✅ 워터마크 재정립 완료 (제거: {removed_count}, 생성: {created_count})\n")

        except Exception as e:
            print(f"⚠️  워터마크 재정립 중 오류: {e}")
            import traceback
            traceback.print_exc()

    def _backup_watermark_style(self, all_products: List[Dict]) -> Optional[Dict]:
        """
        1~10등 상품의 워터마크 클래스명과 스타일 백업

        중요: 쿠팡 워터마크는 RankMark_rank1__xxx, RankMark_rank2__xxx 처럼
        클래스명 자체에 순위가 포함되어 있으므로 모든 클래스를 백업해야 함

        Returns:
            {
                'rank_classes': ['rank1_class', 'rank2_class', ..., 'rank10_class'],
                'tagName': 'span',
                'fontSize': '...',
                ...
            }
        """
        try:
            if not all_products:
                return None

            # 모든 1~10등 상품에서 워터마크 클래스 수집
            # ⚠️  중요: 워터마크를 위치 순서가 아닌 텍스트 내용 기준으로 정렬
            js_code = """
            var products = arguments[0];  // 1~10등 상품 element 배열
            var rankClasses = new Array(10).fill(null);  // 1~10등 슬롯
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
                        console.log('Backup watermark: rank ' + rankNum + ' -> ' + watermark.className);
                    } else {
                        // 순위가 유효하지 않으면 위치 기준으로 저장 (fallback)
                        rankClasses[i] = watermark.className;
                        console.log('Backup watermark (fallback): position ' + i + ' -> ' + watermark.className);
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
                // 워터마크 없으면 null로 유지 (이미 fill(null)로 초기화됨)
            }

            if (commonStyle) {
                commonStyle.rankClasses = rankClasses;
                return commonStyle;
            }

            return null;
            """

            # 1~10등 element 배열 전달
            elements = [p['element'] for p in all_products[:10]]
            style_info = self.driver.execute_script(js_code, elements)

            if style_info and style_info.get('rankClasses'):
                rank_classes = style_info['rankClasses']
                valid_classes = [c for c in rank_classes if c]
                print(f"   ✓ 워터마크 스타일 백업 완료 ({len(valid_classes)}개 클래스)")
                print(f"      예시: {valid_classes[0] if valid_classes else 'N/A'}")
                return style_info
            else:
                print(f"   ⚠️  워터마크를 찾을 수 없음 (1~10등 외 상품일 수 있음)")
                return None

        except Exception as e:
            print(f"   ⚠️  워터마크 스타일 백업 실패: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _remove_all_watermarks(self, all_products: List[Dict]) -> int:
        """
        모든 상품에서 워터마크 제거

        Returns:
            제거된 워터마크 개수
        """
        removed_count = 0

        js_code = """
        var element = arguments[0];

        // 워터마크 요소 찾기 (다양한 선택자 시도)
        var watermark = element.querySelector('[class*="number"]') ||
                        element.querySelector('[class*="rank"]') ||
                        element.querySelector('[class*="Rank"]') ||
                        element.querySelector('span[class*="badge"]');

        if (watermark) {
            console.log('Found watermark:', watermark.className, 'text:', watermark.textContent);
            if (watermark.parentElement) {
                watermark.parentElement.removeChild(watermark);
                console.log('Removed watermark');
                return {removed: true, className: watermark.className, text: watermark.textContent};
            }
        } else {
            console.log('No watermark found in element');
        }
        return {removed: false};
        """

        for idx, product in enumerate(all_products[:10], 1):  # 1~10등만 워터마크가 있음
            try:
                result = self.driver.execute_script(js_code, product['element'])
                if result and result.get('removed'):
                    removed_count += 1
                    print(f"   ✓ {idx}등 워터마크 제거: '{result.get('text')}' (class: {result.get('className')})")
                else:
                    print(f"   ⚠️  {idx}등 워터마크 없음 (11등 이하일 수 있음)")
            except Exception as e:
                print(f"   ⚠️  {idx}등 워터마크 제거 실패: {e}")

        return removed_count

    def _create_new_watermarks(
        self,
        product_elements: List,
        style_info: Dict
    ) -> int:
        """
        새로운 순서에 맞게 워터마크 생성

        중요: 백업한 rankClasses[0]을 새 1등에, rankClasses[1]을 새 2등에 적용

        Args:
            product_elements: 현재 DOM 순서의 상위 10개 상품 (WebElement 리스트)
            style_info: 백업된 워터마크 스타일 정보 (rankClasses 포함)

        Returns:
            생성된 워터마크 개수
        """
        created_count = 0
        rank_classes = style_info.get('rankClasses', [])

        for rank, element in enumerate(product_elements, 1):
            try:
                # rank 인덱스는 0-based (rank 1 → index 0)
                class_index = rank - 1

                if class_index >= len(rank_classes) or not rank_classes[class_index]:
                    print(f"   ⚠️  {rank}등 워터마크 클래스 없음 (백업 실패)")
                    continue

                # 해당 순위의 원본 클래스명 사용
                rank_class_name = rank_classes[class_index]

                js_code = """
                var element = arguments[0];
                var rankNum = arguments[1];
                var rankClassName = arguments[2];  // 원본 클래스명 (예: "RankMark_rank1__xxx")
                var style = arguments[3];

                console.log('Creating watermark for rank:', rankNum, 'with class:', rankClassName);

                // 기존 워터마크가 남아있는지 확인 후 제거
                var existingWatermark = element.querySelector('[class*="RankMark"]') ||
                                       element.querySelector('[class*="rank"]') ||
                                       element.querySelector('[class*="number"]');
                if (existingWatermark && existingWatermark.parentElement) {
                    existingWatermark.parentElement.removeChild(existingWatermark);
                    console.log('Removed existing watermark');
                }

                // 워터마크 생성
                var watermark = document.createElement(style.tagName || 'span');
                watermark.className = rankClassName;  // 원본 클래스명 사용
                watermark.textContent = rankNum.toString();

                // 인라인 스타일은 최소화 (CSS 클래스로 대부분 처리됨)
                // 필요한 스타일만 fallback으로 적용
                if (!watermark.style.position || watermark.style.position === 'static') {
                    watermark.style.position = style.position || 'absolute';
                }

                // 상품 요소에 추가
                element.style.position = 'relative';
                element.insertBefore(watermark, element.firstChild);

                console.log('Watermark created:', rankNum, 'class:', watermark.className, 'text:', watermark.textContent);
                return true;
                """

                # rank, 클래스명, 스타일 전달
                created = self.driver.execute_script(js_code, element, rank, rank_class_name, style_info)
                if created:
                    created_count += 1
                    print(f"   ✓ {rank}등 워터마크 생성 완료 (class: {rank_class_name[:30]}...)")

            except Exception as e:
                print(f"   ⚠️  {rank}등 워터마크 생성 실패: {e}")
                import traceback
                traceback.print_exc()

        return created_count

    def verify_new_order(self, all_products: List[Dict]) -> List[Dict]:
        """
        DOM 재배치 후 실제 순서 확인

        Args:
            all_products: 재배치 전 상품 리스트

        Returns:
            재배치 후 새로운 순서의 상품 리스트 (딕셔너리 리스트)
        """
        try:
            print(f"\n🔍 재배치 후 순서 확인 중...")

            # DOM에서 현재 순서대로 상품 요소들 다시 가져오기
            structure = self.finder.analyze_product_list_structure()
            new_organic_products_elements = structure['organic_products']  # WebElement 리스트

            # WebElement 리스트를 딕셔너리 리스트로 변환
            new_organic_products = self.finder.extract_all_products_params(new_organic_products_elements)

            print(f"✅ 재배치 확인 완료: {len(new_organic_products)}개 일반 상품\n")

            return new_organic_products

        except Exception as e:
            print(f"❌ 재배치 확인 실패: {e}")
            import traceback
            traceback.print_exc()
            return all_products

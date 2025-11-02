#!/usr/bin/env python3
"""
상품 검색 및 화면 중앙 정렬 모듈
쿠팡 검색 결과에서 특정 순위의 상품을 찾아 화면 중앙에 위치시킴
"""

import time
import re
from typing import Optional, Dict, List, Tuple
from urllib.parse import urlparse, parse_qs
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


class ProductFinder:
    """쿠팡 검색 결과에서 특정 순위의 상품을 찾고 화면 중앙에 위치시키는 클래스"""

    def __init__(self, driver):
        """
        Args:
            driver: Selenium WebDriver 인스턴스
        """
        self.driver = driver
        self._highlighted_element = None  # 현재 하이라이트된 요소 추적
        self._original_styles = {}  # 원본 스타일 저장

    def analyze_product_list_structure(self) -> Dict:
        """
        #product-list 내부의 전체 구조를 분석
        광고와 일반 제품의 위치를 파악

        Returns:
            {
                "all_items": List[WebElement],  # 전체 li 요소
                "items_info": List[Dict],  # 각 항목의 정보 (is_ad, dom_index, rank)
                "organic_products": List[WebElement],  # 광고 제외 제품만
                "organic_dom_indices": List[int]  # 광고 제외 제품의 DOM 인덱스
            }
        """
        try:
            # 전체 li 요소 추출 (베스트셀러 영역 제외)
            # 1. data-id 속성이 있는 일반 상품 리스트
            all_items = self.driver.find_elements(By.CSS_SELECTOR, "#product-list > li[data-id]")

            if not all_items:
                # 2. data-id가 없으면 전체 li 가져오기 (특수 섹션도 포함)
                # ⚠️ 중요: 특수 섹션을 제외하면 DOM 재배치 시 순서가 꼬임!
                # 특수 섹션은 포함시키되, 아래 로직에서 is_ad=True로 표시하여 원위치 유지
                all_items = self.driver.find_elements(By.CSS_SELECTOR, "#product-list > li")

                print(f"   ⚠️  data-id 없음 - 전체 li 요소 사용 (특수 섹션 포함)")

            print(f"\n🔍 DOM 구조 분석:")
            print(f"   전체 li 개수: {len(all_items)}")

            # 디버깅: 모든 li의 class 출력 (처음 10개)
            if len(all_items) > 0:
                print(f"\n   📋 처음 10개 항목의 class 속성 (디버깅):")
                for i, item in enumerate(all_items[:10]):
                    item_class = item.get_attribute('class') or '(없음)'
                    # ProductUnit 포함 여부 표시
                    has_product_unit = 'ProductUnit' in item_class or 'productUnit' in item_class
                    marker = "✅" if has_product_unit else "❌"
                    print(f"      [{i}] {marker} class=\"{item_class[:80]}...\"" if len(item_class) > 80 else f"      [{i}] {marker} class=\"{item_class}\"")

            items_info = []
            organic_products = []
            organic_dom_indices = []
            organic_rank = 0  # 광고 제외 순위
            ad_rank = 0  # 광고 순위

            for dom_index, item in enumerate(all_items):
                try:
                    # 🔑 전략 1: class 기반으로 특수 섹션 먼저 체크
                    item_class = item.get_attribute('class') or ''
                    item_class_lower = item_class.lower()

                    # 특수 섹션 키워드
                    special_section_keywords = ['best-seller', 'limited-time-offer', 'time-deal', 'special-offer']
                    is_special_section = any(keyword in item_class_lower for keyword in special_section_keywords)

                    if is_special_section:
                        # 특수 섹션 → 원위치 고정
                        section_type = next((kw for kw in special_section_keywords if kw in item_class_lower), 'unknown')
                        items_info.append({
                            "dom_index": dom_index,
                            "is_ad": True,  # 광고로 표시하여 원위치 유지
                            "rank": None,
                            "type": f"특수섹션({section_type})",
                            'product_id': None,
                            'item_id': None,
                            'vendor_item_id': None
                        })
                        print(f"   [전체:{dom_index+1:2d}] 특수 섹션 감지 ({section_type}) - 원위치 유지")
                        continue

                    # 🔑 전략 2: 상품 링크 체크
                    link = None
                    try:
                        link_elem = item.find_element(By.CSS_SELECTOR, 'a[href*="/vp/products/"]')
                        link = link_elem.get_attribute("href")
                    except:
                        try:
                            link_elem = item.find_element(By.CSS_SELECTOR, "a.search-product-link")
                            link = link_elem.get_attribute("href")
                        except:
                            pass

                    # 링크가 없으면 특수 섹션 (class 체크를 통과한 경우)
                    if not link:
                        is_product_unit = 'productunit' in item_class_lower or 'product-unit' in item_class_lower

                        items_info.append({
                            "dom_index": dom_index,
                            "is_ad": True,  # 광고로 표시하여 원위치 유지
                            "rank": None,
                            "type": f"특수섹션({'ProductUnit' if is_product_unit else '링크없음'})",
                            'product_id': None,
                            'item_id': None,
                            'vendor_item_id': None
                        })
                        print(f"   [전체:{dom_index+1:2d}] 특수 섹션 감지 (상품 링크 없음) - 원위치 유지")
                        continue

                    # 3. URL 파라미터 추출 (링크가 있으므로 안전)
                    url_params = self.extract_url_params(link)

                    # 4. 광고 판별 (extract_products()와 동일한 로직 사용)
                    # - URL에 rank 파라미터 있음 + AdMark 없음 = 일반 상품
                    # - 그 외 = 광고
                    has_rank_param = ("&rank=" in link) or ("?rank=" in link)

                    # AdMark 클래스 확인
                    try:
                        ad_mark = item.find_element(By.CSS_SELECTOR, '[class*="AdMark"]')
                        is_explicit_ad = True
                    except:
                        is_explicit_ad = False

                    # 일반 상품 판단
                    is_ad = not (has_rank_param and not is_explicit_ad)

                    # 정보 저장
                    total_rank = dom_index + 1
                    if is_ad:
                        ad_rank += 1
                        items_info.append({
                            "dom_index": dom_index,
                            "is_ad": True,
                            "rank": None,
                            "type": "광고",
                            **url_params
                        })
                        print(f"   [전체:{total_rank:2d}/광고:{ad_rank:2d}] - P:{url_params['product_id']} / I:{url_params['item_id']} / V:{url_params['vendor_item_id']}")
                    else:
                        organic_rank += 1
                        organic_products.append(item)
                        organic_dom_indices.append(dom_index)
                        items_info.append({
                            "dom_index": dom_index,
                            "is_ad": False,
                            "rank": organic_rank,
                            "type": "일반",
                            **url_params
                        })
                        print(f"   [전체:{total_rank:2d}/일반:{organic_rank:2d}] - P:{url_params['product_id']} / I:{url_params['item_id']} / V:{url_params['vendor_item_id']}")

                except Exception as e:
                    # 파싱 실패 시 광고로 간주
                    items_info.append({
                        "dom_index": dom_index,
                        "is_ad": True,
                        "rank": None,
                        "type": "파싱실패"
                    })
                    print(f"   [{dom_index:2d}] 파싱 실패 (광고로 간주)")

            print(f"\n   ✅ 분석 완료:")
            print(f"      - 일반 제품: {len(organic_products)}개")
            print(f"      - 광고: {len(all_items) - len(organic_products)}개")

            return {
                "all_items": all_items,
                "items_info": items_info,
                "organic_products": organic_products,
                "organic_dom_indices": organic_dom_indices
            }

        except Exception as e:
            print(f"❌ DOM 구조 분석 실패: {e}")
            import traceback
            traceback.print_exc()
            return {
                "all_items": [],
                "items_info": [],
                "organic_products": [],
                "organic_dom_indices": []
            }

    def extract_products(self, exclude_ads: bool = True) -> List[WebElement]:
        """
        현재 페이지의 모든 상품 요소를 추출

        Args:
            exclude_ads: 광고 상품 제외 여부 (기본: True)

        Returns:
            상품 요소 리스트 (광고 제외 시 rank 파라미터 있는 상품만)
        """
        try:
            # 쿠팡 검색 결과 상품 리스트 선택자 (올바른 선택자)
            # 방법 1: #product-list > li (data-id 속성 있는 것)
            all_products = self.driver.find_elements(By.CSS_SELECTOR, "#product-list > li[data-id]")

            # 방법 2: data-id 없는 경우 전체 li
            # ⚠️ 중요: 여기서는 특수 섹션을 제외해도 됨 (재배치 대상이 아니므로)
            if not all_products:
                all_products = self.driver.find_elements(By.CSS_SELECTOR, "#product-list > li")

            # 방법 3: 대체 선택자 (구 버전 호환)
            if not all_products:
                all_products = self.driver.find_elements(By.CSS_SELECTOR, "li.search-product")

            print(f"📦 전체 상품 수: {len(all_products)}")

            # 광고 제외 필터링
            if exclude_ads:
                organic_products = []
                ad_count = 0

                for product in all_products:
                    try:
                        # 특수 섹션 체크 (best-seller, limited-time-offer 등)
                        item_class = product.get_attribute('class') or ''
                        item_class_lower = item_class.lower()
                        special_section_keywords = ['best-seller', 'limited-time-offer', 'time-deal', 'special-offer']
                        is_special_section = any(keyword in item_class_lower for keyword in special_section_keywords)

                        if is_special_section:
                            ad_count += 1
                            continue

                        # 상품 링크 추출
                        # 우선순위: a[href*="/vp/products/"] > a.search-product-link
                        link = None
                        try:
                            link_elem = product.find_element(By.CSS_SELECTOR, 'a[href*="/vp/products/"]')
                            link = link_elem.get_attribute("href")
                        except:
                            try:
                                link_elem = product.find_element(By.CSS_SELECTOR, "a.search-product-link")
                                link = link_elem.get_attribute("href")
                            except:
                                pass

                        if not link:
                            ad_count += 1
                            continue

                        # 광고 판별 기준:
                        # 1. URL에 rank 파라미터가 있으면 자연 검색 결과
                        # 2. rank 파라미터가 없으면 광고
                        # 3. AdMark 클래스가 있으면 명시적 광고
                        has_rank_param = ("&rank=" in link) or ("?rank=" in link)

                        # AdMark 클래스 확인
                        try:
                            ad_mark = product.find_element(By.CSS_SELECTOR, '[class*="AdMark"]')
                            is_explicit_ad = True
                        except:
                            is_explicit_ad = False

                        # 자연 검색 결과 판단
                        if has_rank_param and not is_explicit_ad:
                            organic_products.append(product)
                        else:
                            ad_count += 1

                    except Exception as e:
                        # 링크 추출 실패 시 건너뛰기
                        ad_count += 1
                        continue

                print(f"   ├─ 자연 검색 결과 (rank 파라미터 있음): {len(organic_products)}")
                print(f"   └─ 광고 상품 제외: {ad_count}")

                return organic_products
            else:
                return all_products

        except Exception as e:
            print(f"⚠️  상품 추출 실패: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_product_info(self, product_element: WebElement) -> Dict:
        """
        상품 요소에서 정보 추출

        Args:
            product_element: 상품 WebElement

        Returns:
            상품 정보 딕셔너리
        """
        try:
            # 상품명 (난독화된 클래스명 대응)
            name = "알 수 없음"
            try:
                # 방법 1: ProductUnit_productName 클래스 (부분 매칭)
                name_elem = product_element.find_element(By.CSS_SELECTOR, '[class*="ProductUnit_productName"]')
                name = name_elem.text.strip()
            except:
                try:
                    # 방법 2: 구 선택자
                    name_elem = product_element.find_element(By.CSS_SELECTOR, "div.name")
                    name = name_elem.text.strip()
                except:
                    pass

            # 가격
            price = "가격 정보 없음"
            try:
                # 방법 1: ProductPrice 클래스 (부분 매칭)
                price_elem = product_element.find_element(By.CSS_SELECTOR, '[class*="ProductPrice_price"]')
                price = price_elem.text.strip()
            except:
                try:
                    # 방법 2: strong.price-value
                    price_elem = product_element.find_element(By.CSS_SELECTOR, "strong.price-value")
                    price = price_elem.text.strip()
                except:
                    pass

            # 링크
            link = None
            try:
                link_elem = product_element.find_element(By.CSS_SELECTOR, 'a[href*="/vp/products/"]')
                link = link_elem.get_attribute("href")
            except:
                try:
                    link_elem = product_element.find_element(By.CSS_SELECTOR, "a.search-product-link")
                    link = link_elem.get_attribute("href")
                except:
                    pass

            # 평점 (난독화된 클래스명 대응)
            rating = None
            try:
                # 방법 1: ProductRating_star 클래스
                rating_elem = product_element.find_element(By.CSS_SELECTOR, '[class*="ProductRating_star"]')
                rating = rating_elem.text.strip()
            except:
                try:
                    # 방법 2: em.rating
                    rating_elem = product_element.find_element(By.CSS_SELECTOR, "em.rating")
                    rating = rating_elem.text.strip()
                except:
                    pass

            # 리뷰 수
            review_count = None
            try:
                # 방법 1: ProductRating 클래스 내부
                review_elem = product_element.find_element(By.CSS_SELECTOR, '[class*="ProductRating"]')
                review_text = review_elem.text
                # "(72376)" 형식에서 숫자 추출
                import re
                match = re.search(r'\((\d+(?:,\d+)*)\)', review_text)
                if match:
                    review_count = match.group(1)
            except:
                try:
                    # 방법 2: span.rating-total-count
                    review_elem = product_element.find_element(By.CSS_SELECTOR, "span.rating-total-count")
                    review_count = review_elem.text.strip()
                except:
                    pass

            return {
                "name": name,
                "price": price,
                "link": link,
                "rating": rating,
                "review_count": review_count,
                "element": product_element
            }

        except Exception as e:
            print(f"⚠️  상품 정보 추출 실패: {e}")
            return {
                "name": "추출 실패",
                "price": None,
                "link": None,
                "rating": None,
                "review_count": None,
                "element": product_element
            }

    def find_product_by_rank(self, target_rank: int = 15, max_pages: int = 5) -> Optional[Dict]:
        """
        특정 순위의 상품을 찾음 (광고 제외, 여러 페이지 검색 가능)

        Args:
            target_rank: 찾을 상품의 순위 (기본: 15, 광고 제외 기준)
            max_pages: 최대 검색 페이지 수 (기본: 5)

        Returns:
            상품 정보 (실패 시 None)
        """
        print(f"\n🔍 {target_rank}등 상품 검색 중 (광고 제외)...")

        current_page = 1
        accumulated_products = []

        while current_page <= max_pages:
            print(f"\n📄 페이지 {current_page} 검색 중...")

            # 현재 페이지의 상품 리스트 추출 (광고 제외)
            products = self.extract_products(exclude_ads=True)

            if not products:
                print(f"   ⚠️  페이지 {current_page}에서 상품을 찾을 수 없습니다")
                break

            # 상품 누적
            accumulated_products.extend(products)
            print(f"   📊 누적 자연 검색 결과: {len(accumulated_products)}")

            # 목표 순위를 찾았는지 확인
            if len(accumulated_products) >= target_rank:
                # 순위는 1부터 시작, 배열 인덱스는 0부터
                target_index = target_rank - 1
                target_product = accumulated_products[target_index]

                # 상품 정보 추출
                product_info = self.get_product_info(target_product)
                product_info["rank"] = target_rank
                product_info["page"] = current_page

                print(f"\n✅ {target_rank}등 상품 발견 (페이지 {current_page}):")
                print(f"   이름: {product_info['name'][:50]}...")
                print(f"   가격: {product_info['price']}")
                if product_info['rating']:
                    print(f"   평점: {product_info['rating']} ({product_info['review_count']})")
                if product_info['link']:
                    print(f"   URL: {product_info['link'][:80]}...")

                return product_info

            # 다음 페이지로 이동
            if current_page < max_pages:
                print(f"   ⏭️  {target_rank}등을 찾기 위해 다음 페이지로 이동 중...")
                if not self._move_to_next_page():
                    print(f"   ⚠️  다음 페이지로 이동 실패")
                    break
                time.sleep(2.0)  # 페이지 로드 대기

            current_page += 1

        # 모든 페이지를 검색했지만 찾지 못함
        print(f"\n❌ {target_rank}등 상품을 찾을 수 없습니다")
        print(f"   총 검색 페이지: {current_page - 1}")
        print(f"   총 자연 검색 결과: {len(accumulated_products)}")
        return None

    def scroll_to_center(self, product_info: Dict, video_recorder=None) -> bool:
        """
        상품을 화면 중앙에 위치시킴

        Args:
            product_info: 상품 정보 (element 포함)
            video_recorder: VideoRecorder 인스턴스 (선택, 녹화 중이면 프레임 캡처)

        Returns:
            성공 여부
        """
        try:
            element = product_info["element"]

            print(f"\n📍 상품을 화면 중앙으로 이동 중...")

            # 사람처럼 자연스럽게 스크롤 (여러 단계로 나눠서)
            if video_recorder:
                # 1. 목표 상품 위치 계산
                target_y = self.driver.execute_script("""
                    const rect = arguments[0].getBoundingClientRect();
                    const absoluteTop = rect.top + window.pageYOffset;
                    const middle = absoluteTop - (window.innerHeight / 2) + (rect.height / 2);
                    return middle;
                """, element)

                current_y = self.driver.execute_script("return window.pageYOffset;")
                distance = target_y - current_y

                # 2. 여러 단계로 나눠서 스크롤 (3-5단계)
                import random
                num_steps = random.randint(3, 5)
                step_size = distance / num_steps

                for step in range(num_steps):
                    # 각 단계마다 조금씩 스크롤
                    scroll_amount = int(step_size + random.uniform(-50, 50))
                    self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")

                    # 스크롤 후 짧은 멈춤 (자동 녹화 중)
                    pause_time = random.uniform(0.5, 1.0)
                    time.sleep(pause_time)

                # 3. 최종 위치 미세 조정
                self.driver.execute_script("""
                    arguments[0].scrollIntoView({
                        behavior: 'smooth',
                        block: 'center',
                        inline: 'nearest'
                    });
                """, element)

                # 미세 조정 대기 (자동 녹화 중)
                time.sleep(0.5)

            else:
                # 영상 녹화 없으면 기존 방식
                self.driver.execute_script("""
                    arguments[0].scrollIntoView({
                        behavior: 'smooth',
                        block: 'center',
                        inline: 'nearest'
                    });
                """, element)
                time.sleep(1.5)

            # 요소가 화면에 보이는지 확인
            is_visible = self.driver.execute_script("""
                const rect = arguments[0].getBoundingClientRect();
                const windowHeight = window.innerHeight || document.documentElement.clientHeight;
                const windowWidth = window.innerWidth || document.documentElement.clientWidth;

                return (
                    rect.top >= 0 &&
                    rect.left >= 0 &&
                    rect.bottom <= windowHeight &&
                    rect.right <= windowWidth
                );
            """, element)

            if is_visible:
                print("✅ 상품이 화면 중앙에 위치했습니다")
                return True
            else:
                print("⚠️  상품이 화면 밖에 있습니다. 재시도 중...")
                # 한 번 더 시도
                self.driver.execute_script("""
                    arguments[0].scrollIntoView({
                        behavior: 'auto',
                        block: 'center',
                        inline: 'nearest'
                    });
                """, element)
                time.sleep(1.0)
                return True

        except Exception as e:
            print(f"❌ 화면 중앙 정렬 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def apply_highlight(self, product_info: Dict) -> bool:
        """
        상품 요소에 하이라이트 효과 적용
        레이아웃에 영향을 주지 않도록 outline과 box-shadow 사용

        Args:
            product_info: 상품 정보 (element 포함)

        Returns:
            성공 여부
        """
        try:
            element = product_info.get("element")
            if not element:
                print("⚠️  하이라이트할 요소를 찾을 수 없습니다")
                return False

            # 기존 하이라이트가 있으면 먼저 제거
            if self._highlighted_element:
                self.remove_highlight()

            # 원래 스타일 저장
            self._original_styles = {
                "outline": element.value_of_css_property("outline"),
                "outline_offset": element.value_of_css_property("outline-offset"),
                "box_shadow": element.value_of_css_property("box-shadow"),
                "background_color": element.value_of_css_property("background-color")
            }

            # 하이라이트 효과 추가 (레이아웃 영향 없음)
            self.driver.execute_script("""
                // outline은 레이아웃에 영향을 주지 않음
                arguments[0].style.outline = '4px solid red';
                arguments[0].style.outlineOffset = '-4px';  // 안쪽으로 표시

                // box-shadow도 레이아웃에 영향 없음
                arguments[0].style.boxShadow = '0 0 20px 5px rgba(255, 0, 0, 0.8)';

                // 배경색 살짝 변경 (투명도)
                arguments[0].style.backgroundColor = 'rgba(255, 255, 0, 0.15)';
            """, element)

            # 현재 하이라이트된 요소 추적
            self._highlighted_element = element

            print("✅ 하이라이트 효과 적용 완료")
            return True

        except Exception as e:
            print(f"⚠️  하이라이트 적용 실패: {e}")
            return False

    def remove_highlight(self) -> bool:
        """
        현재 하이라이트된 요소의 효과 제거

        Returns:
            성공 여부
        """
        try:
            if not self._highlighted_element:
                return True  # 하이라이트된 요소가 없으면 성공으로 간주

            # 원래 스타일로 복원
            self.driver.execute_script("""
                arguments[0].style.outline = arguments[1];
                arguments[0].style.outlineOffset = arguments[2];
                arguments[0].style.boxShadow = arguments[3];
                arguments[0].style.backgroundColor = arguments[4];
            """,
                self._highlighted_element,
                self._original_styles.get("outline", ""),
                self._original_styles.get("outline_offset", ""),
                self._original_styles.get("box_shadow", ""),
                self._original_styles.get("background_color", "")
            )

            # 추적 정보 초기화
            self._highlighted_element = None
            self._original_styles = {}

            print("✅ 하이라이트 효과 제거 완료")
            return True

        except Exception as e:
            print(f"⚠️  하이라이트 제거 실패: {e}")
            # 실패해도 추적 정보는 초기화
            self._highlighted_element = None
            self._original_styles = {}
            return False

    def _scroll_to_load_more(self):
        """
        페이지를 스크롤하여 더 많은 상품 로드
        """
        try:
            print("📜 더 많은 상품 로드를 위해 스크롤 중...")

            # 페이지 끝까지 스크롤
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2.0)

            # 다시 위로 조금 스크롤 (lazy loading 트리거)
            self.driver.execute_script("window.scrollBy(0, -500);")
            time.sleep(1.0)

        except Exception as e:
            print(f"⚠️  스크롤 실패: {e}")

    def _move_to_next_page(self) -> bool:
        """
        다음 페이지로 이동

        Returns:
            성공 여부
        """
        try:
            # 다음 페이지 버튼 찾기
            # 쿠팡 페이지네이션: a.btn-next 또는 a[title="next"]
            next_button = None

            # 방법 1: CSS 선택자로 찾기
            try:
                next_button = self.driver.find_element(By.CSS_SELECTOR, "a.btn-next")
            except:
                pass

            # 방법 2: title 속성으로 찾기
            if not next_button:
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, "a[title='다음']")
                except:
                    pass

            # 방법 3: XPath로 찾기
            if not next_button:
                try:
                    next_button = self.driver.find_element(By.XPATH, "//a[contains(@class, 'next')]")
                except:
                    pass

            if not next_button:
                print("   ⚠️  다음 페이지 버튼을 찾을 수 없습니다")
                return False

            # 버튼이 활성화되어 있는지 확인
            if "disabled" in next_button.get_attribute("class") or "":
                print("   ⚠️  다음 페이지가 없습니다 (마지막 페이지)")
                return False

            # 클릭 전 현재 URL 저장
            old_url = self.driver.current_url

            # 다음 페이지 버튼 클릭
            next_button.click()
            time.sleep(1.5)

            # URL이 변경되었는지 확인
            new_url = self.driver.current_url
            if old_url == new_url:
                print("   ⚠️  페이지가 이동하지 않았습니다")
                return False

            print(f"   ✅ 다음 페이지로 이동 완료")
            return True

        except Exception as e:
            print(f"   ⚠️  다음 페이지 이동 실패: {e}")
            return False

    def print_product_list(self, limit: int = 30):
        """
        현재 페이지의 상품 목록을 순위별로 콘솔에 출력 (광고 제외)

        Args:
            limit: 출력할 최대 상품 수 (기본: 30)
        """
        print("\n" + "=" * 80)
        print("📋 상품 목록 (광고 제외, /vp/products? 링크만)")
        print("=" * 80)

        products = self.extract_products(exclude_ads=True)

        if not products:
            print("❌ 상품을 찾을 수 없습니다")
            return

        # 출력할 상품 수 제한
        display_count = min(len(products), limit)

        for i, product in enumerate(products[:display_count], 1):
            product_info = self.get_product_info(product)

            print(f"\n{i:2d}위. {product_info['name'][:60]}")
            print(f"     💰 {product_info['price']}")

            if product_info['rating']:
                print(f"     ⭐ {product_info['rating']} ({product_info['review_count']})")

            if product_info['link']:
                # URL에서 상품 ID 추출
                if "/vp/products/" in product_info['link']:
                    product_id = product_info['link'].split("/vp/products/")[1].split("?")[0]
                    print(f"     🔗 상품 ID: {product_id}")

        if len(products) > limit:
            print(f"\n... 외 {len(products) - limit}개 상품 더 있음")

        print("\n" + "=" * 80)
        print(f"총 {len(products)}개 자연 검색 결과")
        print("=" * 80 + "\n")

    def find_and_center_product(self, target_rank: int = 15) -> Optional[Dict]:
        """
        특정 순위의 상품을 찾아서 화면 중앙에 위치시킴 (통합 메서드)

        Args:
            target_rank: 찾을 상품의 순위 (기본: 15)

        Returns:
            상품 정보 (실패 시 None)
        """
        # 1. 상품 찾기
        product_info = self.find_product_by_rank(target_rank)

        if not product_info:
            return None

        # 2. 화면 중앙에 위치
        success = self.scroll_to_center(product_info)

        if not success:
            print("⚠️  화면 중앙 정렬 실패했지만 상품 정보는 반환합니다")

        return product_info

    @staticmethod
    def extract_url_params(url: str) -> Dict[str, str]:
        """
        상품 URL에서 파라미터 추출

        예시 URL:
        /vp/products/141088383?itemId=17321560995&vendorItemId=4007596558&q=c타입 고속 충전기 케이블&searchId=f323b5501186199&sourceType=search&itemsCount=36&searchRank=13&rank=13

        Args:
            url: 상품 URL (href)

        Returns:
            {
                "product_id": "141088383",
                "item_id": "17321560995",
                "vendor_item_id": "4007596558",
                "keyword": "c타입 고속 충전기 케이블",
                "rank": "13"
            }
        """
        result = {
            "product_id": "",
            "item_id": "",
            "vendor_item_id": "",
            "keyword": "",
            "rank": ""
        }

        if not url:
            return result

        try:
            # product_id 추출: /vp/products/{product_id}
            product_id_match = re.search(r'/vp/products/(\d+)', url)
            if product_id_match:
                result["product_id"] = product_id_match.group(1)

            # URL 파라미터 파싱
            parsed = urlparse(url)
            params = parse_qs(parsed.query)

            # itemId 추출
            if 'itemId' in params:
                result["item_id"] = params['itemId'][0]

            # vendorItemId 추출
            if 'vendorItemId' in params:
                result["vendor_item_id"] = params['vendorItemId'][0]

            # keyword (q) 추출
            if 'q' in params:
                result["keyword"] = params['q'][0]

            # rank 추출 (rank 또는 searchRank)
            if 'rank' in params:
                result["rank"] = params['rank'][0]
            elif 'searchRank' in params:
                result["rank"] = params['searchRank'][0]

        except Exception as e:
            print(f"   ⚠️  URL 파라미터 추출 실패: {e}")

        return result

    def extract_all_products_params(self, organic_products: List[WebElement]) -> List[Dict]:
        """
        전체 일반 상품 목록의 URL 파라미터 추출

        Args:
            organic_products: 광고 제외 상품 요소 리스트

        Returns:
            [
                {
                    "rank": 1,
                    "product_id": "141088383",
                    "item_id": "17321560995",
                    "vendor_item_id": "4007596558",
                    "keyword": "c타입 고속 충전기 케이블",
                    "url_rank": "13",
                    "link": "/vp/products/...",
                    "name": "상품명",
                    "element": WebElement
                },
                ...
            ]
        """
        result = []

        for rank, product in enumerate(organic_products, start=1):
            try:
                # 상품 링크 추출
                link = None
                try:
                    link_elem = product.find_element(By.CSS_SELECTOR, 'a[href*="/vp/products/"]')
                    link = link_elem.get_attribute("href")
                except:
                    try:
                        link_elem = product.find_element(By.CSS_SELECTOR, "a.search-product-link")
                        link = link_elem.get_attribute("href")
                    except:
                        pass

                if not link:
                    continue

                # URL 파라미터 추출
                url_params = self.extract_url_params(link)

                # 상품명 추출
                name = ""
                try:
                    name_elem = product.find_element(By.CSS_SELECTOR, ".name")
                    name = name_elem.text.strip()
                except:
                    pass

                result.append({
                    "rank": rank,
                    "product_id": url_params['product_id'],
                    "item_id": url_params['item_id'],
                    "vendor_item_id": url_params['vendor_item_id'],
                    "keyword": url_params['keyword'],
                    "url_rank": url_params['rank'],
                    "link": link,
                    "name": name,
                    "element": product
                })

            except Exception as e:
                print(f"   ⚠️  {rank}등 상품 파라미터 추출 실패: {e}")
                continue

        return result

    def find_product_by_params(
        self,
        all_products_params: List[Dict],
        product_id: str = None,
        item_id: str = None,
        vendor_item_id: str = None
    ) -> Optional[Tuple[Dict, str]]:
        """
        파라미터로 상품 검색 (우선순위별 매칭)

        우선순위:
        1. product_id + item_id + vendor_item_id 모두 일치
        2. product_id + vendor_item_id 일치
        3. product_id만 일치
        4. vendor_item_id만 일치
        5. item_id만 일치

        Args:
            all_products_params: extract_all_products_params()의 결과
            product_id: 상품 ID
            item_id: 아이템 ID
            vendor_item_id: 판매자 아이템 ID

        Returns:
            (매칭된 상품 정보, 매칭 조건) 튜플, 없으면 (None, None)
        """
        if not all_products_params:
            return (None, None)

        # 1순위: product_id + item_id + vendor_item_id 모두 일치
        if product_id and item_id and vendor_item_id:
            for product in all_products_params:
                if (product['product_id'] == str(product_id) and
                    product['item_id'] == str(item_id) and
                    product['vendor_item_id'] == str(vendor_item_id)):
                    match_condition = "완전 일치 (product_id + item_id + vendor_item_id)"
                    rank_info = f" (순위: {product['rank']})" if 'rank' in product else ""
                    print(f"✅ [{match_condition}] 상품 발견: {product.get('name', 'Unknown')[:50]}...{rank_info}")
                    return (product, match_condition)

        # 2순위: product_id + vendor_item_id 일치
        if product_id and vendor_item_id:
            for product in all_products_params:
                if (product['product_id'] == str(product_id) and
                    product['vendor_item_id'] == str(vendor_item_id)):
                    match_condition = "product_id + vendor_item_id 일치"
                    rank_info = f" (순위: {product['rank']})" if 'rank' in product else ""
                    print(f"✅ [{match_condition}] 상품 발견: {product.get('name', 'Unknown')[:50]}...{rank_info}")
                    return (product, match_condition)

        # 3순위: product_id만 일치
        if product_id:
            for product in all_products_params:
                if product['product_id'] == str(product_id):
                    match_condition = "product_id 일치"
                    rank_info = f" (순위: {product['rank']})" if 'rank' in product else ""
                    print(f"✅ [{match_condition}] 상품 발견: {product.get('name', 'Unknown')[:50]}...{rank_info}")
                    return (product, match_condition)

        # 4순위: vendor_item_id만 일치
        if vendor_item_id:
            for product in all_products_params:
                if product['vendor_item_id'] == str(vendor_item_id):
                    match_condition = "vendor_item_id 일치"
                    rank_info = f" (순위: {product['rank']})" if 'rank' in product else ""
                    print(f"✅ [{match_condition}] 상품 발견: {product.get('name', 'Unknown')[:50]}...{rank_info}")
                    return (product, match_condition)

        # 5순위: item_id만 일치
        if item_id:
            for product in all_products_params:
                if product['item_id'] == str(item_id):
                    match_condition = "item_id 일치"
                    rank_info = f" (순위: {product['rank']})" if 'rank' in product else ""
                    print(f"✅ [{match_condition}] 상품 발견: {product.get('name', 'Unknown')[:50]}...{rank_info}")
                    return (product, match_condition)

        print(f"❌ 매칭되는 상품을 찾지 못했습니다")
        print(f"   검색 조건: product_id={product_id}, item_id={item_id}, vendor_item_id={vendor_item_id}")
        return (None, None)

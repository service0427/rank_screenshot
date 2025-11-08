#!/usr/bin/env python3
"""
상품 페이지 방문 모듈
쿠키/세션 생성을 위해 특정 상품 페이지를 방문
"""

from typing import Optional, Tuple, Dict, Any
import time
from selenium.webdriver.common.by import By


class ProductPageVisitor:
    """상품 페이지 방문 클래스"""

    def __init__(self, driver, handler=None, core=None, enable_main_filter=False):
        """
        Args:
            driver: Selenium WebDriver
            handler: CoupangHandlerSelenium (검색 기능 사용, optional)
            core: BrowserCoreUC (네트워크 필터용, optional)
            enable_main_filter: 메인 페이지 네트워크 필터 활성화 여부
        """
        self.driver = driver
        self.handler = handler
        self.core = core
        self.enable_main_filter = enable_main_filter

    def visit_product_page(
        self,
        product_id: str,
        item_id: str,
        vendor_item_id: str,
        wait_time: float = 2.0,
        collect_info: bool = True
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        상품 페이지 방문 및 정보 수집

        Args:
            product_id: 상품 ID
            item_id: 아이템 ID
            vendor_item_id: 판매자 아이템 ID
            wait_time: 페이지 로드 후 대기 시간 (초)
            collect_info: 상품 정보 수집 여부 (기본: True)

        Returns:
            (성공 여부, 에러 메시지, 수집된 상품 정보)
        """
        try:
            # URL 생성
            product_url = self._build_product_url(product_id, item_id, vendor_item_id)

            print(f"\n📦 상품 페이지 방문 시작:")
            print(f"   - Product ID: {product_id}")
            print(f"   - Item ID: {item_id}")
            print(f"   - Vendor Item ID: {vendor_item_id}")
            print(f"   - URL: {product_url}")

            # 상품 페이지 이동
            self.driver.get(product_url)

            # 페이지 로드 대기
            time.sleep(wait_time)

            # 현재 URL 확인 (리다이렉트 체크)
            current_url = self.driver.current_url
            print(f"   ✓ 페이지 로드 완료")
            print(f"   - 현재 URL: {current_url}")

            # 점검 페이지 체크
            if "sorry" in current_url.lower() or "block" in current_url.lower():
                print(f"   ⚠️  점검 페이지로 리다이렉트됨")
                return (False, "점검 페이지 감지", None)

            # 상품 정보 수집 (옵션)
            product_info = None
            if collect_info:
                product_info = self.collect_product_info()

            print(f"✅ 상품 페이지 방문 완료")
            return (True, None, product_info)

        except Exception as e:
            error_msg = f"상품 페이지 방문 실패: {e}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return (False, error_msg, None)

    def visit_and_return_to_search(
        self,
        product_id: str,
        item_id: str,
        vendor_item_id: str,
        keyword: str,
        wait_time: float = 2.0
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        상품 페이지 방문 후 검색 결과로 복귀

        워크플로우:
        1. 상품 페이지 방문 및 정보 수집
        2. 쿠팡 메인으로 이동
        3. 검색어로 다시 검색

        Args:
            product_id: 상품 ID
            item_id: 아이템 ID
            vendor_item_id: 판매자 아이템 ID
            keyword: 검색 키워드
            wait_time: 각 단계별 대기 시간 (초)

        Returns:
            (성공 여부, 에러 메시지, 수집된 상품 정보)
        """
        try:
            print(f"\n{'=' * 60}")
            print(f"🔄 상품 페이지 방문 → 검색 복귀 워크플로우")
            print(f"{'=' * 60}\n")

            # Step 1: 상품 페이지 방문 및 정보 수집
            success, error, product_info = self.visit_product_page(
                product_id, item_id, vendor_item_id, wait_time, collect_info=True
            )
            if not success:
                return (False, f"상품 페이지 방문 실패: {error}", None)

            # Step 2: 쿠팡 메인으로 이동
            print(f"\n🏠 쿠팡 메인으로 이동...")

            # 네트워크 필터 활성화 (페이지 이동 **전**에)
            if self.core and self.enable_main_filter:
                print(f"   🔍 필터 활성화 조건 체크: enable_main_filter={self.enable_main_filter}")
                print(f"   ✅ 페이지 이동 전 네트워크 필터 활성화\n")
                self.core.enable_network_filter()
            elif not self.enable_main_filter:
                print(f"   ℹ️  네트워크 필터 비활성화됨 (--enable-main-filter 플래그 없음)\n")

            self.driver.get("https://www.coupang.com")
            time.sleep(wait_time)
            print(f"   ✓ 메인 페이지 로드 완료")

            # 네트워크 필터 작동 확인 (페이지 로드 후 모니터링)
            if self.core and self.enable_main_filter:
                print(f"\n   🔍 네트워크 필터 작동 확인 (3초간 모니터링)...")
                self.core._monitor_network_requests(duration=3)

            # Step 3: 검색어로 다시 검색
            print(f"\n🔍 검색어로 복귀: '{keyword}'")

            # 네트워크 필터 비활성화 (검색 결과 페이지에서는 필터 해제)
            if self.core and self.enable_main_filter:
                self.core.disable_network_filter()

            if self.handler:
                # handler가 있으면 자연스러운 검색 사용
                if not self.handler.search_product(keyword):
                    return (False, "검색 실패 - 검색창을 찾을 수 없음", product_info)
                time.sleep(wait_time * 2)
                print(f"   ✓ 검색 결과 로드 완료")
            else:
                # handler가 없으면 URL 직접 이동 (fallback)
                search_url = f"https://www.coupang.com/np/search?q={keyword}"
                self.driver.get(search_url)
                time.sleep(wait_time * 2)
                print(f"   ✓ 검색 결과 로드 완료 (URL 직접 이동)")

            print(f"\n✅ 상품 페이지 방문 → 검색 복귀 완료")
            print(f"{'=' * 60}\n")
            return (True, None, product_info)

        except Exception as e:
            error_msg = f"워크플로우 실패: {e}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return (False, error_msg, None)

    def _build_product_url(
        self,
        product_id: str,
        item_id: str,
        vendor_item_id: str
    ) -> str:
        """
        상품 URL 생성

        Args:
            product_id: 상품 ID
            item_id: 아이템 ID
            vendor_item_id: 판매자 아이템 ID

        Returns:
            상품 페이지 URL
        """
        base_url = "https://www.coupang.com/vp/products"
        return f"{base_url}/{product_id}?itemId={item_id}&vendorItemId={vendor_item_id}"

    def collect_product_info(self) -> Optional[Dict[str, Any]]:
        """
        현재 상품 페이지에서 상세 정보 수집

        수집 정보:
        - title: 상품명
        - price: 가격 정보 (current, original, discount_rate)
        - delivery: 배송 정보 (type, badge_url)
        - thumbnails: 썸네일 이미지 URL 리스트
        - categories: 카테고리 경로
        - sold_out: 품절 여부

        Returns:
            수집된 상품 정보 딕셔너리 (실패 시 None)
        """
        try:
            print(f"\n📊 상품 페이지 정보 수집 시작...")

            # JavaScript로 한 번에 모든 정보 수집
            js_code = """
            const productInfo = {
                title: null,
                price: {
                    current: null,
                    original: null,
                    discount_rate: null
                },
                delivery: {
                    type: null,
                    badge_url: null
                },
                thumbnails: [],
                categories: [],
                sold_out: false
            };

            // 1. 상품명
            const titleEl = document.querySelector('h1.product-title span');
            if (titleEl) {
                productInfo.title = titleEl.textContent.trim();
            }

            // 2. 가격 정보
            const currentPriceEl = document.querySelector('.price-amount.final-price-amount');
            if (currentPriceEl) {
                productInfo.price.current = currentPriceEl.textContent.trim();
            }

            const originalPriceEl = document.querySelector('.price-amount.original-price-amount');
            if (originalPriceEl) {
                productInfo.price.original = originalPriceEl.textContent.trim();
            }

            const discountEl = document.querySelector('.discount-percentage');
            if (discountEl) {
                productInfo.price.discount_rate = discountEl.textContent.trim();
            }

            // 3. 배송 정보
            const deliveryBadge = document.querySelector('img[src*="badge"]');
            if (deliveryBadge) {
                productInfo.delivery.badge_url = deliveryBadge.src;

                // 배송 타입 분류
                const badgeUrl = deliveryBadge.src.toLowerCase();
                if (badgeUrl.includes('rocket')) {
                    if (badgeUrl.includes('fresh')) {
                        productInfo.delivery.type = 'Rocket Fresh';
                    } else if (badgeUrl.includes('direct')) {
                        productInfo.delivery.type = 'Rocket Direct';
                    } else if (badgeUrl.includes('install')) {
                        productInfo.delivery.type = 'Rocket Install';
                    } else if (badgeUrl.includes('seller')) {
                        productInfo.delivery.type = 'Rocket Seller';
                    } else {
                        productInfo.delivery.type = 'Rocket Delivery';
                    }
                } else {
                    productInfo.delivery.type = 'General';
                }
            }

            // 4. 썸네일 이미지
            const thumbnailEls = document.querySelectorAll('ul.twc-static > li > img');
            thumbnailEls.forEach(img => {
                const imgUrl = img.currentSrc || img.src;
                if (imgUrl && imgUrl.includes('/thumbnails/')) {
                    productInfo.thumbnails.push(imgUrl);
                }
            });

            // 5. 카테고리 (breadcrumb)
            const breadcrumbEls = document.querySelectorAll('ul.breadcrumb li a');
            breadcrumbEls.forEach(link => {
                productInfo.categories.push({
                    name: link.textContent.trim(),
                    href: link.href
                });
            });

            // 6. 품절 상태 감지
            // 우선순위 1: JSON-LD 스키마 체크 (가장 신뢰도 높음)
            const jsonLdScripts = document.querySelectorAll('script[type="application/ld+json"]');
            jsonLdScripts.forEach(script => {
                try {
                    const data = JSON.parse(script.textContent);
                    if (data.offers && data.offers.availability) {
                        if (data.offers.availability.includes('SoldOut') ||
                            data.offers.availability.includes('OutOfStock')) {
                            productInfo.sold_out = true;
                        } else if (data.offers.availability.includes('InStock')) {
                            productInfo.sold_out = false;  // 명시적으로 재고 있음
                        }
                    }
                } catch (e) {}
            });

            // 우선순위 2: 구매 버튼 상태 체크 (재고 있으면 구매 버튼 활성화)
            if (!productInfo.sold_out) {
                const buyButton = document.querySelector('.btn-buy') ||
                                 document.querySelector('[class*="prod-buy"]') ||
                                 document.querySelector('button[class*="buy"]');

                if (buyButton) {
                    const buttonText = buyButton.textContent.trim();
                    const isDisabled = buyButton.disabled ||
                                      buyButton.classList.contains('disabled') ||
                                      buyButton.getAttribute('aria-disabled') === 'true';

                    // 버튼이 비활성화되어 있고, "품절" 텍스트가 있으면 품절
                    if (isDisabled && (buttonText.includes('품절') || buttonText.includes('일시품절'))) {
                        productInfo.sold_out = true;
                    }
                    // 버튼이 활성화되어 있으면 재고 있음
                    else if (!isDisabled && buttonText.includes('구매')) {
                        productInfo.sold_out = false;
                    }
                }
            }

            // 우선순위 3: CSS 클래스 체크 (상품 영역 내에서만)
            if (!productInfo.sold_out) {
                const productArea = document.querySelector('.prod-atf') ||
                                   document.querySelector('.prod-buy-header') ||
                                   document.querySelector('#contents');

                if (productArea) {
                    const soldOutEl = productArea.querySelector('.sold-out') ||
                                     productArea.querySelector('.oos-stylized') ||
                                     productArea.querySelector('[class*="sold-out"]');

                    if (soldOutEl) {
                        productInfo.sold_out = true;
                    }
                }
            }

            return productInfo;
            """

            # JavaScript 실행
            product_info = self.driver.execute_script(js_code)

            if product_info:
                print(f"   ✓ 상품명: {product_info.get('title', 'N/A')[:50]}...")
                print(f"   ✓ 현재가: {product_info.get('price', {}).get('current', 'N/A')}")
                print(f"   ✓ 배송: {product_info.get('delivery', {}).get('type', 'N/A')}")
                print(f"   ✓ 썸네일: {len(product_info.get('thumbnails', []))}개")
                print(f"   ✓ 카테고리: {len(product_info.get('categories', []))}개")
                print(f"   ✓ 품절: {'예' if product_info.get('sold_out') else '아니오'}")
                print(f"✅ 상품 정보 수집 완료\n")

                return product_info
            else:
                print(f"⚠️  상품 정보를 수집할 수 없습니다\n")
                return None

        except Exception as e:
            print(f"❌ 상품 정보 수집 실패: {e}")
            import traceback
            traceback.print_exc()
            return None

#!/usr/bin/env python3
"""
Coupang Handler - Selenium 기반
undetected-chromedriver 최적화
"""

import time
from typing import Optional, Dict, List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys

from common.constants import ExecutionStatus, ActionStatus
from common.utils.human_behavior_selenium import natural_typing, before_search

# 통합 이벤트 로거
try:
    from common.unified_event_logger import log_event, EventType
    UNIFIED_LOGGER_AVAILABLE = True
except ImportError:
    UNIFIED_LOGGER_AVAILABLE = False


class CoupangHandlerSelenium:
    """쿠팡 사이트 핸들러 (Selenium 기반)"""

    BASE_URL = "https://www.coupang.com"

    def __init__(self, driver, network_mode: str = "Local", worker_id: str = None, vpn_interface: str = None):
        """
        Args:
            driver: Selenium WebDriver 객체
            network_mode: 네트워크 모드 ("Local", "VPN 0", "Proxy" 등)
            worker_id: 워커 ID (로깅용)
            vpn_interface: VPN 인터페이스 (로깅용)
        """
        self.driver = driver
        self.wait = WebDriverWait(driver, 30)
        self.status = ExecutionStatus.BROWSER_READY
        self.action_status = ActionStatus.INIT
        self.network_mode = network_mode
        self.worker_id = worker_id or "Unknown"
        self.vpn_interface = vpn_interface

    def navigate_to_home(self, video_recorder=None) -> bool:
        """
        쿠팡 홈페이지로 이동 (20초 타임아웃)

        Args:
            video_recorder: 영상 녹화 객체 (선택)

        Returns:
            성공 여부
        """
        print("🏠 Navigating to Coupang home...")
        self.status = ExecutionStatus.BROWSER_LAUNCHING
        self.action_status = ActionStatus.NAVIGATING

        try:
            # 현재 URL 확인 (이미 쿠팡 홈이면 재로드 스킵)
            current_url = self.driver.current_url.rstrip('/')
            target_url = self.BASE_URL.rstrip('/')

            if current_url == target_url:
                print(f"   ℹ️  이미 쿠팡 홈 페이지입니다 (재로드 스킵)")
                print(f"   현재 URL: {current_url}")
                self.action_status = ActionStatus.LOADED

                # 네트워크 모드 오버레이 표시
                self.show_network_mode_overlay()

                print("   ✓ Home page ready")
                return True

            # 페이지 로드 타임아웃 설정 (20초)
            self.driver.set_page_load_timeout(20)

            print(f"   🔄 페이지 로드 중: {self.BASE_URL}")
            self.driver.get(self.BASE_URL)
            self.action_status = ActionStatus.LOADED

            # 페이지 로딩 대기 (자동 녹화 중이므로 프레임 캡처 불필요)
            time.sleep(2)

            # 네트워크 모드 오버레이 표시
            self.show_network_mode_overlay()

            print("   ✓ Home page loaded")
            return True

        except TimeoutException:
            print("   ✗ Timeout loading home page (20초 초과)")
            print("   🚨 쿠팡 홈페이지 무한 로딩 감지 - 강제 종료")
            self.action_status = ActionStatus.ERROR_TIMEOUT
            return False
        except Exception as e:
            print(f"   ✗ Error: {e}")
            self.action_status = ActionStatus.ERROR_NAVIGATION
            return False

    def search_product(self, keyword: str, video_recorder=None) -> bool:
        """
        상품 검색 (JavaScript 스크립트 방식)

        Args:
            keyword: 검색 키워드
            video_recorder: 영상 녹화 객체 (선택)

        Returns:
            성공 여부
        """
        print(f"🔍 Searching for: {keyword}")
        self.status = ExecutionStatus.SEARCHING
        self.action_status = ActionStatus.TYPING

        # 검색 시작 이벤트 로깅
        if UNIFIED_LOGGER_AVAILABLE:
            log_event(
                worker_id=self.worker_id,
                event_type=EventType.SEARCH_STARTED,
                interface=self.vpn_interface,
                details={'keyword': keyword}
            )

        try:
            # 검색 전 자연스러운 마우스 움직임 (Akamai 탐지 우회)
            print("   🖱️  검색 전 마우스 움직임...")
            before_search(self.driver)

            # JavaScript로 검색 실행
            search_script = """
            const keyword = arguments[0];
            const input = document.querySelector('input.is-speech[name="q"]');
            const headerBtn = document.querySelector('button.headerSearchBtn[type="submit"]');

            if (!input) {
              console.warn("검색 input을 못 찾았어.");
              return false;
            } else {
              const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
              setter?.call(input, keyword);
              input.dispatchEvent(new Event('input',  { bubbles: true }));
              input.dispatchEvent(new Event('change', { bubbles: true }));

              let form = input.closest('form');
              if (!form) form = document.querySelector('form[role="search"]') || document.querySelector('form');

              setTimeout(() => {
                if (form) {
                  const innerSubmit = form.querySelector('button[type="submit"], input[type="submit"]');
                  try {
                    if (form.requestSubmit) {
                      form.requestSubmit(innerSubmit || undefined);
                    } else {
                      form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })) || form.submit();
                    }
                    console.log(`2초 후 폼 제출로 "${keyword}" 검색`);
                  } catch (e) {
                    console.warn("requestSubmit 실패 -> 버튼 클릭 폴백 시도:", e);
                    if (headerBtn) {
                      headerBtn.click();
                      console.log(`2초 후 헤더 버튼 클릭 폴백으로 "${keyword}" 검색`);
                    } else {
                      console.warn("제출 경로를 찾지 못했어.");
                    }
                  }
                } else if (headerBtn) {
                  headerBtn.click();
                  console.log(`2초 후 헤더 버튼 클릭으로 "${keyword}" 검색`);
                } else {
                  console.warn("form/버튼 모두 없음.");
                }
              }, 2000);

              return true;
            }
            """

            result = self.driver.execute_script(search_script, keyword)

            if not result:
                print("   ✗ Search input not found")
                print("   🔄 페이지 새로고침 후 재시도...")

                # 새로고침
                self.driver.refresh()
                time.sleep(3)  # 로딩 대기

                # 검색 전 마우스 움직임 다시
                before_search(self.driver)

                # 재시도
                result = self.driver.execute_script(search_script, keyword)

                if not result:
                    print("   ✗ Search input not found (재시도 후에도 실패)")
                    self.action_status = ActionStatus.ERROR_ELEMENT_NOT_FOUND
                    return False
                else:
                    print("   ✓ Search input found after refresh")

            print(f"   ✓ Search script executed for: {keyword}")
            self.status = ExecutionStatus.SEARCH_SUBMITTED

            # 검색 제출 이벤트 로깅
            if UNIFIED_LOGGER_AVAILABLE:
                log_event(
                    worker_id=self.worker_id,
                    event_type=EventType.SEARCH_SUBMITTED,
                    interface=self.vpn_interface,
                    details={'keyword': keyword}
                )

            # 검색 결과 로딩 대기 (자동 녹화 중이므로 프레임 캡처 불필요)
            time.sleep(7)

            self.status = ExecutionStatus.RESULTS_LOADED
            self.action_status = ActionStatus.SUCCESS

            # 검색 완료 이벤트 로깅
            if UNIFIED_LOGGER_AVAILABLE:
                log_event(
                    worker_id=self.worker_id,
                    event_type=EventType.RESULTS_LOADED,
                    interface=self.vpn_interface,
                    details={'keyword': keyword}
                )

            print("   ✓ Search completed")
            return True

        except TimeoutException:
            print("   ✗ Timeout during search")
            self.action_status = ActionStatus.ERROR_TIMEOUT
            return False
        except Exception as e:
            print(f"   ✗ Search error: {e}")
            self.action_status = ActionStatus.ERROR_UNKNOWN
            return False

    def get_product_list(self, limit: int = 10) -> List[Dict]:
        """
        상품 목록 추출

        Args:
            limit: 추출할 상품 개수

        Returns:
            상품 정보 리스트
        """
        print(f"📦 Extracting product list (limit: {limit})...")

        products = []

        try:
            # 상품 카드 셀렉터
            product_selectors = [
                (By.CSS_SELECTOR, "li.search-product"),
                (By.CSS_SELECTOR, "div.search-product"),
                (By.CSS_SELECTOR, "li[data-product-id]"),
                (By.CSS_SELECTOR, "div[data-product-id]")
            ]

            product_elements = None
            for by, selector in product_selectors:
                try:
                    elements = self.driver.find_elements(by, selector)
                    if elements and len(elements) > 0:
                        product_elements = elements
                        print(f"   Found {len(elements)} products with selector: {selector}")
                        break
                except:
                    continue

            if not product_elements:
                print("   ✗ No products found")
                return []

            # 각 상품 정보 추출
            for i, element in enumerate(product_elements[:limit]):
                try:
                    # 상품명
                    name_selectors = [
                        (By.CSS_SELECTOR, "div.name"),
                        (By.CSS_SELECTOR, "a.name"),
                        (By.CSS_SELECTOR, "span.name")
                    ]
                    name = "N/A"
                    for by, sel in name_selectors:
                        try:
                            name_elem = element.find_element(by, sel)
                            if name_elem:
                                name = name_elem.text
                                break
                        except:
                            continue

                    # 가격
                    price_selectors = [
                        (By.CSS_SELECTOR, "strong.price-value"),
                        (By.CSS_SELECTOR, "em.sale"),
                        (By.CSS_SELECTOR, "span.price")
                    ]
                    price = "N/A"
                    for by, sel in price_selectors:
                        try:
                            price_elem = element.find_element(by, sel)
                            if price_elem:
                                price = price_elem.text
                                break
                        except:
                            continue

                    # 링크
                    link = None
                    try:
                        link_elem = element.find_element(By.TAG_NAME, "a")
                        if link_elem:
                            link = link_elem.get_attribute("href")
                    except:
                        pass

                    # 상품 ID
                    product_id = None
                    try:
                        product_id = element.get_attribute("data-product-id")
                    except:
                        pass

                    products.append({
                        "index": i + 1,
                        "name": name.strip() if name else "N/A",
                        "price": price.strip() if price else "N/A",
                        "link": link,
                        "product_id": product_id
                    })

                    print(f"   {i + 1}. {name[:50] if name else 'N/A'}... - {price}")

                except Exception as e:
                    print(f"   ⚠️  Product {i + 1} extraction failed: {e}")
                    continue

            print(f"   ✓ Extracted {len(products)} products")
            return products

        except Exception as e:
            print(f"   ✗ Error extracting products: {e}")
            return []

    def click_product(self, index: int = 0) -> bool:
        """
        상품 클릭

        Args:
            index: 상품 인덱스 (0부터 시작)

        Returns:
            성공 여부
        """
        print(f"👆 Clicking product #{index + 1}...")
        self.status = ExecutionStatus.PRODUCT_CLICKING
        self.action_status = ActionStatus.ELEMENT_WAITING

        try:
            # 상품 셀렉터
            product_selectors = [
                (By.CSS_SELECTOR, "li.search-product"),
                (By.CSS_SELECTOR, "div.search-product"),
                (By.CSS_SELECTOR, "li[data-product-id]")
            ]

            product_elements = None
            for by, selector in product_selectors:
                try:
                    elements = self.driver.find_elements(by, selector)
                    if elements and len(elements) > index:
                        product_elements = elements
                        break
                except:
                    continue

            if not product_elements or len(product_elements) <= index:
                print(f"   ✗ Product #{index + 1} not found")
                self.action_status = ActionStatus.ERROR_ELEMENT_NOT_FOUND
                return False

            element = product_elements[index]
            self.action_status = ActionStatus.ELEMENT_FOUND
            self.status = ExecutionStatus.PRODUCT_FOUND

            # 링크 찾기
            link_elem = element.find_element(By.TAG_NAME, "a")
            if not link_elem:
                print("   ✗ Product link not found")
                return False

            # 클릭
            self.action_status = ActionStatus.CLICKING
            link_elem.click()

            # 페이지 로딩 대기
            time.sleep(3)
            self.status = ExecutionStatus.PRODUCT_PAGE_LOADED
            self.action_status = ActionStatus.SUCCESS

            print(f"   ✓ Product page loaded")
            return True

        except TimeoutException:
            print("   ✗ Timeout clicking product")
            self.action_status = ActionStatus.ERROR_TIMEOUT
            return False
        except Exception as e:
            print(f"   ✗ Click error: {e}")
            self.action_status = ActionStatus.ERROR_UNKNOWN
            return False

    def add_to_cart(self) -> bool:
        """
        장바구니에 추가

        Returns:
            성공 여부
        """
        print("🛒 Adding to cart...")
        self.status = ExecutionStatus.CART_CLICKING
        self.action_status = ActionStatus.ELEMENT_WAITING

        try:
            # 장바구니 버튼 셀렉터
            cart_selectors = [
                (By.CSS_SELECTOR, "button.cart-btn"),
                (By.CSS_SELECTOR, "button[data-cart]"),
                (By.XPATH, "//button[contains(text(), '장바구니')]"),
                (By.XPATH, "//a[contains(text(), '장바구니')]")
            ]

            cart_button = None
            for by, selector in cart_selectors:
                try:
                    cart_button = self.wait.until(
                        EC.element_to_be_clickable((by, selector))
                    )
                    if cart_button:
                        break
                except:
                    continue

            if not cart_button:
                print("   ✗ Cart button not found")
                self.action_status = ActionStatus.ERROR_ELEMENT_NOT_FOUND
                return False

            self.action_status = ActionStatus.ELEMENT_FOUND

            # 클릭
            self.action_status = ActionStatus.CLICKING
            cart_button.click()
            self.status = ExecutionStatus.CART_CLICKED
            self.action_status = ActionStatus.SUCCESS

            time.sleep(2)

            print("   ✓ Added to cart")
            return True

        except TimeoutException:
            print("   ✗ Timeout adding to cart")
            self.action_status = ActionStatus.ERROR_TIMEOUT
            return False
        except Exception as e:
            print(f"   ✗ Cart error: {e}")
            self.action_status = ActionStatus.ERROR_UNKNOWN
            return False

    def show_network_mode_overlay(self):
        """
        브라우저 화면 중앙에 네트워크 모드 표시
        (3초 후 자동 페이드 아웃)
        """
        try:
            overlay_script = f"""
            (function() {{
                // 기존 오버레이 제거 (중복 방지)
                const existing = document.getElementById('network-mode-overlay');
                if (existing) {{
                    existing.remove();
                }}

                // 오버레이 생성
                const overlay = document.createElement('div');
                overlay.id = 'network-mode-overlay';
                overlay.textContent = '{self.network_mode}';

                // 스타일 설정
                overlay.style.cssText = `
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background-color: rgba(0, 0, 0, 0.8);
                    color: white;
                    font-size: 64px;
                    font-weight: bold;
                    padding: 40px 60px;
                    border-radius: 20px;
                    z-index: 999999;
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
                    text-align: center;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    transition: opacity 0.5s ease-out;
                `;

                document.body.appendChild(overlay);

                // 3초 후 페이드 아웃
                setTimeout(() => {{
                    overlay.style.opacity = '0';
                    setTimeout(() => overlay.remove(), 500);
                }}, 3000);
            }})();
            """

            self.driver.execute_script(overlay_script)
            print(f"   🌐 네트워크 모드 표시: {self.network_mode}")

        except Exception as e:
            print(f"   ⚠️  오버레이 표시 실패: {e}")

    def get_status(self) -> Dict:
        """현재 상태 반환"""
        url = ""
        try:
            if self.driver:
                url = self.driver.current_url
        except:
            pass

        return {
            "execution_status": self.status.value,
            "action_status": self.action_status.value,
            "url": url
        }

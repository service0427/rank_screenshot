#!/usr/bin/env python3
"""
스크린샷 캡처 모듈
브라우저 페이지 스크린샷을 캡처하고 저장하는 기능 제공
"""

import os
import stat
import time
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime


class ScreenshotCapturer:
    """스크린샷 캡처 및 저장을 담당하는 클래스"""

    def __init__(self, driver, base_dir: str = "screenshots"):
        """
        Args:
            driver: Selenium WebDriver 인스턴스
            base_dir: 스크린샷 저장 기본 디렉토리 (기본: "screenshots")
        """
        self.driver = driver
        self.base_dir = Path(base_dir)

    def capture(
        self,
        keyword: str = "",
        version: str = "",
        full_page: bool = False,
        product_id: str = "",
        item_id: str = "",
        vendor_item_id: str = ""
    ) -> Optional[str]:
        """
        현재 페이지 스크린샷 캡처

        Args:
            keyword: 검색 키워드 (파일명에 포함)
            version: Chrome 버전 (사용 안 함 - 하위 호환성 유지)
            full_page: 전체 페이지 캡처 여부 (기본: False, viewport만)
            product_id: 상품 ID (파일명에 포함)
            item_id: 아이템 ID (파일명에 포함)
            vendor_item_id: 판매자 아이템 ID (파일명에 포함)

        Returns:
            저장된 파일 경로 (실패 시 None)
        """
        if not self.driver:
            print("   ⚠️  No active driver for screenshot")
            return None

        try:
            # no_img 이미지 체크 및 해결 시도 (캡처 전)
            self._resolve_no_img_in_viewport(max_retries=2)

            # 저장 경로 생성
            filepath = self._generate_filepath(keyword, product_id, item_id, vendor_item_id)

            # 스크린샷 캡처
            if full_page:
                self._capture_full_page(filepath)
            else:
                self._capture_viewport(filepath)

            # 파일 크기 확인
            file_size = filepath.stat().st_size / 1024  # KB

            print(f"📸 Screenshot saved:")
            print(f"   Path: {filepath}")
            print(f"   Size: {file_size:.2f} KB")

            # 오래된 스크린샷 자동 정리 (최신 50개만 유지)
            from common.utils.file_cleanup import cleanup_screenshots
            try:
                cleanup_screenshots(base_dir=self.base_dir, keep_count=50)
            except Exception:
                pass  # 정리 실패해도 스크린샷 캡처는 성공으로 처리

            return str(filepath)

        except Exception as e:
            print(f"   ⚠️  Screenshot failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _generate_filepath(
        self,
        keyword: str,
        product_id: str,
        item_id: str,
        vendor_item_id: str
    ) -> Path:
        """
        스크린샷 파일 경로 생성

        경로 구조: screenshots/YYYY/MM/DD/HH-MM-SS_{keyword}_{product_id}_{item_id}_{vendor_item_id}.png

        Args:
            keyword: 검색 키워드
            product_id: 상품 ID
            item_id: 아이템 ID
            vendor_item_id: 판매자 아이템 ID

        Returns:
            저장할 파일 경로
        """
        # 현재 날짜/시간
        now = datetime.now()

        # 월별 폴더 밑에 일별 폴더 생성
        # screenshots/YYYY/MM/DD/
        year_month_day_dir = self.base_dir / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")

        # 디렉토리 생성 (일단 기본 권한으로)
        os.makedirs(str(year_month_day_dir), exist_ok=True)

        # 생성 직후 명시적으로 chmod 777 설정 (umask 무시)
        # 이 방법이 가장 확실함
        try:
            os.chmod(self.base_dir, 0o777)  # screenshots
            os.chmod(year_month_day_dir.parent.parent, 0o777)  # YYYY
            os.chmod(year_month_day_dir.parent, 0o777)  # MM
            os.chmod(year_month_day_dir, 0o777)  # DD
        except (PermissionError, OSError):
            # 다른 사용자 소유 디렉토리는 권한 변경 불가 (무시)
            pass

        # 파일명 생성: His_{keyword}_{product_id}_{item_id}_{vendor_item_id}.png
        time_str = now.strftime("%H%M%S")

        # 키워드 정리 (파일명에 사용 불가능한 문자 제거)
        safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_keyword:
            safe_keyword = "unknown"

        # 상품 정보가 없으면 "none"으로 표시
        safe_product_id = product_id if product_id else "none"
        safe_item_id = item_id if item_id else "none"
        safe_vendor_item_id = vendor_item_id if vendor_item_id else "none"

        filename = f"{time_str}_{safe_keyword}_{safe_product_id}_{safe_item_id}_{safe_vendor_item_id}.png"
        return year_month_day_dir / filename

    def _capture_viewport(self, filepath: Path):
        """
        현재 Viewport만 캡처

        Args:
            filepath: 저장할 파일 경로
        """
        self.driver.save_screenshot(str(filepath))

    def _capture_full_page(self, filepath: Path):
        """
        전체 페이지 캡처 (스크롤 포함)

        Args:
            filepath: 저장할 파일 경로
        """
        # 페이지 전체 높이 가져오기
        total_height = self.driver.execute_script("return document.body.scrollHeight")
        viewport_height = self.driver.execute_script("return window.innerHeight")

        # 원본 창 크기 저장
        original_size = self.driver.get_window_size()

        try:
            # 전체 페이지를 담을 수 있도록 창 크기 조절
            self.driver.set_window_size(original_size['width'], total_height)
            time.sleep(0.5)  # 렌더링 대기

            # 캡처
            self.driver.save_screenshot(str(filepath))

        finally:
            # 원래 크기로 복원
            self.driver.set_window_size(original_size['width'], original_size['height'])

    def check_no_img_in_viewport(self) -> Dict[str, int]:
        """
        Viewport 내 no_img 이미지 개수 체크

        Returns:
            {'viewport': viewport 내 no_img 개수, 'total': 전체 no_img 개수}
        """
        try:
            result = self.driver.execute_script("""
                const allImages = Array.from(document.querySelectorAll('img'));

                // no_img 이미지 필터링
                const noImgImages = allImages.filter(img =>
                    img.src.includes('no_img_1000_1000.png')
                );

                // viewport 내 no_img 이미지 필터링
                const noImgInViewport = noImgImages.filter(img => {
                    const rect = img.getBoundingClientRect();
                    return rect.top >= 0 &&
                           rect.bottom <= window.innerHeight &&
                           rect.left >= 0 &&
                           rect.right <= window.innerWidth;
                });

                return {
                    viewport: noImgInViewport.length,
                    total: noImgImages.length
                };
            """)

            print(f"   🖼️  no_img 이미지: viewport {result['viewport']}개 / 전체 {result['total']}개")

            return result

        except Exception as e:
            print(f"   ⚠️  no_img 체크 실패: {e}")
            return {'viewport': 0, 'total': 0}

    def _resolve_no_img_in_viewport(self, max_retries: int = 2) -> bool:
        """
        Viewport 내 no_img 이미지 해결 시도

        Args:
            max_retries: 최대 재시도 횟수 (기본: 2)

        Returns:
            성공 여부 (viewport에 no_img 없으면 True)
        """
        for attempt in range(1, max_retries + 1):
            # no_img 체크
            result = self.check_no_img_in_viewport()
            viewport_count = result['viewport']

            # viewport에 no_img 없으면 성공
            if viewport_count == 0:
                if attempt > 1:
                    print(f"   ✅ no_img 해결 완료 (시도 {attempt}회)")
                return True

            # no_img가 있으면 해결 시도
            if attempt < max_retries:
                print(f"   🔄 no_img 해결 시도 중... ({attempt}/{max_retries})")

                # 1. 추가 대기 (네트워크 완료 대기)
                time.sleep(2)

                # 2. 미세 스크롤로 lazy loading 재트리거
                try:
                    self.driver.execute_script("""
                        const currentScroll = window.scrollY;
                        // 아래로 100px 스크롤
                        window.scrollBy(0, 100);
                        setTimeout(() => {
                            // 원래 위치로 복귀
                            window.scrollTo(0, currentScroll);
                        }, 500);
                    """)
                    time.sleep(0.8)
                except Exception as e:
                    print(f"   ⚠️  스크롤 재트리거 실패: {e}")

        # 최대 재시도 후에도 no_img가 있으면 경고
        final_result = self.check_no_img_in_viewport()
        if final_result['viewport'] > 0:
            print(f"   ⚠️  viewport에 no_img {final_result['viewport']}개 남음 (계속 진행)")

        return True  # 실패해도 캡처는 진행
